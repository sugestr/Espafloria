# Server action: 🤖 Claude AI Reconcile Finalize  (v7.3)
# v7.3 (2026-04-30):
#   1. Body summary использует <br/> вместо \n для line breaks (Odoo HTML view не рендерит \n).
#   2. env.cr.flush() ПЕРЕД pedido.message_post(summary) — flushes pending Odoo auto-tracking
#      messages from button_validate FIRST, чтобы Claude summary имел БОЛЬШИЙ id и появлялся
#      первым в chatter (newest top, под Activities).
# v7.2: детальный summary chatter (с list orange/yellow/green) + auto-create mail.activity
# v7.1: plain text summary (HTML escape fix)
# v7: Phase A2 always writes quantity + gate-by-color + summaries
# v6: tracking_disable + remove generic "✅ done"

UOM_PAQUETE_ID = 31
MINOR_THRESHOLD = 5
ROLLBACK_MARKER = 'ROLLBACK_HOLDED_API'
CLAUDE_AUTHOR = 56
PASS_COLORS = (10, 8, 3, 2)
BLOCK_COLORS = (1, 4)

for pedido in records:
    try:
        if ROLLBACK_MARKER in (pedido.note or ''):
            done_pickings = pedido.picking_ids.filtered(lambda p: p.state == 'done')
            for picking in done_pickings:
                try:
                    wizard = env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking', active_ids=[picking.id]).create({})
                    for return_line in wizard.product_return_moves:
                        if return_line.move_id:
                            return_line.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'quantity': return_line.move_id.quantity})
                    return_action = wizard.action_create_returns()
                    new_pid = return_action.get('res_id') if isinstance(return_action, dict) else None
                    if new_pid:
                        new_picking = env['stock.picking'].browse(new_pid)
                        for m in new_picking.move_ids:
                            m.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'quantity': m.product_uom_qty})
                        new_picking.with_context(skip_backorder=True, tracking_disable=True, mail_create_nolog=True, mail_notrack=True).button_validate()
                        pedido.message_post(body="✅ reverse picking " + new_picking.name + " validated", author_id=CLAUDE_AUTHOR)
                except Exception as ep:
                    pedido.message_post(body="❌ rollback picking error: " + str(ep), author_id=CLAUDE_AUTHOR)
            try:
                pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).button_draft()
            except Exception as e2:
                pedido.message_post(body="⚠️ button_draft failed: " + str(e2), author_id=CLAUDE_AUTHOR)
            for line in pedido.order_line:
                line.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'price_unit': 0, 'x_studio_supplier_sku': False, 'x_studio_supplier_product_name': False, 'x_studio_item_comment': False})
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'note': False, 'x_studio_claude_finalize': False})
            pedido.message_post(body="✅ Claude rollback finished. State=" + pedido.state, author_id=CLAUDE_AUTHOR)
            continue

        if pedido.state == 'purchase':
            pending = pedido.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if not pending:
                pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
                continue
            flagged = []
            for picking in pending:
                for move in picking.move_ids:
                    if move.state in ('done', 'cancel'):
                        continue
                    color = move.x_studio_review_color or 0
                    if color in PASS_COLORS:
                        continue
                    if color in BLOCK_COLORS:
                        flagged.append(move.product_id.display_name + ': color=' + str(color))
                        continue
                    paper = move.product_uom_qty or 0
                    actual = move.quantity or 0
                    delta = abs(paper - actual)
                    if delta == 0:
                        continue
                    elif delta <= MINOR_THRESHOLD:
                        sign = '+' if actual > paper else '-'
                        new_status = 'OK (auto ' + sign + str(int(delta)) + ')'
                        if move.x_studio_review_status != new_status:
                            move.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_review_status': new_status})
                    else:
                        flagged.append(move.product_id.display_name + ': дельта ' + str(int(actual-paper)) + ' стеблей')
            if flagged:
                pedido.message_post(body="⛔ Claude validate retry stopped (" + str(len(flagged)) + " moves >MINOR): " + '; '.join(flagged), author_id=CLAUDE_AUTHOR)
                pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
                continue
            for picking in pending:
                picking.with_context(skip_backorder=True, tracking_disable=True, mail_create_nolog=True, mail_notrack=True).button_validate()
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
            continue

        if pedido.state != 'draft':
            pedido.message_post(body="⛔ Claude finalize skipped: state=" + str(pedido.state), author_id=CLAUDE_AUTHOR)
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
            continue
        if not pedido.order_line:
            pedido.message_post(body="⛔ Claude finalize skipped: no order_line", author_id=CLAUDE_AUTHOR)
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
            continue
        if pedido.amount_total <= 0:
            pedido.message_post(body="⛔ Claude finalize skipped: amount_total=0", author_id=CLAUDE_AUTHOR)
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
            continue
        unfilled = pedido.order_line.filtered(lambda l: not l.x_studio_supplier_sku)
        if unfilled:
            pedido.message_post(body="⛔ Claude finalize skipped: " + str(len(unfilled)) + " lines without supplier_sku", author_id=CLAUDE_AUTHOR)
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
            continue
        pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).button_confirm()
        pack_lines_summary = []
        for picking in pedido.picking_ids:
            if picking.state == 'done':
                continue
            for move in picking.move_ids:
                line = move.purchase_line_id
                if not line:
                    continue
                vals = {}
                if line.uom_id.id == UOM_PAQUETE_ID:
                    paq_count = line.product_qty
                    stems = line.x_studio_expected_qty or paq_count
                    vals['x_studio_received_packs'] = paq_count
                    vals['quantity'] = stems
                    avg = (stems / paq_count) if paq_count > 0 else 0
                    pack_lines_summary.append(line.name + ': ' + str(int(paq_count)) + ' пак × ' + str(round(avg, 1)) + ' = ' + str(int(stems)) + ' шт')
                else:
                    target_qty = line.x_studio_expected_qty if line.x_studio_expected_qty else line.product_qty
                    vals['quantity'] = target_qty
                if vals:
                    move.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write(vals)
        if pack_lines_summary:
            pack_body = "📦 Phase A2 (pack detection) — найдено " + str(len(pack_lines_summary)) + " пачек:<br/>"
            for s in pack_lines_summary:
                pack_body += "• " + s + "<br/>"
            pedido.message_post(body=pack_body, author_id=CLAUDE_AUTHOR)
        flagged = []
        orange_count = 0
        for picking in pedido.picking_ids:
            for move in picking.move_ids:
                if move.state in ('done', 'cancel'):
                    continue
                color = move.x_studio_review_color or 0
                if color == 2:
                    orange_count += 1
                if color in PASS_COLORS:
                    continue
                if color in BLOCK_COLORS:
                    flagged.append(move.product_id.display_name + ': color=' + str(color))
                    continue
                paper = move.product_uom_qty or 0
                actual = move.quantity or 0
                delta = abs(paper - actual)
                if delta == 0:
                    continue
                elif delta <= MINOR_THRESHOLD:
                    sign = '+' if actual > paper else '-'
                    new_status = 'OK (auto ' + sign + str(int(delta)) + ')'
                    if move.x_studio_review_status != new_status:
                        move.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_review_status': new_status})
                else:
                    flagged.append(move.product_id.display_name + ': дельта ' + str(int(actual-paper)) + ' стеблей')
        if flagged:
            pedido.message_post(body="⛔ Claude finalize stopped at gate (" + str(len(flagged)) + " moves blocked): " + '; '.join(flagged), author_id=CLAUDE_AUTHOR)
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
            continue
        validated_picks = []
        for picking in pedido.picking_ids:
            if picking.state == 'done':
                continue
            picking.with_context(skip_backorder=True, tracking_disable=True, mail_create_nolog=True, mail_notrack=True).button_validate()
            if picking.state == 'done':
                validated_picks.append(picking.name)
        if validated_picks:
            # ===== Detailed summary message =====
            line_count = len(pedido.order_line)
            pick_names = ', '.join(validated_picks)
            wh_name = ''
            if pedido.picking_type_id and pedido.picking_type_id.warehouse_id:
                wh_name = pedido.picking_type_id.warehouse_id.name
            # Collect orange lines from item_comment
            orange_lines_list = []
            green_count = 0
            yellow_count = 0
            for line in pedido.order_line:
                comment = line.x_studio_item_comment or ''
                if not comment:
                    continue
                first = comment.split('\n')[0] if '\n' in comment else comment
                if '🟠' in comment:
                    orange_lines_list.append('• ' + line.name + ' — ' + first)
                elif '🟡' in comment:
                    yellow_count += 1
                elif '✅' in comment:
                    green_count += 1
            done_body = "✅ " + pick_names + " done. " + str(line_count) + " строк сверены, paper-truth применён.<br/>"
            done_body += "Сумма pedido: " + str(round(pedido.amount_total, 2)) + "€."
            if wh_name:
                done_body += " Warehouse: " + wh_name + "."
            done_body += "<br/><br/>"
            if orange_lines_list:
                done_body += "🟠 " + str(len(orange_lines_list)) + " substantial fixes:<br/>"
                for ol in orange_lines_list:
                    done_body += ol + "<br/>"
                done_body += "<br/>"
            if yellow_count > 0:
                done_body += "🟡 " + str(yellow_count) + " minor fixes<br/>"
            done_body += "✅ " + str(green_count) + " green: clean paper-match"
            # Flush pending Odoo tracking messages so Claude summary gets HIGHER id (newest top)
            env.cr.flush()
            pedido.message_post(body=done_body, author_id=CLAUDE_AUTHOR)
            # ===== Auto-create activity if orange/yellow/red present =====
            if orange_lines_list or yellow_count > 0:
                # Idempotency: skip if substantial activity уже есть
                existing_activity = env['mail.activity'].search([
                    ('res_model', '=', 'purchase.order'),
                    ('res_id', '=', pedido.id),
                    ('user_id', '=', 2),
                ], limit=1)
                if not existing_activity:
                    purchase_model_id = env['ir.model'].search([('model', '=', 'purchase.order')], limit=1).id
                    activity_note = "<p><b>" + str(len(orange_lines_list)) + " substantial fixes (orange):</b></p>"
                    if orange_lines_list:
                        activity_note += "<ol>"
                        for ol in orange_lines_list:
                            activity_note += "<li>" + ol[2:] + "</li>"
                        activity_note += "</ol>"
                    if yellow_count > 0:
                        activity_note += "<p>+ " + str(yellow_count) + " minor (yellow) fixes — см. line.x_studio_item_comment.</p>"
                    activity_note += "<p>Зелёных " + str(green_count) + " — clean paper-match, ревью не требуется.</p>"
                    env['mail.activity'].create({
                        'res_model_id': purchase_model_id,
                        'res_id': pedido.id,
                        'activity_type_id': 4,  # To-Do
                        'user_id': 2,  # Andriy
                        'summary': '🟠 Принять ' + str(len(orange_lines_list)) + ' substantial фиксов',
                        'note': activity_note,
                    })
        pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})

    except Exception as e:
        pedido.message_post(body="❌ Claude finalize ERROR: " + str(e), author_id=CLAUDE_AUTHOR)
        pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
