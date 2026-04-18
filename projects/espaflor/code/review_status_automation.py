# Review Status Automation
# Server action id=1146, triggered by base.automation id=1
# Watched fields: quantity, x_studio_received_packs
# Model: stock.move
# Last updated in prod: 2026-04-18
#
# What it does:
# - Reads review state of a stock.move line
# - Detects if is_pack line (by paper_unit name: 'paq' / 'pack' / 'paquete')
# - Computes severity and status text:
#   0 = green (OK)
#   1 = blue (needs input: "посчитать!" or "... и пачки?")
#   2 = yellow (mismatch with paper)
#   3 = red (mismatch with logist — overrides everything else)
# - Writes x_studio_review_status + x_studio_review_color

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

    parts = []
    severity = 0
    # 0 green, 1 blue/input needed, 2 yellow, 3 red

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

    if severity == 3:
        color = 1      # red
    elif severity == 2:
        color = 3      # yellow
    elif severity == 1:
        color = 4      # blue (проверь на твоей базе)
    else:
        color = 10     # green

    vals = {}
    if rec.x_studio_review_status != status:
        vals['x_studio_review_status'] = status
    if rec.x_studio_review_color != color:
        vals['x_studio_review_color'] = color

    if vals:
        rec.write(vals)
