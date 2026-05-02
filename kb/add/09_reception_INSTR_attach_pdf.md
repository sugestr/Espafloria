<!-- v: 2 | updated: 2026-05-02T21:10Z -->

# INSTR — Bulk attach paper PDF к Verdnatura pedido (post-reset)

Промт для отдельного чата. Самодостаточный — копировать целиком.

---

## Промт начинается

Ты работаешь над Espafloria SL Odoo 19 SaaS Custom (`espafloriasl.odoo.com`). Сначала прочитай по порядку:

1. `/Users/andriy/Documents/espafloria.odoo/CLAUDE.md`
2. `/Users/andriy/Documents/espafloria.odoo/kb/99_invariants.md`

## Цель

После DB reset и Holded re-import у нас в Odoo заново созданы все Verdnatura pedido (`purchase.order`) — **с новыми ID**, но с теми же vendor refs `12XXXXXXX` в поле `name`. У нас в репо лежат paper PDF — оригинальные albaranes от Verdnatura. Нужно **bulk-attach** каждый PDF к соответствующему pedido в Odoo через `ir.attachment` + `set_binary_field` с GitHub raw URL (Odoo сама фетчит файл, base64 не передавать inline).

## Где лежат PDF

Локально:
```
/Users/andriy/Documents/espafloria.odoo/pedido.files/reception_paper/
```

В репо (public GitHub): `sugestr/Espafloria` → `pedido.files/reception_paper/`

Public raw URL pattern (Odoo сама их фетчит):
```
https://raw.githubusercontent.com/sugestr/Espafloria/main/pedido.files/reception_paper/<filename>
```

В папке ~170 файлов:
- `verdnatura_<docNum>.pdf` — individual paper PDF за конкретный pedido (около 166 штук, docNum формата `12XXXXXXX`)
- `Factura_A126XXXXXX.pdf` (4-5 файлов) — monthly factura bundles (НЕ трогать, они уже разбиты на individual выше)
- `correction-*.pdf` (если есть) — отложить, owner разберёт вручную

## Verdnatura partner

Найди partner_id для Verdnatura:

```
search_records('res.partner', [['name','ilike','VERDNATURA']], fields=['id','name','vat'])
```

Должен быть один — `VERDNATURA LEVANTE SL` (был id=42 до reset, после reset скорее всего другой). Запомни как `VERD_PARTNER_ID`.

## Workflow

### Шаг 1 — list PDF

```bash
ls /Users/andriy/Documents/espafloria.odoo/pedido.files/reception_paper/verdnatura_*.pdf
```

Извлеки docNum из имени: `verdnatura_12211352.pdf` → docNum = `12211352`. Регекс `verdnatura_(\d+)\.pdf`.

### Шаг 2 — match с pedido

Для каждого docNum:

```
search_records('purchase.order',
  [['partner_id','=',VERD_PARTNER_ID], ['name','ilike',docNum]],
  fields=['id','name','partner_ref','state'],
  limit=2
)
```

Holded import обычно создаёт name типа `Holded albaran id: AC260497 Vendor ref:12510703`. Поэтому ищи по docNum в name (ilike — подстрока).

Кейсы:
- 1 hit → match, продолжить
- 0 hits → SKIP, добавить в unmatched
- 2+ hits → SKIP, в conflicts (2 pedido с тем же vendor ref — нестандарт)

### Шаг 3 — DRY-RUN отчёт ДО любого create

Покажи owner:

```
Total PDF файлов: X
Matched 1:1: Y
Unmatched (нет pedido с таким docNum): Z (примеры)
Conflicts (>1 pedido): W (примеры)
Already attached (см. шаг 3a): K
```

### Шаг 3a — проверить existing attachments

Перед attach проверь нет ли уже файла:

```
search_records('ir.attachment',
  [['res_model','=','purchase.order'], ['res_id','=',pedido_id]],
  fields=['id','name','mimetype'],
  limit=5
)
```

Если уже есть PDF (по `name` или `mimetype='application/pdf'`) — SKIP, не дубль.

