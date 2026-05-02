<!-- v: 2 | updated: 2026-05-02T12:30Z -->
# INSTR: Wipe test transactions — сборник рецептов

**Что это:** набор **независимых рецептов** для зачистки разных типов мусора в Odoo Online после тестов. Каждый блок (POS, sales, accounting, stock, loyalty, partners, etc.) можно применять **отдельно** и в любом порядке внутри своей зоны.

**Когда использовать:** после периода тестирования (POS / sales / loyalty / accounting / stock-движения) надо обнулить транзакционный слой и оставить чистую конфигурацию, продукты, pedidos и автоматизации.

---

## ⚠️ Backup first — основное правило

**Перед любой зачисткой делать Database Manager → Download backup.** Это в десятки раз быстрее любой селективной очистки и даёт mandatory rollback на случай если что-то пойдёт не так.

После backup'а:
- Если тестовый период короткий и backup есть с момента «до тестов» → restore.
- Если backup'а до тестов нет, или хочется сохранить накопленную конфигурацию между бэкапами → применять рецепты ниже **выборочно**.

Этот документ **НЕ заменяет** backup как primary tool. Это сборник «как почистить X не трогая Y» для случаев когда restore не подходит.

---

## ⚠️ Точки невозврата — что нельзя трогать после определённых событий

| После события | НЕ трогать | Почему |
|---|---|---|
| Pedido confirmed (`state=purchase`) + picking done | `stock.move`, `stock.move.line`, `stock.picking` (incoming) этого pedido | Удалит факт приёмки. Stock.quant остаётся как есть (без audit trail). |
| Account.move posted и отчёт за период подан в налоговую | `account.move` за этот период | Бухгалтерская достоверность. |
| POS session closed с реальными продажами | `pos.session`, related `account.move` | Закрытие сессии = бухгалтерская проводка дня. |
| Reconciliation учёных vendor codes (через action 1217) | `product.supplierinfo` для этого partner | Месяцы накопленного ETL артефакта. |

**Правило:** если рецепт сносит сущность которая физически уже отработала (приходовала товар на склад, фискализировалась через закрытую сессию, попала в bill), — вместо delete делать **archive** (`active=false`) или **reverse** (credit note для invoice). Delete — только для тестовых данных без реального бизнес-эффекта.

---

## Гарантии этих рецептов

**НЕ трогается** (если применять рецепты по описанию):
- `product.template` / `product.product` (каталог + служебные карточки)
- `purchase.order` / `purchase.order.line` / `product.supplierinfo` (pedidos и learned codes)
- Конфиг: journals, taxes, POS configs, picking types, locations, sequences для productive entities (Purchase Order P, etc.)
- `base.automation`, `ir.actions.server` custom (1145, 1146, 1150, 1176, 1203, 1209, 1217), Studio views, custom fields
- Реальных партнёров (suppliers Verdnatura/Serviflor/Rillo/Decora/ParEx, owner, POS Terminal, 🌹 Букет 53, Claude AI 56)
- `res.users`, `hr.employee`

