---
name: Odoo 19 stock.return.picking API
description: Как правильно вызывать wizard возврата picking в Odoo 19 из server action с POS-user контекста
type: feedback
originSessionId: 07213270-a7cf-4f8d-8fef-9168e48c9bf8
---
Wizard `stock.return.picking` в Odoo 19 имеет только 2 записываемых поля: `picking_id` и `product_return_moves` (o2m на `stock.return.picking.line`). **Нет `location_id`** — передача его в create vals поднимает ошибку.

Поля `stock.return.picking.line`: `product_id` (required), `quantity` (required), `move_id`, `to_refund`, `wizard_id`.

Метод создания возвратного picking: `action_create_returns()` — возвращает action dict с `res_id` нового picking.

ACL: `stock.return.picking` доступен только группе `Inventory / User` (id=56). POS-user (группа 87 Point of Sale / User) НЕ имеет прав. Для вызова из action на pos.payment нужен `.sudo()`.

**Why:** при дебаге action 1203 (Bouquet re-assembly) reverse старого POS picking тихо падал в except — сначала из-за несуществующего `location_id`, потом из-за ACL. Оба исправления нужны.

**How to apply:** при любом программном вызове return-wizard из контекста POS-user:
```python
env['stock.return.picking'].sudo().with_context(
    active_id=pick.id, active_ids=pick.ids, active_model='stock.picking'
).create({
    'picking_id': pick.id,
    'product_return_moves': [(0, 0, {
        'product_id': m.product_id.id,
        'quantity': m.product_uom_qty,
        'move_id': m.id,
    }) for m in pick.move_ids if m.state == 'done'],
}).action_create_returns()
```
Потом на возвратном picking: `mv.write({'quantity': mv.product_uom_qty})` для каждого move, затем `.with_context(skip_backorder=True).button_validate()` (тоже sudo на browse нового picking).