**ЖДИ owner «ок»** на dry-run отчёт перед массовым create.

### Шаг 4 — bulk attach (после ок)

Для каждой matched пары `(pedido_id, docNum)`:

```python
# 4a — создать metadata record
att = create_record('ir.attachment', {
    'name': f'verdnatura_{docNum}.pdf',
    'res_model': 'purchase.order',
    'res_id': pedido_id,
    'type': 'binary',
    'mimetype': 'application/pdf',
})

# 4b — Odoo сама фетчит файл по URL
set_binary_field(
    'ir.attachment', att['record']['id'], 'datas',
    source=f'https://raw.githubusercontent.com/sugestr/Espafloria/main/pedido.files/reception_paper/verdnatura_{docNum}.pdf'
)
```

Между attach делай `sleep 0.5` — избегай rate limit.

### Шаг 5 — verify

После всех attach — повторный поиск:

```
search_records('ir.attachment',
  [['res_model','=','purchase.order'], ['mimetype','=','application/pdf']],
  fields=['id','res_id','name'],
  limit=300
)
```

Покажи count и сверь с ожидаемым.

### Шаг 6 — chatter audit на каждом изменённом pedido

Чтобы было видно что bot прицепил PDF:

```python
create_record('mail.message', {
    'model': 'purchase.order', 'res_id': pedido_id, 'author_id': 56,
    'message_type': 'comment', 'subtype_id': 1,
    'body': f'<p>🤖 Paper PDF attached: verdnatura_{docNum}.pdf (att id={att_id}). Источник: reception_paper/ via GitHub raw URL.</p>'
})
```

`author_id=56` = 🤖 Claude AI Reconciliation, должен survive reset; если нет — используй любого system user.

### Шаг 7 — финальный отчёт owner

```
✅ Attached: N PDF
⏭️ Skipped (already attached): K
❌ Unmatched (нет pedido): Z (список docNum)
⚠️ Conflicts (>1 pedido): W (список docNum + ids)

Coverage: N / total Verdnatura pedidos = ratio
```

## Hard rules (CLAUDE.md)

- **Тест на 1 файле** перед bulk: возьми первый PDF, прогони шаги 4a+4b на одном pedido, проверь что attachment появился в UI и открывается. ТОЛЬКО ПОТОМ batch.
- **author_id=56** на chatter (🤖 Claude AI Reconciliation).
- **GitHub raw URL должен быть public reachable** — проверь через `curl -I` первый URL до пробного create. Если 404 — repo private или путь не тот, owner подскажет.
- НЕ удаляй existing attachments.
- НЕ меняй pedido `name`, `partner_ref` или другие header поля — только attach файлов.
- НЕ создавай attachments если pedido не нашёлся — добавь в unmatched список для owner manual review.

## Запрещено

- НЕ инлайнить base64 PDF в `create_record` — context blow-up. Только `set_binary_field` с `source=URL`.
- НЕ парсить PDF (это другая задача — reconcile algorithm).
- НЕ создавать новые покупки/строки.
- НЕ обрабатывать `Factura_A126*.pdf` (monthly bundles — уже split на individual выше).
- НЕ обрабатывать `correction-*.pdf` если есть — это special, owner вручную.
- НЕ трогать non-Verdnatura pedido (если есть от других suppliers после reset — Holded import возможно создал).

## CHANGELOG

После задачи — одна строка в `/Users/andriy/Documents/espafloria.odoo/kb/CHANGELOG.md` сверху (bump v):

```
- 2026-05-XX — **paper PDF bulk attach post-reset**: N PDF прицеплены к Verdnatura pedido через GitHub raw URL + ir.attachment + set_binary_field. K pre-existing skipped, Z unmatched, W conflicts. author_id=56 chatter audit на каждом.
```

Если файл >15 entries — удали самую старую.

Git commit + push (через `mcp__Desktop_Commander__start_process` для git ops, не bash sandbox — bash блокирует `.git/`).

## Промт заканчивается
