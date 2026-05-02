<!-- v: 2 | updated: 2026-05-02T21:10Z -->

# INSTR — Запуск reception_algorithm на ОДНОМ pedido (тестовый прогон + сравнение версий)

Промт для отдельного чата. Самодостаточный — копировать целиком.

Контекст использования:
- **Фаза 1 (тестирование):** owner запускает этот промт несколько раз в отдельных чатах с РАЗНЫМИ версиями `reception_algorithm.md` (например v19 → v20 → v21). Цель: сравнить результаты, выбрать лучшую версию.
- **Фаза 2 (фиксация):** после выбора canonical версии — owner оставляет её как `reception_algorithm.md` в репо.
- **Фаза 3 (production):** owner прогоняет ВСЕ pedido через выбранную версию (отдельный bulk-промт, не этот).

Этот промт — только **single pedido test run**. Никаких bulk loops.

---

## Промт начинается

Ты работаешь над Espafloria SL Odoo 19 SaaS Custom (`espafloriasl.odoo.com`). Тестируешь reception_algorithm на ОДНОМ pedido. Это test run — НЕ batch, НЕ loop, только один pedido от начала до конца.

### Параметры запуска (заполняет owner перед запуском)

```
PEDIDO_DOCNUM = "12XXXXXXX"        # vendor ref Verdnatura
ALGORITHM_VERSION = "vNN"          # тестируемая версия (v19 / v20 / draft)
ALGORITHM_FILE_PATH = "/Users/andriy/Documents/master-context/master-context/reception_algorithm.md"
                                   # либо путь к draft версии типа reception_algorithm_v20_draft.md
COMPARE_TO_VERSION = "vNN-1" | None  # если есть baseline для сравнения, указать версию
DRY_RUN = true | false             # true = посчитать & показать decisions, не писать в Odoo
```

### Что прочитать в самом начале

1. `/Users/andriy/Documents/master-context/CLAUDE.md`
2. `/Users/andriy/Documents/master-context/master-context/99_invariants.md`
3. **`{ALGORITHM_FILE_PATH}` целиком** — это твой spec. Следуй буквально.
4. `/Users/andriy/Documents/master-context/master-context/reconcile_finalize_action.py` — server action 1217 (mirror prod-кода). Понять что делает finalize-флаг.
5. Если есть COMPARE_TO_VERSION — прочитать тоже эту версию для diff-понимания.

### Шаг 1 — найти pedido

```
search_records('purchase.order',
  [['name','ilike',PEDIDO_DOCNUM]],
  fields=['id','name','partner_id','partner_ref','state','amount_total','order_line','x_studio_claude_finalize'],
  limit=2
)
```

Кейсы:
- 0 hits → стоп, показать owner: "не нашёл pedido с docNum {PEDIDO_DOCNUM}"
- 2+ hits → стоп, показать owner: "найдено N pedido с этим docNum, кого брать?"
- 1 hit → продолжить, запомнить как `PEDIDO_ID`

### Шаг 2 — найти paper PDF

Ищи в `/Users/andriy/Documents/master-context/reception_paper/verdnatura_{PEDIDO_DOCNUM}.pdf`.

```bash
ls /Users/andriy/Documents/master-context/reception_paper/verdnatura_{PEDIDO_DOCNUM}.pdf
```

Если нет — стоп, owner manual.

Парсинг paper:
```bash
pdftotext -layout /Users/andriy/Documents/master-context/reception_paper/verdnatura_{PEDIDO_DOCNUM}.pdf -
```

Если PDF — multi-pedido bundle (Factura A126*) — извлекай секцию между `Albarán {PEDIDO_DOCNUM}` маркерами per spec §A2 в reception_algorithm.

### Шаг 3 — прогнать алгоритм

Следуй `{ALGORITHM_FILE_PATH}` буквально. Спецификация описывает per-line decision tree (paper-truth, MIX consolidate, pack/stem, ⛔ placeholder, ×N inflation, и т.д.).

Для каждой order_line pedido:
1. Извлечь paper.ref (codigo Verdnatura), qty, price из paper PDF
2. Match с line.product_id и line.x_studio_supplier_sku
3. Применить decision tree из spec
4. Записать решение (с указанием rule из spec — ссылка типа «§B2 row 3 paper-truth wins»)

### Шаг 4 — DRY_RUN режим (если DRY_RUN=true)

НЕ менять Odoo. Только распечатать **per-line decision report**:

```
Pedido {PEDIDO_DOCNUM} (id={PEDIDO_ID}) — DRY-RUN | algorithm {ALGORITHM_VERSION}

Paper subtotal: XX.XX€ + IVA → total YY.YY€
Odoo current state: amount_total=ZZ.ZZ€ state={state}

Per-line decisions:
  Line {id} {product.name}
    paper.ref={ref}, paper qty={N}, paper price={P}
    odoo qty={N'}, odoo price={P'}, odoo card={card}
    DECISION: {action} per §{rule}
    RATIONALE: {1-2 lines}

  Line {id} ...
  ...

Card creates needed: K (list with proposed default_code, name, category, tax)
Reassigns: M (list with old_card_id → new_card_id)
Phase A writes: P (list of fields to update)
Trigger 1217: yes/no
Expected new amount_total: YY.YY€ (≡ paper)

Outstanding ambiguous: A (list with explanation, owner-decision needed)
```

