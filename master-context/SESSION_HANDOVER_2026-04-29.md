<!-- v: 1 | updated: 2026-04-29T13:15Z -->
# Session handover — Verdnatura 2026 reconciliation

Контекст для новой сессии: подбираем работу по реконсиляции 173 Verdnatura albaranes за 2026 г.

## 1. Большая цель

**Перенести историю заказов 2026 с Holded в Odoo на основе бумажных PDF поставщика.** Holded — глючный инструмент, бумага = правда. Закрыть pedido = сверить paper PDF (истина) + Odoo lines (мнение бухгалтера: какая карта + recount qty).

## 2. Жёсткие правила (read first)

- **Бумага первичнее Holded.** Holded API данные = бухгалтерский ввод, мог ошибаться. Не закрывать pedido без paper PDF.
- **Откатывать всё что закрыто без paper.** Уже откачен 37724/12492439 (мой косяк через Holded API).
- **Карта = один продукт.** Не сливать дорогую и дешёвую под один codigo (даже если похожие имена).
- **Нумерация в ответах**: 1, 1.1, 1.2, 2.1 (для ссылок номером).
- **Verdnatura partner_id = 42** (НЕ 23).
- **Author_id=56** (🤖 Claude AI Reconciliation) на всех `message_post` через action 1217.
- **Soft-gate ≤5 стеблей** — auto-OK; >5 — flag для owner.
- **Accept Holded recount при положительной дельте** (paper<Holded → щедрость поставщика, в нашу пользу). Кроме явных опечаток ввода.

## 3. Текущая инфраструктура

### 3.1 Action 1217 (`master-context/reconcile_finalize_action.py`)
Триггер: `purchase.order.x_studio_claude_finalize=True` (через base.automation 15, фильтр state in ['draft', 'purchase']).

Три ветки:
- **A) ROLLBACK** — note содержит `ROLLBACK_HOLDED_API` → reverse picking + button_draft + clear Phase A
- **B) RETRY** — state=purchase + есть pending pickings → soft-gate + validate
- **C) DRAFT** — pre-flight + button_confirm + Phase A2 + soft-gate + validate

### 3.2 Кастомные поля
- `purchase.order.x_studio_claude_finalize` — flag триггер
- `purchase.order.note` — для маркера ROLLBACK_HOLDED_API
- `purchase.order.line.x_studio_supplier_sku` — paper Verdnatura Ref
- `purchase.order.line.x_studio_supplier_product_name` — paper Concepto
- `purchase.order.line.x_studio_expected_qty` — paper-truth qty
- `purchase.order.line.x_studio_item_comment` — лог
- `stock.move.x_studio_received_packs` — реально полученные паки
- `stock.move.x_studio_review_status` — gate смотрит на префикс "OK"

## 4. Cumulative статус по 173 pedidos (на 2026-04-29 13:15 UTC)

| Состояние | Кол-во | Комментарий |
|---|---|---|
| Fully closed (state=purchase + picking done) | **107** | через настоящий paper PDF; 105 от агентов + Pilot 2 + Pilot 3 |
| Stuck >MINOR (state=purchase, picking assigned) | 8 | требуют accept Holded или paper PDF; review_status>5 stems |
| Откачен (state=draft, reverse picking done) | 1 | 37724/12492439 — мой косяк; ждёт повторного reconcile на paper |
| PNG-плейсхолдер draft | 16 | paper PDF не скачан; **1 уже скачан** (12492439, верифицирован) |
| Draft с amount_total>0 без Phase A | ~30 | прогнал bulk flag — не пускает pre-flight (нет supplier_sku) |
| Draft amount=0 без Phase A | ~10 | агенты не доходили |
| Line/qty mismatch (paper N ≠ Odoo M) | ~13 | разбирать вручную/агент с remap |

## 5. URL pattern для скачивания paper PDF из Holded

Через Chrome MCP (Holded UI):
```
https://app.holded.com/box/file?p=purchaseshipments/<mongoId>/deliverynote<fileId>.pdf
```

