# Bouquet: create SO from POS order on Assemble bouquet payment
# Server action id=1203
# Model: pos.payment
# Trigger: base.automation id=10, on_create_or_write, filter [('payment_method_id', '=', 6)]
# Last updated in prod: 2026-04-23
#
# What it does:
# - Reassemble branch: creates sale.order BP-YYYY-NNNN (tech partner Anon id=53) when florist
#   pays a POS order via "Собрать букет" (method id=6). If a Settle-linked old bouquet SO exists,
#   cancels it and reverses its original POS picking — "reassemble" flow.
# - Dismantle branch: triggered when pos.order has DISMANTLE_MARKER (product id=7865) AND
#   at least one line with sale_order_origin_id → SO with partner_id=53. Cancels old SO,
#   reverses old POS picking, cancels own future POS picking (belt-and-suspenders — see §44).
#   Does NOT create new SO. If marker present without Settle-link → raises UserError.
# - Idempotent via client_order_ref='POS#<pos_order.id>'.
#
# Stock-leak prevention layers 2 & 3: bouquet_on_picking_action.py (id=1205),
# bouquet_on_order_paid_action.py (id=1207). All three idempotent via reverse return check.
#
# Keys shared across the 3 actions:
#   BOUQUET_METHOD_ID = 6              — payment method "Собрать букет"
#   TECH_PARTNER_ID = 53               — Anon (клиент букета) res.partner
#   DISMANTLE_MARKER_PRODUCT_ID = 7865 — [BQ-DISMANTLE] 🗑 Разборка букета
#
# See: [05_florists_logistics_accountant.md §1.2.3](05_florists_logistics_accountant.md),
#      [99_invariants.md §32, §44](99_invariants.md)

BOUQUET_METHOD_ID = 6
TECH_PARTNER_ID = 53
DISMANTLE_MARKER_PRODUCT_ID = 7865
SEQUENCE_BY_WH_CODE = {
    'PLA': 'espafloria.bouquet.plaza',
    'GLO': 'espafloria.bouquet.gloria',
    'BLA': 'espafloria.bouquet.blau',
}

def reverse_pos_picking(pick, env):
    existing_return = env['stock.picking'].sudo().search([('return_id', '=', pick.id)], limit=1)
    if existing_return:
        return existing_return.id
    move_lines_vals = []
    for m in pick.move_ids.filtered(lambda mm: mm.state == 'done' and mm.product_uom_qty > 0):
        move_lines_vals.append((0, 0, {
            'product_id': m.product_id.id,
            'quantity': m.product_uom_qty,
            'move_id': m.id,
        }))
    if not move_lines_vals:
        return False
    return_wizard = env['stock.return.picking'].sudo().with_context(
        active_id=pick.id, active_ids=pick.ids, active_model='stock.picking',
    ).create({'picking_id': pick.id, 'product_return_moves': move_lines_vals})
    action_res = return_wizard.action_create_returns()
    new_pick_id = action_res.get('res_id') if isinstance(action_res, dict) else False
    if new_pick_id:
        new_pick = env['stock.picking'].sudo().browse(new_pick_id)
        for mv in new_pick.move_ids:
            mv.write({'quantity': mv.product_uom_qty})
        new_pick.with_context(skip_backorder=True).button_validate()
    return new_pick_id

SaleOrderSudo = env['sale.order'].sudo()