**Можно снести** (отдельными рецептами, по выбору):
- `pos.session` / `pos.order` / `pos.payment`
- `account.move` (out_invoice/refund + entry-типы от POS closing/payment combine) + `account.payment`
- `sale.order` + delivery `stock.picking` (PLA/OUT/*)
- POS `stock.picking` type=18 (PLA/POS/*) + `stock.move` + `stock.move.line`
- `stock.quant` (опционально: UPDATE quantity=0 либо DELETE)
- `stock.reference` orphans (custom model action 699 «References»)
- `loyalty.card` + `loyalty.history`
- `mail.message` + `mail.followers` orphans на удалённых моделях
- Тестовые `res.partner` (US tax authorities, явно тестовые имена)
- Sequences (Sales/POS/Bouquet/per-config POS) — отдельный рецепт
- Все WIPE TEST `ir.actions.server` (само-удаляются в конце своего блока)

---

## 0. Pre-checks (всегда перед началом)

| Проверка | Где | Ожидаемое |
|---|---|---|
| Developer mode ON | URL содержит `?debug=1` или иконка 🐞 | ✅ |
| Lock dates пустые | Settings → Accounting → Fiscal Periods + `res.company.{fiscalyear,tax,sale,purchase,hard}_lock_date` | все `false` |
| Hash chain на journals | `account.journal.restrict_mode_hash_table` на journals 10/15/19/20/24 | все `false` |
| pos.session все closed | `pos.session.state` | все `closed` |
| Реальных продаж не было | подтвердить с owner | ✅ |

Если lock dates выставлены — снять. Если hash chain включён на journal — снять (или будет blocker на Reset to Draft).

---

## 1. FK dependency chain ВНУТРИ одного blocка

Если применяешь блок «POS wipe» целиком — соблюдать порядок (иначе FK violations откатят транзакцию). Если применяешь блоки по отдельности — порядок между ними не важен (например stock wipe не зависит от sale wipe).

**Внутри POS wipe:**
1. **Customer invoices** (out_invoice) — Reset to Draft → Delete (через UI на posted, через MCP на draft)
2. **POS orders** — нужен SQL-bypass через `ir.actions.server`
3. **POS sessions** — нужен SQL-bypass (MCP не имеет unlink rights)
4. **POS payments** (`pos.payment`) — снести **до** pos.order через MCP `delete_records`
5. **Account.payment** — обход через `outstanding_account_id=false` потом MCP unlink
6. **Account.move** (entry-типы POS closing) — Reset to Draft → MCP unlink
7. **Sale.order** — cancel-state через MCP, sale-state через SQL bypass
8. **Stock.picking + stock.move + stock.move.line** — все или только тестовые типы (через SQL action)
9. **Stock.quant** — UPDATE quantity=0 и/или DELETE (опционально)
10. **Stock.reference** orphans — DELETE FROM stock_reference (action 699 список)
11. **Loyalty.card + loyalty.history** — SQL DELETE
12. **mail.message + mail.followers** orphans на удалённых моделях
13. **res.partner** тестовые — DELETE (если без FK), иначе archive
14. **Sequences reset** (`ir.sequence.number_next_actual=1, number_next=1`) — через MCP `update_records`
15. **Self-delete WIPE TEST actions**

---

## 2. Strategy matrix — что куда упирается

| Сущность | Ограничение | Workaround |
|---|---|---|
| `account.move` posted | UI ругается «can't delete posted journal item» | Reset to Draft (debug menu) → Delete |
| `pos.order` paid/done | `_check_already_invoiced` блокирует write на state | SQL UPDATE через server action |
| `pos.session` | MCP access denied | server action `DELETE FROM pos_session` |
| `loyalty.card` / `loyalty.history` | MCP access denied | server action SQL DELETE |
| `account.payment` paid/reconciled | `_check_outstanding_account` требует posted move | UPDATE `outstanding_account_id=false` → MCP unlink (каскадит move) |
| `stock.picking` type=18 (POS) | После SQL DELETE pos.session/order остаются orphan | server action `DELETE FROM stock_picking WHERE picking_type_id=18` (+ stock_move + stock_move_line) |
| `sale.order` state=sale | write блокирует state change | SQL UPDATE через server action, потом MCP unlink |
| `stock.quant` non-zero | оставляет записи в Physical Inventory list | UPDATE quantity=0 (cleanup) или DELETE (full wipe) |
| `stock.reference` orphans | модель в MCP скрыта | server action SQL DELETE |
| Posted moves через ORM | не через delete напрямую | флаг allow_set_draft на journal или Reset to Draft |

---

## 3. Server action template

Все санкционированные SQL bypass'ы — через `ir.actions.server` с `state='code'` + `binding_model_id` к удобной модели (Inventory list, Contacts, Sessions). Самоудаление в конце:

```python
# WIPE TEST: <subject>
env.cr.execute("DELETE FROM <table>")
# ... другие операции ...
env.cr.execute("DELETE FROM ir_act_server WHERE id = <ACTION_ID>")
env.cr.execute("DELETE FROM ir_actions WHERE id = <ACTION_ID>")
env.cr.commit()
```

**⚠️ Gotcha:** `ir_actions.name` в Odoo 19 — `jsonb` (translated). `LIKE 'WIPE%'` падает с `operator does not exist: jsonb ~~ unknown`. Использовать **прямые ID** или `name->>'en_US' LIKE '...'`.

**⚠️ Gotcha:** Action может удалить сам себя в той же транзакции — Postgres это разрешает (код уже в Python memory к моменту DELETE).

---

## 4. Step-by-step с кодом

### Шаг 4.1. Customer invoices

Через UI (debug mode) или MCP. Draft → MCP `delete_record('account.move', id)`. Posted → UI **Action → Reset to Draft → Action → Delete**. Если invoice связан с pos.order — на pos.order поле `account_move` обнулится автоматически.

### Шаг 4.2. POS orders + sessions + payments

**Порядок:** pos.payment → pos.order (через SQL state cancel) → pos.session (через SQL DELETE). Stock.picking type=18 — отдельным SQL шагом.

```python
# WIPE TEST: cancel all pos.orders (server action на pos.order, model_id=937)
env.cr.execute("UPDATE pos_order SET state='cancel' WHERE state IN ('paid','done','invoiced')")
env.cr.commit()
env['pos.order'].invalidate_model()
```

После этого pos.order можно `delete_records` через MCP. Pos.payment — снести **до** pos.order через MCP `delete_records('pos.payment', [...])`.

```python
# WIPE TEST: delete all pos.sessions (server action, model_id=940)
env.cr.execute("DELETE FROM pos_session")
env.cr.commit()
env['pos.session'].invalidate_model()
```

### Шаг 4.3. Account.payment + entries

Сначала снять constraint:

```python
# через MCP
update_records('account.payment', all_ids, {'outstanding_account_id': false})
delete_records('account.payment', all_ids)
# каскадно сносится связанный account.move
```

Оставшиеся `account.move` (state=draft после reset) — `delete_records` через MCP.

### Шаг 4.4. Sale.order

Cancel-state SO → MCP `delete_records` напрямую. Sale-state — server action:

```python
# WIPE TEST: cancel remaining sale.orders (server action, model_id=617)
env.cr.execute("UPDATE sale_order SET state='cancel' WHERE state='sale'")
env.cr.commit()
env['sale.order'].invalidate_model()
```

Потом MCP unlink. Связанные delivery PLA/OUT/* pickings — отдельным SQL DELETE.

### Шаг 4.5. Stock wipe (всё)

```python
# WIPE TEST: cleanup all stock + actions (server action, model_id=745=stock.picking)
env.cr.execute("DELETE FROM stock_move_line")
env.cr.execute("DELETE FROM stock_move")
env.cr.execute("DELETE FROM stock_picking")
env.cr.execute("UPDATE stock_quant SET quantity=0, reserved_quantity=0")  # или DELETE
env.cr.execute("DELETE FROM ir_act_server WHERE id IN (<all WIPE TEST ids>)")
env.cr.execute("DELETE FROM ir_actions WHERE id IN (<all WIPE TEST ids>)")
env.cr.commit()
```

**⚠️** Если хотим сохранить pedidos — НЕ запускать этот action. Pedidos подтверждённые имеют связанные stock.picking. Если pedidos все draft (как после re-import) — pickings ещё не созданы, безопасно.

**⚠️** При DELETE `stock_quant` записи Physical Inventory list (action `/odoo/physical-inventory`) пустеет полностью. При UPDATE `quantity=0` — записи остаются, но с нулём.

### Шаг 4.6. Stock.reference (action 699)

```python
env.cr.execute("DELETE FROM stock_reference")
env.cr.commit()
```

### Шаг 4.7. Loyalty + mail orphans + test partners

```python
# WIPE TEST: cleanup loyalty + mail + test partners (server action, model_id=90=res.partner)
# 1. Loyalty
env.cr.execute("DELETE FROM loyalty_history")
env.cr.execute("DELETE FROM loyalty_card")
# 2. mail orphans на удалённых моделях
wiped = ('pos.order','pos.session','pos.payment','sale.order','purchase.order','account.move','account.payment','stock.picking','stock.move','stock.move.line','loyalty.card','loyalty.history','product.supplierinfo')
env.cr.execute("DELETE FROM mail_followers WHERE res_model = ANY(%s)", (list(wiped),))
env.cr.execute("DELETE FROM mail_message WHERE model = ANY(%s)", (list(wiped),))
# 3. Тестовые партнёры (точные ID в зависимости от состояния — НЕ удалять реальных)
test_partner_ids = [...]  # US tax authorities, явные TEST-партнёры
env.cr.execute("DELETE FROM mail_followers WHERE res_model='res.partner' AND res_id = ANY(%s)", (test_partner_ids,))
env.cr.execute("DELETE FROM mail_message WHERE model='res.partner' AND res_id = ANY(%s)", (test_partner_ids,))
env.cr.execute("DELETE FROM res_partner WHERE id = ANY(%s)", (test_partner_ids,))
env.cr.commit()
```

Если на res.partner есть FK от другой сущности — DELETE упадёт с FK violation, вся транзакция откатится. Тогда fallback: archive (`UPDATE res_partner SET active=false WHERE id = ANY(%s)`).

### Шаг 4.8. Sequences reset

Через MCP. Сбросить только тестово-разогнанные. **НЕ трогать** Purchase Order P (id=17) — это baseline для Holded import (14000+).

```python
# Sequences которые тестинг разгоняет
update_records('ir.sequence', [
    3,    # Sales Order S
    20,   # POS Session /
    36,   # PLA/OUT/
    43,   # PLA/POS/
    54,   # BLA/OUT/
    64,   # POS order from config #1
    66,   # POS order line from config #1
    67,   # POS device from config #1
    88,   # Bouquet Plaza BP-YYYY-
], {'number_next_actual': 1, 'number_next': 1})
```

Если pedidos тоже снесли (более радикальный wipe) — добавить:
- 35 PLA/IN/
- 44 GLO/IN/
- 53 BLA/IN/

---

## 5. Pre-flight script — что точно нужно проверить

```python
# В одном MCP-запросе перед началом
search_records('res.company', fields=['fiscalyear_lock_date','tax_lock_date','sale_lock_date','purchase_lock_date','hard_lock_date'])
search_records('account.journal', domain=[['restrict_mode_hash_table','=',True]])
search_records('pos.session', domain=[['state','!=','closed']])
search_records('account.move', domain=[['state','=','posted'],['move_type','=','out_invoice']])  # сколько posted invoice'ов
search_records('purchase.order', limit=1)  # сколько pedidos
search_records('product.template', limit=1)  # сколько карточек
```

Если есть открытые сессии — закрыть. Если есть hash chain — снять. Если посчитал pedidos и карточки и они NOT 0 — `purchase.order` и `product.template` гарантированно не пострадают (они не в нашем chain).

---

## 6. Post-wipe verification

```python
search_records('pos.session', limit=1)        # 0
search_records('pos.order', limit=1)          # 0
search_records('pos.payment', limit=1)        # 0
search_records('account.move', limit=1)       # 0
search_records('account.payment', limit=1)    # 0
search_records('sale.order', limit=1)         # 0
search_records('loyalty.card', limit=1)       # 0
search_records('stock.picking', limit=1)      # 0
search_records('stock.move', limit=1)         # 0
search_records('mail.message', domain=[['model','in',['pos.order','sale.order','account.move']]], limit=1)  # 0
search_records('purchase.order', limit=1)     # ≠0 (сохранились)
search_records('product.template', limit=1)  # ≠0 (сохранились)
search_records('product.supplierinfo', limit=1)  # ≠0 (сохранились) — если их вообще не сносили
search_records('ir.actions.server', domain=[['name','ilike','WIPE TEST']], limit=1)  # 0 (все само-удалились)
```

---

## 7. Что **точно** не сносить

| Не трогать | Причина |
|---|---|
| `product.template` / `product.product` | Каталог — нормированные карточки + служебные. Восстановление требует re-import |
| `purchase.order` / `purchase.order.line` | Pedidos от Holded — основа reconciliation |
| `product.supplierinfo` | Learned vendor codes — long-term ETL артефакт, копится месяцами |
| `res.partner` реальные | Espafloria, suppliers, Букет 53, Claude 56, owner |
| `res.users`, `hr.employee` | Учётки и сотрудники |
| `ir.cron`, `base.automation`, кастомные `ir.actions.server` (1145/1146/1150/1176/1203/1209/1217), `ir.ui.view` Studio, `ir.model.fields` (state=manual) | Конфигурация системы |
| `pos.config`, `pos.payment.method`, `account.journal`, `account.tax`, `stock.warehouse`, `stock.location`, `stock.picking.type` | Конфигурация POS/учёта/склада |
| Sequence `Purchase Order` (id=17) | Baseline Holded import (14000+) |

---

## 8. Backup перед wipe

Odoo Online: **Database Manager → Download backup** (если есть критическое сомнение). При запуске restore — потеряешь правки сделанные после backup.

---

## 9. Известные gotchas из real-world прогона (2026-05-02)

1. **jsonb LIKE на ir.actions.name** — падает. Использовать прямые ID.
2. **procurement_group table не существует** в Odoo Online Custom этой инсталляции — ожидавшаяся "ссылочная" модель оказалась `stock.reference` (custom).
3. **pos.order.amount_paid stored** — установка в 0 не разблокирует state change. Только SQL bypass.
4. **account.payment unlink каскадит** связанный move — если payment унесли, его account.move уйдёт автоматически.
5. **MCP user permissions** не дают unlink на pos.session, loyalty.card, loyalty.history, stock.reference — только server action.
6. **stock.quant с quantity=0** не показывается в `inventoryLocation` фильтрах но видно в Physical Inventory page. DELETE убирает совсем.
7. **Кэш браузера** на Action menu — после само-удаления action имя ещё висит до Cmd+Shift+R.
8. **res.partner с FK от ir.cron / fiscal positions / payment terms** не удалится. Fallback — archive.

---

## 10. См. также

- [99_invariants.md](99_invariants.md) — правило «перед массовыми операциями — тест на одной записи».
- [CHANGELOG.md](CHANGELOG.md) — entry 2026-05-02 с детальным real-world прогоном этой процедуры.
- [07_state_snapshot.md](07_state_snapshot.md) — текущий state базы (что сейчас есть и в каких количествах).