`fileId` извлекается из DOM iframe `[src*="nextappload"]`:
```js
const ifr = document.querySelector('iframe[src*="nextappload"]');
const a = ifr.contentDocument.querySelector('a[href*="/box/file?p="]');
const url = 'https://app.holded.com' + a.getAttribute('href');
const res = await fetch(url, { credentials: 'include' });
const buf = await res.arrayBuffer();
// blob download via <a download>
```

API endpoint `/invoicing/v1/documents/purchaseshipment/<id>` НЕ возвращает attachment fileId. Только Chrome iframe.

### 5.1 mongoIds для 16 PNG-плейсхолдеров
```
12492439 → 69d032da49ae8a0ada04c61d  (СКАЧАН ✓)
12492083 → 69d02f6e4832163ad6062215
12491307 → 69c3fc2b61cc673b240d25b7
12461957 → 69c3e699e67af17d5b081377
12455416 → 69c3d9b73b95ff85a10573b1
12420769 → 69d0ecc90cdc8102cc070271
12294902 → 698b91dce1a36a9555057362
12295939 → 698b90e8fa04b1226a06a110
12294906 → 6981ee1889530b7252053977
12295948 → 6981ec978745bf820a0c062d
12294920 → 6981e9c6e34390448503f6f1
12281779 → 6981e5bce28afc17fe0fe43b
12295963 → 6981e381728f94af3707ef08
12210664 → 6966c337592c26af0201f3dd
12212028 → 6966c1017f0a739963093d9b
12186249 → 69675354fe7992777f09af7b
```

### 5.2 ВАЖНО — проверить альтернативные имена в Downloads
Пользователь раньше скачивал PDF под именами:
- `<docNum> VERDNATURA LEVANTE SL.pdf` — реальные PDF (50-180 KB)
- `<docNum> VERDNATURA LEVANTE SL (1).pdf`, `(2).pdf` — дубли
- `delivery-note-<docNum>.pdf` — реальные PDF

`verdnatura_<docNum>.pdf` ≤11 KB = PNG-плейсхолдер (мой bulk download испортил).

**Сначала grep в Downloads** на эти альтернативные имена — может они уже есть в нужном виде, не надо качать.

## 6. 8 stuck pedidos требующие accept Holded или paper

Phase A применена. Соглашаемся с Holded recount по правилу 4.1 (положительная дельта = щедрость).

| Pedido | docNum | Проблемная line | Дельта | Решение |
|---|---|---|---|---|
| 37589 | 12178233 | ROSA PRETTY PILLOW AYANA | +13 | accept Holded — закрыто этой сессией |
| 37598 | 12210647 | ALLIUM NEAPOLITANUM | +20 | accept — закрыто |
| 37620 | 12241558 | BOLSA NATURE | +20 | accept — закрыто |
| 37667 | 12362713 | STATICE | +11 | accept — закрыто |
| 37683 | 12389782 | RANUNCULUS GRANDE | +47 | accept — закрыто |
| 37678 | 12391326 | HORTENSIA NACIONAL | +22 | accept — закрыто |
| 37732 | 12511587 | CRISANTEMO UNIFLOR | +20 | accept — закрыто |
| 37582 | 12186266 | RS Dragon Fly +8 / **CLAVEL -39** | -39 на CLAVEL | **❌ СТРАННО** — paper 40 / Odoo 1. Owner проверить |

**37582 не закрыт** — CLAVEL -39 подозрительно (опечатка ввода 1 vs 40?). Owner глазами.

Обновление: 7 из 8 уже закрыты этой сессией через accept Holded (move 771, 701, 820, 1157, 992, 984, 1081 переписан review_status="OK (accept Holded +N)"). Остался только 37582 CLAVEL.

## 7. Задачи для новой сессии (по приоритету)