for payment in records:
    pos_order = payment.pos_order_id
    if not pos_order:
        continue
    pos_sudo = pos_order.sudo()
    idem_key = 'POS#%d' % pos_order.id
    existing = SaleOrderSudo.search([('client_order_ref', '=', idem_key)], limit=1)
    if existing:
        continue

    has_marker = any(l.product_id.id == DISMANTLE_MARKER_PRODUCT_ID for l in pos_sudo.lines)

    origin_ids = []
    for l in pos_sudo.lines:
        oid = l.sale_order_origin_id.id if l.sale_order_origin_id else 0
        so_from_sol = 0
        if not oid and l.sale_order_line_id:
            so_from_sol = l.sale_order_line_id.order_id.id
        picked = oid or so_from_sol
        if picked and picked not in origin_ids:
            origin_ids.append(picked)

    all_found = SaleOrderSudo.browse(origin_ids)
    tech_bouquet_sos = all_found.filtered(lambda so: so.partner_id.id == TECH_PARTNER_ID)
    active_old_sos = tech_bouquet_sos.filtered(lambda so: so.state == 'sale')

    if has_marker and not tech_bouquet_sos:
        raise UserError('Разборка букета: нет связи с активным букетом. Нажми Register → Orders, выбери букет BP-* для разборки, и потом добавь маркер "🗑 Разборка букета".')

    is_dismantle = has_marker and bool(tech_bouquet_sos)
    old_sos = active_old_sos

    reassembled_from = []
    if old_sos:
        linked_lines = pos_sudo.lines.filtered(lambda l: l.sale_order_line_id)
        if linked_lines:
            linked_lines.write({'sale_order_line_id': False})
        for old in old_sos:
            old_pos_id = False
            if old.client_order_ref and old.client_order_ref.startswith('POS#'):
                try:
                    old_pos_id = int(old.client_order_ref[4:])
                except (ValueError, TypeError):
                    old_pos_id = False
            if old_pos_id:
                old_pos = env['pos.order'].sudo().browse(old_pos_id).exists()
                if old_pos:
                    for opick in old_pos.picking_ids.filtered(lambda p: p.state == 'done'):
                        try:
                            reverse_pos_picking(opick, env)
                        except Exception as e:
                            try:
                                old.message_post(body='[bouquet reverse] POS picking %s reverse FAILED: %s' % (opick.name, str(e)))
                            except Exception:
                                pass
            for pick in old.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                moves_to_cancel = pick.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
                if moves_to_cancel:
                    moves_to_cancel.write({'state': 'cancel'})
                pick.write({'state': 'cancel'})
            old.write({'state': 'cancel'})
            reassembled_from.append(old)

    if is_dismantle:
        for cpick in pos_sudo.picking_ids:
            if cpick.state == 'done':
                try:
                    reverse_pos_picking(cpick, env)
                except Exception as e:
                    target = reassembled_from[0] if reassembled_from else (tech_bouquet_sos[0] if tech_bouquet_sos else None)
                    if target:
                        try:
                            target.message_post(body='[bouquet dismantle] Current POS picking %s reverse FAILED: %s' % (cpick.name, str(e)))
                        except Exception:
                            pass
            elif cpick.state != 'cancel':
                moves_to_cancel = cpick.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
                if moves_to_cancel:
                    moves_to_cancel.write({'state': 'cancel'})
                cpick.write({'state': 'cancel'})
        for old in reassembled_from:
            try:
                old.message_post(body='🗑 Разобран через POS %s.' % (pos_order.name or ('POS#%d' % pos_order.id)))
            except Exception:
                pass
        continue

    wh = pos_sudo.session_id.config_id.warehouse_id
    seq_code = SEQUENCE_BY_WH_CODE.get(wh.code)
    so_name = env['ir.sequence'].sudo().next_by_code(seq_code) if seq_code else False

    order_line_vals = []
    for pl in pos_sudo.lines:
        if pl.product_id.id == DISMANTLE_MARKER_PRODUCT_ID:
            continue
        if pl.qty == 0:
            continue
        order_line_vals.append((0, 0, {
            'product_id': pl.product_id.id,
            'product_uom_qty': pl.qty,
            'price_unit': pl.price_unit,
            'discount': pl.discount,
        }))
    if not order_line_vals:
        continue
    origin_val = pos_order.name if (pos_order.name and pos_order.name != '/') else ('POS#%d' % pos_order.id)
    so_vals = {
        'partner_id': TECH_PARTNER_ID,
        'warehouse_id': wh.id,
        'company_id': pos_order.company_id.id,
        'origin': origin_val,
        'client_order_ref': idem_key,
        'order_line': order_line_vals,
    }
    if so_name:
        so_vals['name'] = so_name
    so = SaleOrderSudo.create(so_vals)

    non_zero_non_marker = [pl for pl in pos_sudo.lines if pl.product_id.id != DISMANTLE_MARKER_PRODUCT_ID and pl.qty > 0]
    for pl, sol in zip(non_zero_non_marker, so.order_line):
        sol.write({'price_unit': pl.price_unit, 'discount': pl.discount})

    so.action_confirm()

    for pick in so.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
        moves_to_cancel = pick.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if moves_to_cancel:
            moves_to_cancel.write({'state': 'cancel'})
        pick.write({'state': 'cancel'})

    for old in reassembled_from:
        try:
            so.message_post(body='Пересобран из %s.' % old.name)
            old.message_post(body='Пересобран в %s.' % so.name)
        except Exception:
            pass
