---
name: Reconcile server action 1217 — constraints
description: Что умеет и не умеет ir.actions.server id=1217 для bulk reconcile Verdnatura albaranes
type: project
originSessionId: 37b18c39-25eb-4c7f-b45c-7e6b5ce66cd3
---
ir.actions.server id=1217 (🤖 Claude AI Reconcile Finalize) триггерится через `x_studio_claude_finalize=True` на purchase.order. Mirror — `master-context/reconcile_finalize_action.py`.

**Pipeline:**
1. Pre-flight: `state=='draft'`, `amount_total>0`, все order_line имеют `x_studio_supplier_sku`
2. button_confirm()
3. Phase A2: пишет `x_studio_received_packs`, `quantity` на stock.move
4. Final gate: останавливается если хоть один stock.move имеет `x_studio_review_status` НЕ начинающийся с "OK"
5. button_validate(skip_backorder=True)

**Что не умеет:**
- **Не работает на state=purchase** — Pre-flight ставит state=='draft' жёстко. Если pedido частично подтверждён (Phase A прошла, picking создан, но gate отвалил) — flip flag не помогает. Нужен либо ручной Validate в UI, либо отдельный «validate-only» server action.
- **Не различает minor variance** — gate отвергает любой review_status кроме "OK*". Параллельная автоматизация пишет «от бумаги ±N» при дельте — gate стоит насмерть.

**Связанные кастомные поля:**
- `purchase.order.line.x_studio_supplier_sku` — paper Ref
- `purchase.order.line.x_studio_supplier_product_name` — paper Concepto
- `purchase.order.line.x_studio_expected_qty` — Holded recount qty (для pack lines = факт стеблей)
- `purchase.order.line.x_studio_item_comment` — лог
- `purchase.order.x_studio_claude_finalize` — flag триггер
- `stock.move.x_studio_review_status` — текстовый статус, gate смотрит на префикс "OK"
- `stock.move.x_studio_received_packs` — реально полученные паки
- `stock.move.x_studio_paper_qty` / `x_studio_paper_unit` — **related** к purchase_line_id.product_qty/.uom_id, не отдельные поля

**Why:** safe_eval ограничения (нет STORE_ATTR, нет hasattr, нет __name__) вынудили использовать `.write({})` везде. Pre-flight на state=='draft' — защита от дубликата выполнения, но это блокирует retry после частичного fail.

**How to apply:**
- Перед триггером flag — убедись что все order_line имеют supplier_sku
- Для retry застрявших pickings нужна либо UI-валидация owner'ом, либо отдельная server action
- Для minor variance (≤2 стеблей) — в Phase A писать `x_studio_expected_qty=paper_qty` (paper=правда), чтобы gate не запутался
