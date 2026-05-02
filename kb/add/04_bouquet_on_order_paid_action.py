# Bouquet dismantle: safety net on pos.order state=paid (layer 3)
# Server action id=1207
# Model: pos.order
# Trigger: base.automation id=12, on_create_or_write, filter [('state', '=', 'paid')]
# Last updated in prod: 2026-04-23
#
# What it does:
# - Fires on every pos.order write while state='paid' (typically 10+ times per order —
#   each POS-side update to the order triggers it). Idempotent.
# - For pos.order with dismantle marker (product id=7865) — iterates picking_ids,
#   reverses any done picking without an existing return. Safety net if layers 1 & 2
#   somehow missed the picking.
# - In the successful end-to-end test (POS Plaza - 000015 / BP-2026-0009), layer 2 (id=1205)
#   caught the picking first, and this layer fired idempotently without extra work.
#
# See: bouquet_on_payment_action.py (layer 1, id=1203),
#      bouquet_on_picking_action.py (layer 2, id=1205),
#      [05_florists_logistics_accountant.md §1.2.3](05_florists_logistics_accountant.md),
#      [99_invariants.md §44](99_invariants.md)

DISMANTLE_MARKER_PRODUCT_ID = 7865

def reverse_pos_picking(pick, env):
    existing_return = env['stock.picking'].sudo().search([('return_id', '=', pick.id)], limit=1)
    if existing_return:
        return existing_return.id
    move_lines_vals = []
    for m in pick.move_ids.filtered(lambda mm: mm.state == 'done' and mm.product_uom_qty > 0):
        move_lines_vals.append((0, 0, {'product_id': m.product_id.id, 'quantity': m.product_uom_qty, 'move_id': m.id}))
    if not move_lines_vals:
        return False
    rw = env['stock.return.picking'].sudo().with_context(active_id=pick.id, active_ids=pick.ids, active_model='stock.picking').create({'picking_id': pick.id, 'product_return_moves': move_lines_vals})
    res = rw.action_create_returns()
    nid = res.get('res_id') if isinstance(res, dict) else False
    if nid:
        np = env['stock.picking'].sudo().browse(nid)
        for mv in np.move_ids:
            mv.write({'quantity': mv.product_uom_qty})
        np.with_context(skip_backorder=True).button_validate()
    return nid

for pos in records:
    pos_sudo = pos.sudo()
    has_marker = any(l.product_id.id == DISMANTLE_MARKER_PRODUCT_ID for l in pos_sudo.lines)
    if not has_marker:
        continue
    for cpick in pos_sudo.picking_ids:
        if cpick.state == 'done':
            existing_return = env['stock.picking'].sudo().search([('return_id', '=', cpick.id)], limit=1)
            if existing_return:
                continue
            try:
                new_id = reverse_pos_picking(cpick, env)
                if new_id:
                    pos_sudo.message_post(body='[bouquet dismantle] Safety net reversed %s via return id=%d' % (cpick.name, new_id))
            except Exception as e:
                try:
                    pos_sudo.message_post(body='[bouquet dismantle] Safety net reverse of %s FAILED: %s' % (cpick.name, str(e)))
                except Exception:
                    pass
        elif cpick.state != 'cancel':
            moves_to_cancel = cpick.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            if moves_to_cancel:
                moves_to_cancel.write({'state': 'cancel'})
            cpick.sudo().write({'state': 'cancel'})
