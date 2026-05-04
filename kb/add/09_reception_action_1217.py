# Server action: 🤖 Claude AI Reconcile Finalize  (v8.1)
# v8.1 (2026-05-04): hotfix — fields.Datetime.now() → datetime.datetime.now() в safe_eval.
#                    `fields` НЕ в безопасном scope server-action; `datetime` есть. Из-за этого
#                    v8.0 retroactive date block тихо ловился в try/except, и **все** pedidos
#                    из bulk 1-5 получали NOW вместо paper.fecha+1. См. CHANGELOG 2026-05-04.
# v8.0 (2026-05-03): retroactive delivery date — picking.date_done + stock.move.date +
#                    purchase.order.date_approve. Logic: paper.fecha (=pedido.date_order
#                    из Holded import) + 1 day если старше недели; иначе NOW. Stock-side
#                    only (purchase_method='receive' для цветов, bills отдельным flow).
# v7.9 (2026-05-01): hotfix — field rename `product_uom` → `uom_id` на stock.move в Odoo 19.
#                    v7.8 падал с Invalid field 'product_uom' на pack lines.
# v7.8 (2026-05-01): zero-backorder fix для pack lines + auto-cancel-delete backorder если возник.
#                    Phase A2 для pack (uom_id=31) теперь пишет product_uom_id=1 (Tallo) +
#                    product_uom_qty=stems → Odoo не пересчитывает по 1:10 → backorder не создаётся.
#                    После button_validate проходим по picking_ids, ищем orphan backorder
#                    (backorder_id != False, state != done) → action_cancel() + unlink().
# v7.7 (2026-04-30): УПРОЩЕНИЕ — summary message + activity убраны из action 1217.
#                    Subagent сам постит summary + creates activity через MCP create_record
#                    после своего trigger/verify. Это работает (pilot 1-5 confirmed) — direct
#                    create на mail.message bypass sanitize, HTML рендерится правильно.
# v7.6: попытка env['mail.message'].create() server-side (escape всё равно был на v7.5)
# v7.5: body starts with <p> (Odoo escape'ила inner tags)
# v7.3-v7.4: <br/>/counts experiments
# v7.2: detailed summary + auto-activity (HTML escape проблема)
# v7: Phase A2 always writes quantity + gate-by-color
# v6: tracking_disable + remove generic "✅ done"
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
                    # zero-backorder v7.9: switch move uom to Tallo + qty in stems
                    # so Odoo expected = received = stems → no backorder
                    # v7.9: field name is 'uom_id' on stock.move в Odoo 19 (НЕ 'product_uom')
                    vals['uom_id'] = 1  # Tallo (line stays Paquete, only move uom switched)
                    vals['product_uom_qty'] = stems
                    vals['quantity'] = stems
                    avg = (stems / paq_count) if paq_count > 0 else 0
                    pack_lines_summary.append(line.name + ': ' + str(int(paq_count)) + ' пак × ' + str(round(avg, 1)) + ' = ' + str(int(stems)) + ' шт')
                else:
                    target_qty = line.x_studio_expected_qty if line.x_studio_expected_qty else line.product_qty
                    vals['quantity'] = target_qty
                if vals:
                    move.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write(vals)
        # Phase A2 pack-detection summary — subagent сам постит после verify (формат pilot 1).
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
        # v7.8: cleanup orphan backorder pickings (если zero-backorder gate всё-таки failed)
        # owner override 82.51: cancel + unlink, не оставлять мусором
        for picking in pedido.picking_ids:
            if picking.backorder_id and picking.state not in ('done', 'cancel'):
                try:
                    picking.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).action_cancel()
                    picking.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).unlink()
                except Exception as eb:
                    pedido.message_post(body="⚠️ backorder cleanup failed " + picking.name + ": " + str(eb), author_id=CLAUDE_AUTHOR)
        # v8.0 (2026-05-03): retroactive delivery date (paper.fecha+1 для старых, NOW для свежих)
        # Owner правило: если pedido старше недели — backdate +1 day (typical supplier delay).
        # Если pedido в пределах недели — leave NOW. Применяется к picking.date_done +
        # stock.move.date + purchase.order.date_approve. Stock-side only (purchase_method='receive'
        # для цветов = bills отдельным flow). Use pedido.date_order = paper.FECHA (Holded import).
        try:
            now_dt = datetime.datetime.now()  # v8.1: fields НЕ в safe_eval, datetime есть
            week_ago = now_dt - datetime.timedelta(days=7)
            paper_fecha = pedido.date_order
            if paper_fecha and paper_fecha < week_ago:
                delivery_date = paper_fecha + datetime.timedelta(days=1)
            else:
                delivery_date = now_dt
            for picking in pedido.picking_ids:
                if picking.state == 'done':
                    picking.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'date_done': delivery_date})
                    for move in picking.move_ids:
                        if move.state == 'done':
                            move.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'date': delivery_date})
            pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'date_approve': delivery_date})
        except Exception as ed:
            pedido.message_post(body="⚠️ retro date setting failed: " + str(ed), author_id=CLAUDE_AUTHOR)
        # Picking-done summary message + activity — subagent делает сам после verify
        pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})

    except Exception as e:
        pedido.message_post(body="❌ Claude finalize ERROR: " + str(e), author_id=CLAUDE_AUTHOR)
        pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