### 7.1 P0 — Скачать 15 paper PDF
1. Сначала grep alternative names в `/Users/andriy/Downloads/` (`<docNum> VERDNATURA LEVANTE SL.pdf` или `delivery-note-<docNum>.pdf`)
2. Если найдены — переименовать в `verdnatura_<docNum>.pdf` (или просто использовать как есть)
3. Если НЕ найдены — через Chrome MCP iframe pattern (см. 5.) скачать каждый по mongoId

### 7.2 P0 — Подгрузить paper PDF в `ir.attachment` каждого pedido
Для всех 173 pedidos прицепить настоящий PDF (не PNG):
```python
mcp__odoo__create_record('ir.attachment', {
    'name': 'verdnatura_<docNum>.pdf',
    'datas': base64_encoded,
    'res_model': 'purchase.order',
    'res_id': pedido_id,
    'mimetype': 'application/pdf'
})
```
Это audit trail — paper в Odoo навсегда.

### 7.3 P1 — Reconcile 16 PNG-плейсхолдеров
После скачивания paper для каждого: Phase A через bash pdftotext + парсинг → flag → action 1217.
Включая 37724 (12492439) — после reconcile вернуть в state=purchase + Validate.

### 7.4 P1 — Phase A на ~30 draft с amount_total>0 без supplier_sku
Это pedidos где Holded написал price (через Holded import), но агенты не дошли до Phase A. Bumping pre-flight через bulk flag не пускает (no supplier_sku). Нужен агент с paper PDF.

### 7.5 P2 — Разбор 13 line/qty mismatch
Природа ошибки: бухгалтер в Holded мог дробить/объединять/дропать строки относительно бумаги. См. примеры в master-context (12421571 — paper 18 vs Odoo 16; CLAVEL MIX merge: 4 paper variants → 3 Odoo strings = -40 stems missing; RS Be Sweet — paper line dropped).

Подход (с **flag review** на каждое нестандартное действие):
- Для каждой paper строки искать матч в Odoo через `product.supplierinfo.product_code = paper Ref`
- Найден product без строки → создать новую order_line + activity 🟠🚧 для review
- Не найден → создать карточку в карантине 207 + activity ❌

### 7.6 P2 — Owner проверка 37582 CLAVEL -39
Paper 40 vs Odoo 1. Опечатка ввода или реально получили 1 стебель?

## 8. Где взять контекст

- `master-context/CHANGELOG.md` — последние 15 записей о работе
- `master-context/reconcile_finalize_action.py` — текущий код action 1217 v5
- `master-context/CLAUDE.md` — стандартные инструкции
- `master-context/99_invariants.md` — правила
- Memory:
  - `feedback_holded_role.md` — Holded только PDF + расспросы
  - `project_pdf_attachment_task.md` — PDF в ir.attachment
  - `feedback_card_distinct_codigos.md` — карта = один продукт
  - `project_odoo_partner_ids.md` — partner_id=42
  - `project_reconcile_action_constraints.md` — action 1217 ограничения
  - `feedback_numbered_outputs.md` — нумерация ответов
  - `feedback_holded_api_docs.md`, `feedback_odoo_version_docs.md` — дисциплина docs
- Holded API: `mcp__holded__holded_raw` GET `/invoicing/v1/documents/purchaseshipment/<mongoId>` (даёт products, не attachments!)
- Chrome MCP: уже есть открытый tab 32855526 на app.holded.com (Browser 1, deviceId `0d2720b2-2fcb-4479-aec1-d08247a64e3a`)

## 9. Что НЕ делать (грабли)

- Не использовать Holded API products как paper truth — это бухгалтерский ввод
- Не cancel done picking стандартными методами — только через `stock.return.picking` wizard
- Не писать `state=` напрямую — использовать `button_draft()` / `button_confirm()`
- Не присваивать через `obj.field = value` в safe_eval — только `obj.write({...})`
- В action 1217 везде `author_id=56` для message_post
- Soft-gate threshold = 5 stems; не менять без обсуждения с owner
- Bash sandbox НЕ позволяет rm/mv user files — через Desktop Commander
