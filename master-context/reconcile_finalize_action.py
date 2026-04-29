# Server action: 🤖 Claude AI Reconcile Finalize  (v5)
# id=1217, model=purchase.order, state=code, usage=base_automation
# Triggered by base.automation 15 watching x_studio_claude_finalize=True on purchase.order
# Filter: state in ('draft', 'purchase')
#
# Three branches:
#   A) ROLLBACK PATH — note contains 'ROLLBACK_HOLDED_API'
#      → for each done picking: open stock.return.picking wizard, set quantities, validate reverse picking
#      → button_draft pedido
#      → clear Phase A on lines (price=0, supplier_sku=False, supplier_product_name=False, item_comment=False)
#      → clear note + flag
#   B) RETRY PATH — state=='purchase'
#      → for each pending picking, soft-gate (≤MINOR_THRESHOLD=5 stems auto-OK; pack with received_packs auto-OK 📦)
#      → if any move >MINOR, flag stop; else validate (skip_backorder)
#   C) DRAFT PATH
#      → pre-flight (state==draft, has lines, amount>0, all lines have supplier_sku)
#      → button_confirm
#      → Phase A2: write x_studio_received_packs + quantity on stock.move
#      → soft-gate
#      → validate (skip_backorder)
#
# All chatter messages posted with author_id=56 (🤖 Claude AI Reconciliation partner)
#
# Mirror per [99_invariants §2] — keep in sync with prod ir.actions.server id=1217.
#
# safe_eval restrictions per [99_invariants §G4]:
#   - No `obj.field = value` — must use `obj.write({'field': value})` (STORE_ATTR forbidden)
#   - No `type(e).__name__` (`__name__` access forbidden)
#   - No `hasattr` — use `'field_name' in record._fields`

UOM_PAQUETE_ID = 31
MINOR_THRESHOLD = 5
ROLLBACK_MARKER = 'ROLLBACK_HOLDED_API'
CLAUDE_AUTHOR = 56  # res.partner id of "🤖 Claude AI Reconciliation"

