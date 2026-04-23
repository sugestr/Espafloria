# Bouquet dismantle: cancel/reverse POS picking (layer 2)
# Server action id=1205
# Model: stock.picking
# Trigger: base.automation id=11, on_create_or_write (no filter_domain)
# Last updated in prod: 2026-04-23
#
# What it does:
# - Fires on every stock.picking create/write. Early fires have no origin (POS sets it last,
#   after button_validate), so this action skips them via `if not pick.origin: continue`.
# - On the final fire (origin = pos.order.name, state = 'done'), looks up the pos.order;
#   if it has the dismantle marker (product id=7865), reverses the picking via
#   stock.return.picking (idempotent: skips if return already exists).
# - For rare states 'draft'/'assigned' (pre-validate), tries .write({'state': 'cancel'}).
#   In practice POS validates the picking before origin is set, so the done-branch is the
#   one that actually runs.
#
# Why the timing hack: in Odoo 19 POS populates picking.origin AFTER button_validate()
# executes. Writing state='cancel' on a done picking doesn't un-do the moves. Only
# stock.return.picking with action_create_returns() properly reverses committed stock.
#
# See: bouquet_on_payment_action.py (layer 1, id=1203),
#      bouquet_on_order_paid_action.py (layer 3, id=1207),
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

for pick in records:
    if not pick.origin:
        continue
    pos = env['pos.order'].sudo().search([('name', '=', pick.origin)], limit=1)
    if not pos:
        continue
    has_marker = any(l.product_id.id == DISMANTLE_MARKER_PRODUCT_ID for l in pos.lines)
    if not has_marker:
        continue
    if pick.state == 'done':
        try:
            new_id = reverse_pos_picking(pick, env)
            if new_id:
                pos.sudo().message_post(body='[bouquet dismantle] Reversed POS picking %s via return id=%d' % (pick.name, new_id))
        except Exception as e:
            try:
                pos.sudo().message_post(body='[bouquet dismantle] Reverse of %s FAILED: %s' % (pick.name, str(e)))
            except Exception:
                pass
    elif pick.state != 'cancel':
        moves_to_cancel = pick.sudo().move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if moves_to_cancel:
            moves_to_cancel.write({'state': 'cancel'})
        pick.sudo().write({'state': 'cancel'})
        try:
            pos.sudo().message_post(body='[bouquet dismantle] Cancelled pre-validate POS picking %s' % pick.name)
        except Exception:
            pass
