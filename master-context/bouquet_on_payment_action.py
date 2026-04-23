# Bouquet reserve-model: Create / Reassemble / Sell branches
# Server action id=1203 (v2 — reserve-model refactor, 2026-04-23)
# Model: pos.order  (changed from pos.payment to ensure POS-picking exists at trigger time)
# Trigger: base.automation 10, on_create_or_write, filter [('state', '=', 'paid')]
#
# Reserve-model principles:
# - При создании букета (assemble) SO-picking остаётся assigned — reserve держит компоненты
# - POS-picking от того же чека reverse'ится через layer 2 (action 1205) когда state=done
# - При Settle с обычной оплатой (Sell) Odoo 19 штатно cancels SO-picking → POS-picking списывает → qty_delivered updated
# - Reassemble = cancel старого SO (reserve отпускается) + create new SO (новый reserve)
# - Маркер [BOUQUET-ASSEMBLY] (id=7864) автоматически добавляется в new SO с price=0 если забыт флористом
#
# Branches:
#   1. Create: method=6, no Settle → new BP-* SO, confirm, SO-picking assigned (reserve)
#   2. Reassemble: method=6, has Settle → cancel old BP-* (close_reason='reassembled'), create new BP-* SO
#   3. Sell: method !=6 (Cash/Card/etc), has Settle → close old SO (sold_full or sold_markdown), no new SO
#   4. Noop: method != 6, no Settle → обычная POS-продажа, не наше дело
#   5. Dismantle (method=8) — handled by separate action 1209
#
# Studio fields written:
#   x_studio_assembled_by (Create + Reassemble — на новом BP)
#   x_studio_sold_by (Sell — на старом BP)
#   x_studio_close_date (Reassemble + Sell — на старом BP)
#   x_studio_close_reason ('reassembled' / 'sold_full' / 'sold_markdown' — на старом BP)
#
# sold_markdown triggered if either:
#   - x_studio_markdown_pct > 0 on old SO (header-level markdown)
#   - any pos.order.line.discount > 0 on non-marker lines
#
# Idempotency:
#   - Assemble create: client_order_ref='POS#<id>' check
#   - Sell: skip if x_studio_close_reason already set
#
# Constants (shared across 1203 и 1209):
#   BOUQUET_ASSEMBLE_METHOD_ID = 6   — "🌹 Собрать / изменить букет"
#   BOUQUET_DISMANTLE_METHOD_ID = 8  — "🗑 Разобрать букет" (in action 1209)
#   TECH_PARTNER_ID = 53             — Anon
#   ASSEMBLY_MARKER_PRODUCT_ID = 7864 — "🌹 Работа по сборке букета"
#
# See: 05_florists_logistics_accountant.md §1.2.x,
#      99_invariants.md §32, §46

BOUQUET_ASSEMBLE_METHOD_ID = 6
BOUQUET_DISMANTLE_METHOD_ID = 8
TECH_PARTNER_ID = 53
ASSEMBLY_MARKER_PRODUCT_ID = 7864
SEQUENCE_BY_WH_CODE = {
    'PLA': 'espafloria.bouquet.plaza',
    'GLO': 'espafloria.bouquet.gloria',
    'BLA': 'espafloria.bouquet.blau',
}

def build_order_lines(pos_sudo):
    """Build SO order_line vals. Auto-insert assembly marker (price=0) if missing."""
    vals = []
    has_marker = False
    for pl in pos_sudo.lines:
        if pl.qty == 0:
            continue
        if pl.product_id.id == ASSEMBLY_MARKER_PRODUCT_ID:
            has_marker = True
        vals.append((0, 0, {
            'product_id': pl.product_id.id,
            'product_uom_qty': pl.qty,
            'price_unit': pl.price_unit,
            'discount': pl.discount,
        }))
    if not has_marker and vals:
        vals.append((0, 0, {
            'product_id': ASSEMBLY_MARKER_PRODUCT_ID,
            'product_uom_qty': 1,
            'price_unit': 0.0,
            'discount': 0.0,
        }))
    return vals

SaleOrderSudo = env['sale.order'].sudo()
NOW = datetime.datetime.now()

