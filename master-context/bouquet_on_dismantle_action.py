# Bouquet reserve-model: Dismantle branch
# Server action id=1209 (new in v2 refactor, 2026-04-23)
# Model: pos.payment
# Trigger: base.automation 13, on_create_or_write, filter [('payment_method_id', '=', 8)]
#
# Dismantle flow:
# - Флорист делает Register → Orders → Settle BP-* → оплата методом «🗑 Разобрать букет» (id=8)
# - Odoo штатно cancels SO-picking старого BP (он был assigned в reserve-model)
# - POS-picking этого чека списал компоненты (штатно)
# - Наш action:
#   1. cancel старый BP-* SO (reserve освобождается полностью)
#   2. reverse POS-picking (компоненты возвращаются на склад)
#   3. chatter: "Разобран через POS"
# - Итог: компоненты снова свободны в наличии, BP-* cancelled
#
# Constants:
#   BOUQUET_DISMANTLE_METHOD_ID = 8  — "🗑 Разобрать букет"
#   TECH_PARTNER_ID = 53             — Anon
#
# See: 05_florists_logistics_accountant.md §1.2.3,
#      99_invariants.md §46

BOUQUET_DISMANTLE_METHOD_ID = 8
TECH_PARTNER_ID = 53

def reverse_pos_picking(pick, env):
    existing = env['stock.picking'].sudo().search([('return_id', '=', pick.id)], limit=1)
    if existing:
        return existing.id
    moves_vals = []
    for m in pick.move_ids.filtered(lambda mm: mm.state == 'done' and mm.product_uom_qty > 0):
        moves_vals.append((0, 0, {'product_id': m.product_id.id, 'quantity': m.product_uom_qty, 'move_id': m.id}))
    if not moves_vals:
        return False
    rw = env['stock.return.picking'].sudo().with_context(
        active_id=pick.id, active_ids=pick.ids, active_model='stock.picking',
    ).create({'picking_id': pick.id, 'product_return_moves': moves_vals})
    res = rw.action_create_returns()
    nid = res.get('res_id') if isinstance(res, dict) else False
    if nid:
        np = env['stock.picking'].sudo().browse(nid)
        for mv in np.move_ids:
            mv.write({'quantity': mv.product_uom_qty})
        np.with_context(skip_backorder=True).button_validate()
    return nid

for payment in records:
    pos_order = payment.pos_order_id
    if not pos_order:
        continue
    pos_sudo = pos_order.sudo()

    origin_ids = []
    for l in pos_sudo.lines:
        oid = l.sale_order_origin_id.id if l.sale_order_origin_id else 0
        if oid and oid not in origin_ids:
            origin_ids.append(oid)
    all_origins = env['sale.order'].sudo().browse(origin_ids)
    active_anon_sos = all_origins.filtered(
        lambda so: so.partner_id.id == TECH_PARTNER_ID and so.state == 'sale'
    )

    if not active_anon_sos:
        raise UserError(
            'Разборка букета: нет связи с активным букетом. '
            'Нажми Register → Orders, выбери букет BP-* и оплати методом «🗑 Разобрать букет».'
        )

    employee_name = pos_order.employee_id.name if pos_order.employee_id else 'флористом'

    for old in active_anon_sos:
        old.sudo().action_cancel()

    for cpick in pos_sudo.picking_ids.filtered(lambda p: p.state == 'done'):
        try:
            reverse_pos_picking(cpick, env)
        except Exception as e:
            try:
                pos_sudo.message_post(
                    body='[bouquet dismantle] Reverse of %s FAILED: %s' % (cpick.name, str(e))
                )
            except Exception:
                pass

    for old in active_anon_sos:
        try:
            old.sudo().message_post(
                body='🗑 Разобран %s через POS %s. Компоненты возвращены на склад.' %
                     (employee_name, pos_order.name)
            )
        except Exception:
            pass
