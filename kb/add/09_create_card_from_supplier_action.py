# Mirror of ir.actions.server id=1239 "Create card from supplier"
# Triggered from purchase.order.line tree button "New +" in view 4467 (purchase.order.form Studio).
# Last sync with prod: 2026-05-09
#
# Purpose: Logist on Mode B pedido recognition flow clicks New + on a line whose
# match_confidence='create_new' (no good candidate found) -> this action:
#   1. Creates product.template + auto-variant in ⛔ Карантин Holded (categ 207)
#   2. SKU = next free in 8400xxx (карантинная band)
#   3. Pricing: standard_price=line.price_unit, list_price=cost*3
#   4. Taxes: sales=82 (10% R), purchase=68 (10% R) — hardcoded for flowers
#   5. Holded Link (x_studio_holded_url) = supplier_photo_url (clickable URL widget)
#   6. Tries base_import.execute_import to auto-fetch URL→image_1920 (FAILS on Odoo Online — see §13.10)
#   7. Creates product.supplierinfo with composite identity key for L1 future matching
#   8. Sets line.product_id=new_variant, match_confidence='confident'
#   9. Back-link via chatter on pedido + on new template (with WHY/SOURCE/PRICING)
#  10. mail.activity TODO "Review auto-created card" deadline +7 days
#  11. Returns ir.actions.act_window target='new' to open new card form in modal
#
# IMPORTANT: image auto-fetch via base_import.execute_import does NOT work on Odoo Online —
# it expects base64 in image_1920 field, throws "Incorrect padding" on URL string.
# Logist must manually click Holded Link → save image → upload to product image. See §13.10.

# Step 3: Create card from supplier data.
# Try base_import.execute_import to auto-fetch URL -> image_1920 bytes (stored locally).
# If fails -> manual upload required (logist clicks Holded Link in form).

