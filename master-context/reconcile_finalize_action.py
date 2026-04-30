# Server action: 🤖 Claude AI Reconcile Finalize  (v7)
# id=1217, model=purchase.order, state=code, usage=base_automation
# Triggered by base.automation 15 watching x_studio_claude_finalize=True on purchase.order
# Filter: state in ('draft', 'purchase')
#
# v7 (2026-04-30):
#   1. Phase A2 ВСЕГДА пишет quantity = expected_qty с tracking_disable (даже если совпадает с product_qty).
#      Без этого button_validate сам делает write quantity = product_uom_qty без нашего context, триггерит auto-Odoo-tracking
#      сообщения "Полученное количество обновлено" под user который запустил MCP (Andriy).
#      Pilot 12186835 на v6 показал — даже с tracking_disable на picking, button_validate спамил chatter.
#   2. Gate-check теперь по color (10/8/3/2 → pass; 1/4 → flag), не по startswith status text.
#      Закрывает баг "auto-minor -0" на оранжевых строках (emoji-prefix '🟠 OK' ломал startswith('OK')
#      из v5/v6 → soft-gate перезатирал статус 1146 на бессмысленный "OK (auto-minor -0)").
#   3. Если delta=0 — НЕ пишем status (1146 уже выставила правильный 'OK' или '🟠 OK').
#      delta>0 — текст без silly "-0" знака.
#   4. Picking-done summary message в chatter (author_id=56) — восстановлен per owner 2026-04-30:
#      «сводный отчёт хорошо. сводный итог имеет смысл сказать сообщением, и потом сообщение когда пикинг делаем».
#      Формат: "✅ {picking_name} done. {N_lines} строк, paper {total}€ ↔ Odoo {total}€. {N_orange} substantial (см. activity)."
#   5. Pack detection summary message — если Phase A2 нашёл pack lines, постится список перед validate.
#      Формат: "📦 Phase A2: найдено N пачек: STATICE 5×8=40, ..."
#
# v6 (2026-04-30, retained):
#   - tracking_disable + mail_create_nolog + mail_notrack на all writes (защита от auto-tracking)
#   - removed pedido-level success summary "✅ Claude finalize done."
#
# Three branches:
#   A) ROLLBACK PATH — note contains 'ROLLBACK_HOLDED_API'
#   B) RETRY PATH — state=='purchase'
#   C) DRAFT PATH — state=='draft'
#
# All explicit chatter posts use author_id=56 (🤖 Claude AI Reconciliation).
#
# Mirror per [99_invariants §2] — keep in sync with prod ir.actions.server id=1217.
#
# safe_eval restrictions per [99_invariants §G4]:
#   - No `obj.field = value` — use `obj.write({'field': value})`
#   - No `type(e).__name__`, no `hasattr` — use `'field_name' in record._fields`

UOM_PAQUETE_ID = 31
MINOR_THRESHOLD = 5
ROLLBACK_MARKER = 'ROLLBACK_HOLDED_API'
CLAUDE_AUTHOR = 56
PASS_COLORS = (10, 8, 3, 2)  # green, dark blue, yellow, orange — gate passes
BLOCK_COLORS = (1, 4)         # red, blue (legacy 'нужен ввод') — gate blocks

for pedido in records:
    try:
        # ===== A) ROLLBACK PATH =====
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

        # ===== B) RETRY PATH =====
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
                    # color == 0 — fallback по qty delta
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

        # ===== C) DRAFT PATH =====
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
        # ===== Phase A2: ALWAYS write quantity = expected_qty с tracking_disable =====
        # (даже если совпадает с product_qty — иначе button_validate сам напишет и спам)
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
                    # Pack: paper paq × stems_per_paq
                    paq_count = line.product_qty
                    stems = line.x_studio_expected_qty or paq_count
                    vals['x_studio_received_packs'] = paq_count
                    vals['quantity'] = stems
                    avg = (stems / paq_count) if paq_count > 0 else 0
                    pack_lines_summary.append(line.name + ': ' + str(int(paq_count)) + ' пак × ' + str(round(avg, 1)) + ' = ' + str(int(stems)) + ' шт')
                else:
                    # Stem: always write quantity = expected_qty (или product_qty fallback)
                    target_qty = line.x_studio_expected_qty if line.x_studio_expected_qty else line.product_qty
                    vals['quantity'] = target_qty
                if vals:
                    move.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write(vals)
        # Pack-detection summary message (если есть pack lines)
        if pack_lines_summary:
            pack_body = "<p>📦 <b>Phase A2 (pack detection)</b> — найдено " + str(len(pack_lines_summary)) + " пачек:</p><ul>"
            for s in pack_lines_summary:
                pack_body += "<li>" + s + "</li>"
            pack_body += "</ul>"
            pedido.message_post(body=pack_body, author_id=CLAUDE_AUTHOR)
        # ===== Final gate (по color) =====
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
                # color == 0 — fallback
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
        # ===== Validate pickings =====
        validated_picks = []
        for picking in pedido.picking_ids:
            if picking.state == 'done':
                continue
            picking.with_context(skip_backorder=True, tracking_disable=True, mail_create_nolog=True, mail_notrack=True).button_validate()
            if picking.state == 'done':
                validated_picks.append(picking.name)
        # ===== Picking-done summary chatter =====
        if validated_picks:
            line_count = len(pedido.order_line)
            pick_names = ', '.join(validated_picks)
            wh_name = ''
            if pedido.picking_type_id and pedido.picking_type_id.warehouse_id:
                wh_name = pedido.picking_type_id.warehouse_id.name
            done_body = "<p>✅ <b>" + pick_names + " done.</b> " + str(line_count) + " строк сверены, paper-truth применён."
            done_body += " Сумма pedido: " + str(round(pedido.amount_total, 2)) + "€."
            if wh_name:
                done_body += " Warehouse: <b>" + wh_name + "</b>."
            if orange_count > 0:
                done_body += " " + str(orange_count) + " substantial (см. activity)."
            done_body += "</p>"
            pedido.message_post(body=done_body, author_id=CLAUDE_AUTHOR)
        pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})

    except Exception as e:
        pedido.message_post(body="❌ Claude finalize ERROR: " + str(e), author_id=CLAUDE_AUTHOR)
        pedido.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({'x_studio_claude_finalize': False})