for pedido in records:
    try:
        # ===== A) ROLLBACK PATH =====
        if ROLLBACK_MARKER in (pedido.note or ''):
            done_pickings = pedido.picking_ids.filtered(lambda p: p.state == 'done')
            for picking in done_pickings:
                try:
                    wizard = env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking', active_ids=[picking.id]).create({})
                    # Set quantities on return lines from original move quantities (default is 0)
                    for return_line in wizard.product_return_moves:
                        if return_line.move_id:
                            return_line.write({'quantity': return_line.move_id.quantity})
                    return_action = wizard.action_create_returns()
                    new_pid = return_action.get('res_id') if isinstance(return_action, dict) else None
                    if new_pid:
                        new_picking = env['stock.picking'].browse(new_pid)
                        for m in new_picking.move_ids:
                            m.write({'quantity': m.product_uom_qty})
                        new_picking.with_context(skip_backorder=True).button_validate()
                        pedido.message_post(body="✅ reverse picking " + new_picking.name + " validated", author_id=CLAUDE_AUTHOR)
                except Exception as ep:
                    pedido.message_post(body="❌ rollback picking error: " + str(ep), author_id=CLAUDE_AUTHOR)
            try:
                pedido.button_draft()
            except Exception as e2:
                pedido.message_post(body="⚠️ button_draft failed: " + str(e2), author_id=CLAUDE_AUTHOR)
            for line in pedido.order_line:
                line.write({
                    'price_unit': 0,
                    'x_studio_supplier_sku': False,
                    'x_studio_supplier_product_name': False,
                    'x_studio_item_comment': False,
                })
            pedido.write({'note': False, 'x_studio_claude_finalize': False})
            pedido.message_post(body="✅ Claude rollback finished. State=" + pedido.state, author_id=CLAUDE_AUTHOR)
            continue

        # ===== B) RETRY PATH =====
        if pedido.state == 'purchase':
            pending = pedido.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if not pending:
                pedido.message_post(body="ℹ️ Claude finalize: state=purchase, все pickings done.", author_id=CLAUDE_AUTHOR)
                pedido.write({'x_studio_claude_finalize': False})
                continue
            flagged = []
            for picking in pending:
                for move in picking.move_ids:
                    if move.state in ('done', 'cancel'):
                        continue
                    status = move.x_studio_review_status or ''
                    if status.startswith('OK'):
                        continue
                    if move.x_studio_received_packs and move.x_studio_received_packs > 0:
                        move.write({'x_studio_review_status': 'OK 📦 (auto-retry)'})
                        continue
                    paper = move.product_uom_qty or 0
                    actual = move.quantity or 0
                    delta = abs(paper - actual)
                    if delta <= MINOR_THRESHOLD:
                        sign = '+' if actual > paper else '-'
                        move.write({'x_studio_review_status': 'OK (auto-minor ' + sign + str(int(delta)) + ')'})
                    else:
                        flagged.append(move.product_id.display_name + ': дельта ' + str(int(actual-paper)) + ' стеблей')
            if flagged:
                pedido.message_post(body="⛔ Claude validate retry stopped (" + str(len(flagged)) + " moves >MINOR): " + '; '.join(flagged), author_id=CLAUDE_AUTHOR)
                pedido.write({'x_studio_claude_finalize': False})
                continue
            for picking in pending:
                picking.with_context(skip_backorder=True).button_validate()
            pedido.write({'x_studio_claude_finalize': False})
            pedido.message_post(body="✅ Claude validate retry done: " + str(len(pending)) + " picking validated.", author_id=CLAUDE_AUTHOR)
            continue

        # ===== C) DRAFT PATH =====
        if pedido.state != 'draft':
            pedido.message_post(body="⛔ Claude finalize skipped: state=" + str(pedido.state), author_id=CLAUDE_AUTHOR)
            pedido.write({'x_studio_claude_finalize': False})
            continue
        if not pedido.order_line:
            pedido.message_post(body="⛔ Claude finalize skipped: no order_line", author_id=CLAUDE_AUTHOR)
            pedido.write({'x_studio_claude_finalize': False})
            continue
        if pedido.amount_total <= 0:
            pedido.message_post(body="⛔ Claude finalize skipped: amount_total=0", author_id=CLAUDE_AUTHOR)
            pedido.write({'x_studio_claude_finalize': False})
            continue
        unfilled = pedido.order_line.filtered(lambda l: not l.x_studio_supplier_sku)
        if unfilled:
            pedido.message_post(body="⛔ Claude finalize skipped: " + str(len(unfilled)) + " lines without supplier_sku", author_id=CLAUDE_AUTHOR)
            pedido.write({'x_studio_claude_finalize': False})
            continue
        pedido.button_confirm()
        for picking in pedido.picking_ids:
            if picking.state == 'done':
                continue
            for move in picking.move_ids:
                line = move.purchase_line_id
                if not line:
                    continue
                vals = {}
                if line.uom_id.id == UOM_PAQUETE_ID:
                    vals['x_studio_received_packs'] = line.product_qty
                    if line.x_studio_expected_qty:
                        vals['quantity'] = line.x_studio_expected_qty
                elif line.x_studio_expected_qty and abs(line.x_studio_expected_qty - line.product_qty) > 0.01:
                    vals['quantity'] = line.x_studio_expected_qty
                if vals:
                    move.write(vals)
        flagged = []
        for picking in pedido.picking_ids:
            for move in picking.move_ids:
                if move.state in ('done', 'cancel'):
                    continue
                status = move.x_studio_review_status or ''
                if status.startswith('OK'):
                    continue
                if move.x_studio_received_packs and move.x_studio_received_packs > 0:
                    move.write({'x_studio_review_status': 'OK 📦 (auto)'})
                    continue
                paper = move.product_uom_qty or 0
                actual = move.quantity or 0
                delta = abs(paper - actual)
                if delta <= MINOR_THRESHOLD:
                    sign = '+' if actual > paper else '-'
                    move.write({'x_studio_review_status': 'OK (auto-minor ' + sign + str(int(delta)) + ')'})
                else:
                    flagged.append(move.product_id.display_name + ': дельта ' + str(int(actual-paper)) + ' стеблей')
        if flagged:
            pedido.message_post(body="⛔ Claude finalize stopped at gate (" + str(len(flagged)) + " moves >MINOR): " + '; '.join(flagged), author_id=CLAUDE_AUTHOR)
            pedido.write({'x_studio_claude_finalize': False})
            continue
        for picking in pedido.picking_ids:
            if picking.state == 'done':
                continue
            picking.with_context(skip_backorder=True).button_validate()
        pedido.write({'x_studio_claude_finalize': False})
        pedido.message_post(body="✅ Claude finalize done.", author_id=CLAUDE_AUTHOR)

    except Exception as e:
        pedido.message_post(body="❌ Claude finalize ERROR: " + str(e), author_id=CLAUDE_AUTHOR)
        pedido.write({'x_studio_claude_finalize': False})