for line in records:
    if not line.x_studio_supplier_product_name and not line.name:
        continue

    name = line.x_studio_supplier_product_name or line.name or 'UNKNOWN'
    name_clean = name.split('|')[0].strip() if '|' in name else name.strip()

    today = datetime.datetime.now()

    existing_codes = env['product.template'].sudo().search([('default_code', '=ilike', '8400%')]).mapped('default_code')
    max_n = 0
    for code in existing_codes:
        if not code:
            continue
        suffix = code[4:]
        if suffix.isdigit():
            try:
                n = int(suffix)
                if n > max_n:
                    max_n = n
            except Exception:
                pass
    next_n = max_n + 1
    pad = 3 if next_n < 1000 else len(str(next_n))
    sku = '8400' + str(next_n).zfill(pad)

    category_id = 207
    sale_tax_id = 82
    purchase_tax_id = 68

    cost = line.price_unit or 0.0
    list_price = round(cost * 3, 2) if cost > 0 else 0.0

    tmpl_name = '\U0001f6a7\U0001f7e0 ' + name_clean + ' (auto-created)'
    photo_url = line.x_studio_supplier_photo_url or ''

    pedido_link = ''
    pedido_name = ''
    factura_ref = ''
    if line.order_id:
        pedido_link = '/odoo/purchase/' + str(line.order_id.id)
        pedido_name = line.order_id.name or ''
        factura_ref = line.order_id.partner_ref or ''

    vendor_name = 'Serviflor'
    if line.order_id and line.order_id.partner_id and line.order_id.partner_id.id == 42:
        vendor_name = 'Verdnatura'

    desc = '\U0001f6a7 AUTO-CREATED CARD — review needed\n\n'
    desc += 'WHY: Logist clicked New + on pedido line where match_confidence=create_new — no existing card matched supplier identity.\n\n'
    desc += 'SOURCE PEDIDO: ' + pedido_name + ' (factura ' + factura_ref + ')\n'
    desc += 'VENDOR: ' + vendor_name + '\n'
    desc += 'SUPPLIER NAME: ' + name_clean + '\n'
    if line.x_studio_supplier_lot_code:
        desc += 'SUPPLIER LOT TRACE: ' + line.x_studio_supplier_lot_code + '\n'
    desc += '\nPRICING: cost=' + str(cost) + 'eur | list_price=' + str(list_price) + 'eur (cost x 3)\n'

    tmpl_vals = {
        'name': tmpl_name,
        'default_code': sku,
        'barcode': sku,
        'categ_id': category_id,
        'list_price': list_price,
        'standard_price': cost,
        'type': 'consu',
        'is_storable': True,
        'invoice_policy': 'order',
        'purchase_method': 'purchase',
        'taxes_id': [(6, 0, [sale_tax_id])],
        'supplier_taxes_id': [(6, 0, [purchase_tax_id])],
        'available_in_pos': False,
    }
    if photo_url:
        tmpl_vals['x_studio_holded_url'] = photo_url

    new_template = env['product.template'].sudo().create(tmpl_vals)
    new_variant = new_template.product_variant_ids[:1]
    if not new_variant:
        continue
    new_variant_id = new_variant.id

    # Try to auto-fetch photo via base_import (core Python, has requests access)
    image_status = 'NOT_TRIED'
    if photo_url:
        try:
            csv_content = ('default_code,image_1920\n' + sku + ',"' + photo_url + '"').encode('utf-8')
            import_record = env['base_import.import'].sudo().create({
                'res_model': 'product.template',
                'file': csv_content,
                'file_type': 'text/csv',
                'file_name': 'photo.csv',
            })
            options = {
                'has_headers': True,
                'separator': ',',
                'quoting': '"',
                'date_format': '',
                'datetime_format': '',
                'float_thousand_separator': ',',
                'float_decimal_separator': '.',
                'fields': [],
                'tracking_disable': True,
            }
            result = import_record.execute_import(
                ['default_code', 'image_1920'],
                ['default_code', 'image_1920'],
                options
            )
            if result and result.get('ids'):
                # Verify image was actually stored
                env.cache.invalidate()
                refreshed = env['product.template'].sudo().browse(new_template.id)
                if refreshed.image_1920:
                    image_status = 'AUTO_FETCHED_AND_STORED_LOCALLY'
                else:
                    image_status = 'IMPORT_OK_BUT_IMAGE_EMPTY'
            else:
                msgs = result.get('messages', []) if result else []
                image_status = 'IMPORT_FAILED: ' + str(msgs)[:200]
        except Exception as e:
            image_status = 'EXCEPTION: ' + str(e)[:200]

    desc += '\nIMAGE STATUS: ' + image_status + '\n'
    desc += '\nREVIEW CHECKLIST:\n'
    if image_status != 'AUTO_FETCHED_AND_STORED_LOCALLY':
        desc += '[ ] Click Holded Link field above (= supplier photo URL) -> save image -> upload to image_1920\n'
    desc += '[ ] Move out of Karantin to proper category when clean catalog is built\n'
    desc += '[ ] Verify taxes (10% R sale=82 / purchase=68 — may need 21% G for accessories)\n'
    desc += '[ ] Verify list_price (cost x 3 = ' + str(list_price) + 'eur)\n'
    desc += '[ ] Remove auto-prefix from name when finalized\n'
    desc += '[ ] Verify SKU (' + sku + ')\n'
    new_template.sudo().write({'description': desc})

    parts = []
    parts.append('ART:' + name_clean.upper())
    parts.append('COLOR:')
    parts.append('ORIGIN:')
    parts.append('GROWER:')
    parts.append('POT:')
    parts.append('HEIGHT:')
    parts.append('PIECES_UNIT:')
    parts.append('UNITS_PER_PACK:')
    parts.append('PACK_MODE:UNIT')
    vendor_prefix = 'SV'
    if line.order_id and line.order_id.partner_id and line.order_id.partner_id.id == 42:
        vendor_prefix = 'VN'
    identity_key = vendor_prefix + '|' + '|'.join(parts)

    si_vals = {
        'partner_id': line.order_id.partner_id.id if line.order_id and line.order_id.partner_id else False,
        'product_id': new_variant_id,
        'product_tmpl_id': new_template.id,
        'product_name': name_clean,
        'price': cost,
        'min_qty': 1,
        'x_studio_supplier_identity_key': identity_key,
    }
    if line.x_studio_supplier_sku:
        si_vals['product_code'] = line.x_studio_supplier_sku
    if line.order_id and line.order_id.currency_id:
        si_vals['currency_id'] = line.order_id.currency_id.id
    if line.order_id and line.order_id.date_order:
        si_vals['date_start'] = line.order_id.date_order.date()
    env['product.supplierinfo'].sudo().create(si_vals)

    line.write({
        'product_id': new_variant_id,
        'x_studio_match_confidence': 'confident',
    })

    note = '\n\n\U0001f7e2 Auto-created card #' + str(new_template.id) + ' (' + sku + '). Image: ' + image_status
    new_comment = (line.x_studio_item_comment or '') + note
    line.write({'x_studio_item_comment': new_comment})

    photo_link_html = ''
    if photo_url:
        photo_link_html = '<br/><b>\U0001f4f7 Photo URL:</b> <a href="' + photo_url + '" target="_blank">\U0001f517 Open</a>'

    pedido_msg = '\U0001f7e2 <b>Created new card</b><br/>Card: <a href="/odoo/inventory/products/' + str(new_template.id) + '">' + tmpl_name + '</a> (sku <code>' + sku + '</code>)<br/>Cost: ' + str(cost) + 'eur → list x3 = ' + str(list_price) + 'eur<br/>Image: <b>' + image_status + '</b>' + photo_link_html
    if line.order_id:
        line.order_id.sudo().message_post(body=pedido_msg)

    why_msg = '\U0001f7e2 <b>Auto-created from supplier data</b><br/><br/>'
    why_msg += '<b>WHY:</b> Logist clicked New + on pedido line where match_confidence=create_new<br/>'
    why_msg += '<b>SOURCE:</b> <a href="' + pedido_link + '">' + pedido_name + '</a> (factura ' + factura_ref + ')<br/>'
    why_msg += '<b>VENDOR:</b> ' + vendor_name + '<br/>'
    why_msg += '<b>SUPPLIER NAME:</b> ' + name_clean + '<br/>'
    why_msg += '<b>PRICING:</b> cost=' + str(cost) + 'eur, list=' + str(list_price) + 'eur (x3)<br/>'
    why_msg += '<b>IMAGE STATUS:</b> ' + image_status + photo_link_html
    new_template.sudo().message_post(body=why_msg)

    activity_type_id = env.ref('mail.mail_activity_data_todo').id
    deadline_date = (today + datetime.timedelta(days=7)).date()
    env['mail.activity'].sudo().create({
        'res_model_id': env['ir.model']._get_id('product.template'),
        'res_id': new_template.id,
        'activity_type_id': activity_type_id,
        'summary': 'Review auto-created card from ' + vendor_name,
        'note': 'Card auto-created from pedido ' + pedido_name + '. Image status: ' + image_status,
        'date_deadline': deadline_date.strftime('%Y-%m-%d'),
        'user_id': line.order_id.user_id.id if (line.order_id and line.order_id.user_id) else env.uid,
    })

if len(records) == 1 and records.product_id:
    action = {
        'type': 'ir.actions.act_window',
        'res_model': 'product.template',
        'res_id': records.product_id.product_tmpl_id.id,
        'view_mode': 'form',
        'target': 'new',
    }
