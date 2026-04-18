# Calculate in Shop — кнопка «Посчитать в магазине»
# Server action id=1150
# Model: stock.picking (Transfer)
# Binding: stock.picking list + form view
# Last updated in prod: 2026-04-18
#
# What it does:
# - Iterates over all stock.moves in the picking
# - For incoming receipts (picking_type_id.code == 'incoming') with linked purchase line
# - Sets quantity = -1 (sentinel: "not counted yet by florist")
# - Does NOT reset x_studio_received_packs (intentional — см. инвариант)
#
# See: [03_odoo_receipt_review.md](../../03_odoo_receipt_review.md)

for picking in records:
    for move in picking.move_ids:
        if move.purchase_line_id and move.picking_id and move.picking_id.picking_type_id.code == 'incoming':
            move['quantity'] = -1
