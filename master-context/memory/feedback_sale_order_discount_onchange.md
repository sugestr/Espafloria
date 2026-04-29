---
name: sale.order.line discount перезатирается на create
description: discount в create vals sale.order.line теряется из-за pricelist onchange — надо ставить write после create
type: feedback
originSessionId: 07213270-a7cf-4f8d-8fef-9168e48c9bf8
---
При `env['sale.order'].create({'order_line': [(0,0,{'discount': 50, ...})]})` значение `discount` не сохраняется — `sale.order.line._compute_discount` / pricelist onchange пересчитывает его в 0 на основе партнёра и прайслиста.

**Why:** в Bouquet workstream discount 50% с POS cart не перенёсся в новый SO BP-2026-0007 (POS line показывал discount=50, SO line показал discount=0). Partner=53 (Anon) без pricelist — всё равно перетёр.

**How to apply:** после `so = env['sale.order'].create(vals)` явно прописать discount на SO-линиях:
```python
for pl, sol in zip(pos_order.lines, so.order_line):
    if pl.discount:
        sol.write({'discount': pl.discount})
```
(Python 3 safe_eval не даёт iter/next — только zip.)
price_unit аналогично может перетереться pricelist'ом — если важен ценник POS, пропиши и его.