Это всё. Если DRY_RUN — конец.

### Шаг 5 — LIVE режим (если DRY_RUN=false)

Применить per-line decisions из шага 3 на pedido в Odoo:

1. **Pilot test на ОДНОЙ строке pedido перед обработкой остальных** (CLAUDE.md правило):
   - Возьми первую строку из плана
   - Применить write
   - Verify через get_record
   - Покажи owner result, ЖДИ «ок»
2. После «ок» — продолжить остальные строки в том же pedido (bulk-loop в рамках одного pedido допустим, но НЕ переходить на другие pedido).
3. Создать карты если spec требует (новые ⛔→ canonical reassign).
4. Создать supplierinfo если spec требует.
5. Финал: trigger action 1217 через `update_record('purchase.order', PEDIDO_ID, {'x_studio_claude_finalize': True})`.
6. `sleep 15` секунд (action 1217 работает через base.automation 15).
7. Verify final state:
   ```
   get_record('purchase.order', PEDIDO_ID, ['name','state','amount_total','picking_ids'])
   ```
   Должно: `state='purchase'`, `amount_total ≡ paper total`, picking done.

### Шаг 6 — отчёт (test run summary)

```
✅ TEST RUN — pedido {PEDIDO_DOCNUM} | algorithm {ALGORITHM_VERSION} | DRY_RUN={DRY_RUN}

Paper total: YY.YY€
Odoo BEFORE: state={old_state}, amount={old_total}
Odoo AFTER:  state={new_state}, amount={new_total}
Match с paper: {YES / NO с дельтой}
Picking: {done / blocked + reason}

Применено правил из spec:
  §B1 card decision: K раз
  §B2 qty matrix: M раз
  §A3.1 supplierinfo learn: P раз
  §A2.11 pack/stem detect: Q раз
  ... (ссылки на §-параграфы spec)

Карт создано: K (ids list)
Карт reassign: M (line.id → new product.id)
Supplierinfo создано: P (ids list)

Issues / surprises:
  - {что-то выявил неожиданно — например spec ambiguous case}
  - {если правило spec не сработало — что и почему}

Время выполнения: ~X минут
```

### Шаг 7 — DIFF с предыдущей версией (если COMPARE_TO_VERSION задан)

Если в репо есть прошлый run-report для того же pedido через COMPARE_TO_VERSION (поищи `master-context/algo_test_runs/{PEDIDO_DOCNUM}_v*.md`) — покажи **side-by-side diff**:

```
Pedido {PEDIDO_DOCNUM}

| Метрика | {old_ver} | {new_ver} | Δ |
|---|---|---|---|
| Final amount | XX.XX€ | YY.YY€ | +0.10€ |
| Decisions per-line | 8 paper-truth | 7 paper-truth + 1 MIX consolidate | -1+1 |
| Cards created | 2 | 1 | -1 (учли existing 7857) |
| Match с paper | yes | yes | OK |
| Issues | none | 1 ambiguous (line 3) | +1 |

Главное отличие: {1-2 предложения}
Какой результат лучше: {old / new / equal} + почему
```

### Шаг 8 — сохранить run-report для архива

Создай файл:
```
/Users/andriy/Documents/master-context/master-context/algo_test_runs/{PEDIDO_DOCNUM}_{ALGORITHM_VERSION}.md
```

Содержимое: вывод шагов 6 + 7 в markdown.

Git commit + push (через `mcp__Desktop_Commander__start_process`, не bash sandbox).

## Hard rules (CLAUDE.md)

- **Один pedido. Не два. Не batch. Не loop по другим pedido.**
- **Pilot test на 1 строке** перед обработкой остальных строк в том же pedido (если LIVE).
- **author_id=56** (🤖 Claude AI Reconciliation) на всём chatter.
- НЕ менять header pedido (`picking_type_id`, `partner_ref`, `partner_id`) — только `order_line` + `x_studio_claude_finalize`.
- НЕ удалять supplierinfo — только создавать.
- При создании supplierinfo указывай `partner_id`, `product_tmpl_id`, `product_code` (paper.ref), `price`, `date_start`. Это backup кода для будущей matching.
- НЕ применять к pedido не-Verdnatura (если попадётся другой supplier — стоп, owner manual).

## Запрещено

- НЕ обрабатывать второй pedido после первого.
- НЕ создавать карт без указания tax/category — следуй spec §A5.
- НЕ применять paper-truth qty без проверки pack/stem ratio (spec §A2.11) — иначе ×N inflation проскочит.
- НЕ trigger 1217 если есть unresolved blocker (cards =0, sku=0, color=red, etc.) — spec §B7.
- НЕ менять reception_algorithm.md (это spec, не output).

## CHANGELOG

После test run — одна строка в `/Users/andriy/Documents/master-context/master-context/CHANGELOG.md` сверху (bump v):

```
- 2026-05-XX — **algo test run pedido {PEDIDO_DOCNUM} v{ALGORITHM_VERSION}**: {DRY_RUN/LIVE}, paper {YY.YY}€ ≡ Odoo, K карт create, M reassigns. Issues: {краткое}. Report: master-context/algo_test_runs/{PEDIDO_DOCNUM}_v{N}.md.
```

## Промт заканчивается