for pos_order in records:
    pos_sudo = pos_order.sudo()
    idem_key = 'POS#%d' % pos_order.id
    methods = set(pos_sudo.payment_ids.mapped('payment_method_id.id'))
    is_assemble = BOUQUET_ASSEMBLE_METHOD_ID in methods
    is_dismantle = BOUQUET_DISMANTLE_METHOD_ID in methods
    if is_dismantle:
        continue  # handled by action 1209

    origin_ids = []
    for l in pos_sudo.lines:
        oid = l.sale_order_origin_id.id if l.sale_order_origin_id else 0
        if oid and oid not in origin_ids:
            origin_ids.append(oid)
    all_origins = SaleOrderSudo.browse(origin_ids)
    anon_origins = all_origins.filtered(lambda so: so.partner_id.id == TECH_PARTNER_ID)
    has_settle = bool(anon_origins)
    active_anon_sos = anon_origins.filtered(lambda so: so.state == 'sale')

    employee = pos_order.employee_id
    employee_name = employee.name if employee else 'флористом'

    # --- Sell branch (not is_assemble, has Settle) ---
    if not is_assemble:
        if not has_settle:
            continue
        unclosed = anon_origins.filtered(lambda so: not so.x_studio_close_reason)
        if not unclosed:
            continue  # already closed (idempotent against multiple pos.order writes)

        partner = pos_order.partner_id
        is_anon_sale = (not partner) or partner.id == TECH_PARTNER_ID
        partner_name = partner.name if partner else 'Anon (без выбора)'
        # any line discount triggers sold_markdown (besides header markdown_pct)
        has_line_discount = any(
            pl.discount > 0
            for pl in pos_sudo.lines
            if pl.product_id.id != ASSEMBLY_MARKER_PRODUCT_ID and pl.qty > 0
        )
        for old in unclosed:
            close_vals = {'x_studio_close_date': NOW, 'x_studio_sold_by': employee.id if employee else False}
            so_markdown = old.x_studio_markdown_pct or 0
            close_vals['x_studio_close_reason'] = 'sold_markdown' if (so_markdown > 0 or has_line_discount) else 'sold_full'
            try:
                old.sudo().write(close_vals)
            except Exception:
                pass
            try:
                msg = '💰 Продан %s клиенту %s через POS %s. Итого %.2f€.' % (
                    employee_name, partner_name, pos_order.name, pos_order.amount_total
                )
                if has_line_discount and so_markdown == 0:
                    msg += ' 💸 Скидки на строках в чеке.'
                if is_anon_sale:
                    msg += ' ⚠️ Анонимная продажа (клиент не выбран — флорист не собрал CRM).'
                old.sudo().message_post(body=msg)
            except Exception:
                pass
        continue

    # --- Assemble (Create + Reassemble) ---
    if SaleOrderSudo.search([('client_order_ref', '=', idem_key)], limit=1):
        continue  # already processed

    if has_settle:
        for old in active_anon_sos:
            try:
                old.sudo().write({'x_studio_close_date': NOW, 'x_studio_close_reason': 'reassembled'})
            except Exception:
                pass
            old.sudo().action_cancel()

    order_line_vals = build_order_lines(pos_sudo)
    if not order_line_vals:
        continue

    wh = pos_sudo.session_id.config_id.warehouse_id
    seq_code = SEQUENCE_BY_WH_CODE.get(wh.code)
    so_name = env['ir.sequence'].sudo().next_by_code(seq_code) if seq_code else False

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
    if employee:
        so_vals['x_studio_assembled_by'] = employee.id
    so = SaleOrderSudo.create(so_vals)

    # Restore price/discount (pricelist onchange may overwrite)
    pl_lines = [pl for pl in pos_sudo.lines if pl.qty > 0]
    for i, pl in enumerate(pl_lines):
        if i < len(so.order_line):
            sol = so.order_line[i]
            sol.write({'price_unit': pl.price_unit, 'discount': pl.discount})

    so.action_confirm()  # SO-picking → assigned (reserve-model)
    # DO NOT cancel SO-picking — reserve holds components
    # POS-picking reverse handled by layer 2 (action 1205 on stock.picking)

    if has_settle:
        old_names = ', '.join(active_anon_sos.mapped('name'))
        try:
            so.sudo().message_post(
                body='✏️ Пересобран %s из %s через POS %s.' % (employee_name, old_names, pos_order.name)
            )
        except Exception:
            pass
        for old in active_anon_sos:
            try:
                old.sudo().message_post(
                    body='✏️ Пересобран %s в %s через POS %s.' % (employee_name, so.name, pos_order.name)
                )
            except Exception:
                pass
    else:
        components = ', '.join([
            sol.product_id.name
            for sol in so.order_line
            if sol.product_id.id != ASSEMBLY_MARKER_PRODUCT_ID
        ])
        try:
            so.sudo().message_post(
                body='🌹 Собран %s через POS %s. Состав: %s.' % (employee_name, pos_order.name, components)
            )
        except Exception:
            pass
