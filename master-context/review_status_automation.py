# Review Status Automation
# Server action id=1146, triggered by base.automation id=1
# Watched fields: quantity, x_studio_received_packs
# Model: stock.move
# Last updated in prod: 2026-04-30 (extended palette: orange=2, dark blue=8)
#
# What it does:
# - Reads review state of a stock.move line
# - Detects if is_pack line (by paper_unit name: 'paq' / 'pack' / 'paquete')
# - Detects if line has substantial robot fix (item_comment contains '🟠')
# - Detects if line is robot clean fill (bot wrote item_comment + logist hasn't verified)
# - Computes severity and status text:
#   0 = green/dark blue (OK / robot clean fill)
#   1 = blue (needs input: "посчитать!" or "... и пачки?")
#   2 = yellow (mismatch with paper)
#   3 = red (mismatch with logist — overrides everything else)
# - Writes x_studio_review_status + x_studio_review_color
#
# Color palette (Odoo kanban color IDs):
#   1 = red          (severity 3 — расхождение с логистом / блокер для owner)
#   2 = orange       (NEW — substantial robot fix: created card / split MIX / reassign / pack-conversion)
#   3 = yellow       (severity 2 — расхождение с бумагой / minor)
#   4 = blue (legacy) (severity 1 — нужен ввод флориста)
#   8 = dark blue    (NEW — robot clean fill: бот заполнил без правок, логист не trogал)
#   10 = green       (severity 0 — perfect match: paper + florist + bot)

for rec in records:
    def fmt_num(v):
        v = float(v or 0)
        if v.is_integer():
            return str(int(v))
        return str(round(v, 2)).rstrip('0').rstrip('.')

    def fmt_diff(v):
        v = float(v or 0)
        if v.is_integer():
            v = int(v)
        return ('+' + str(v)) if v > 0 else str(v)

    unit = ((rec.x_studio_paper_unit.display_name or rec.x_studio_paper_unit.name or '') if rec.x_studio_paper_unit else '').lower()
    is_pack = 'paq' in unit or 'pack' in unit or 'paquete' in unit

    paper_qty = rec.x_studio_paper_qty or 0
    logist_qty = rec.x_studio_expected_qty_info or 0
    qty = rec.quantity if rec.quantity is not False and rec.quantity is not None else -1
    packs_raw = rec.x_studio_received_packs
    packs = packs_raw if packs_raw is not False and packs_raw is not None else 0

    units_missing = qty < 0
    packs_missing = is_pack and (packs <= 0)

    # Read item_comment from purchase.order.line for fix-type detection
    item_comment = ''
    if rec.purchase_line_id and rec.purchase_line_id.x_studio_item_comment:
        item_comment = rec.purchase_line_id.x_studio_item_comment or ''

    has_substantial_fix = '🟠' in item_comment
    bot_filled = ('Claude AI' in item_comment) or ('🤖' in item_comment) or ('✅ Paper match' in item_comment) or ('Phase A' in item_comment)

    parts = []
    severity = 0
    # 0 = OK or robot-clean
    # 1 = blue (input needed)
    # 2 = yellow (paper mismatch)
    # 3 = red (logist mismatch — overrides)

    if units_missing:
        parts.append('посчитать!')
        severity = max(severity, 1)

    if packs_missing:
        parts.append('... и пачки?')
        severity = max(severity, 1)

    if not units_missing and not is_pack:
        d = qty - paper_qty
        if d != 0:
            parts.append('от бумаги ' + fmt_diff(d))
            severity = max(severity, 2)

    if is_pack and not packs_missing:
        d = packs - paper_qty
        if d < 0:
            parts.append(' / пачек МЕНЬШЕ на ' + fmt_num(abs(d)))
            severity = max(severity, 2)
        elif d > 0:
            parts.append(' / пачек БОЛЬШЕ на ' + fmt_num(d))
            severity = max(severity, 2)

    if logist_qty > 0 and not units_missing:
        d = qty - logist_qty
        if d != 0:
            parts.append(' / от логиста ' + fmt_diff(d))
            severity = 3

    avg = ''
    if is_pack and not packs_missing and not units_missing and packs > 0:
        avg = '📦 ' + fmt_num(qty / packs) + ' шт/пак'

    status = ' '.join(parts) if parts else 'OK'
    if avg:
        status += ' ' + avg

    # Color selection — extended palette
    if severity == 3:
        color = 1      # red — расхождение с логистом
    elif has_substantial_fix and severity <= 2:
        color = 2      # orange — substantial robot fix (overrides yellow if no logist conflict)
        if severity == 0:
            status = '🟠 ' + status
    elif severity == 2:
        color = 3      # yellow — расхождение с бумагой
    elif severity == 1:
        color = 4      # blue (legacy) — нужен ввод флориста
    else:
        # severity 0 — all aligned, no fixes
        if bot_filled and logist_qty == 0:
            color = 8  # dark blue — robot clean fill (бот заполнил, логист не trogал)
            status = '🤖 ' + status if not status.startswith('🤖') else status
        else:
            color = 10 # green — perfect match (paper + florist + bot OR just legacy receipt)

    vals = {}
    if rec.x_studio_review_status != status:
        vals['x_studio_review_status'] = status
    if rec.x_studio_review_color != color:
        vals['x_studio_review_color'] = color

    if vals:
        rec.write(vals)
