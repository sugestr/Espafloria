# Migrate to selected variant
# Server action id=1145
# Model: product.template
# Binding: product form + list view
# Last updated in prod: 2026-04-18 (with supplierinfo copy patch)
#
# What it does:
# - Migrates a quarantine product.template to a new product.product variant
# - Validates target variant
# - Transfers SKU/barcode/images/descriptions/custom fields
# - COPIES product.supplierinfo (learned vendor codes) to new variant — patch 2026-04-18
# - Archives old product.template
#
# Usage (on quarantine product):
#   1. Fill x_studio_target_variant with new variant
#   2. Save
#   3. Click "Migrate to selected variant" button
#
# See: [06_catalog_migration_toolkit.md](../../06_catalog_migration_toolkit.md)

for record in records:
    if not record.x_studio_target_variant:
        raise UserError("Fill 'Replace With Variant' first.")

    target = record.x_studio_target_variant

    if target.id == record.id:
        raise UserError("Target variant cannot be the same record.")

    if not target.active:
        raise UserError("Target variant is archived.")

    # Нельзя использовать уже занятый variant
    if 'x_studio_variant_legacy_source' in target._fields and target.x_studio_variant_legacy_source:
        raise UserError("This variant has already been used as a migration target.")

    # Нельзя мигрировать в карантинную ветку категорий
    target_categ = False
    if 'product_tmpl_id' in target._fields and target.product_tmpl_id and target.product_tmpl_id.categ_id:
        target_categ = target.product_tmpl_id.categ_id

    if target_categ:
        quarantine_ids = env['product.category'].search([('id', 'child_of', 207)]).ids
        if target_categ.id in quarantine_ids:
            raise UserError("You cannot migrate into a quarantine category.")

    old_code = record.default_code or ""
    old_barcode = record.barcode or ""

    old_categ_name = ""
    if 'categ_id' in record._fields and record.categ_id:
        old_categ_name = record.categ_id.complete_name or ""

    old_codigo_fabrica = ""
    if 'x_studio_codigo_fabrica' in record._fields and record.x_studio_codigo_fabrica:
        old_codigo_fabrica = record.x_studio_codigo_fabrica

    old_holded_url = ""
    if 'x_studio_holded_url' in record._fields and record.x_studio_holded_url:
        old_holded_url = record.x_studio_holded_url

    old_holded_created = ""
    if 'x_studio_holded_created' in record._fields and record.x_studio_holded_created:
        old_holded_created = str(record.x_studio_holded_created)

    old_name = record.display_name or ""

    # 1. Освобождаем SKU / barcode на старой карточке
    old_updates = {
        'x_studio_migration_status': 'archived',
    }

    if old_code:
        old_updates['default_code'] = 'OLD_' + old_code

    if old_barcode:
        old_updates['barcode'] = 'OLD_' + old_barcode

    record.write(old_updates)

    # 2. Готовим текст миграционной заметки
    migration_note_parts = []
    migration_note_parts.append("Migrated from old product:")
    migration_note_parts.append(old_name)

    if old_categ_name:
        migration_note_parts.append("Old category: " + old_categ_name)

    if old_code:
        migration_note_parts.append("Old SKU: " + old_code)

    if old_barcode:
        migration_note_parts.append("Old barcode: " + old_barcode)

    if old_codigo_fabrica:
        migration_note_parts.append("Old codigo fabrica: " + old_codigo_fabrica)

    if old_holded_created:
        migration_note_parts.append("Holded created: " + old_holded_created)

    if old_holded_url:
        migration_note_parts.append("Holded URL: " + old_holded_url)

    migration_note_text = "\n".join(migration_note_parts)

    # 3. Переносим данные в новый variant
    target_updates = {
        'x_studio_variant_legacy_source': record.id,
        'x_studio_variant_migration_status': 'migrated',
    }

    # SKU / barcode
    if old_code:
        target_updates['default_code'] = old_code

    if old_barcode:
        target_updates['barcode'] = old_barcode

    # Фото именно в variant, не в template
    if 'image_1920' in record._fields and 'image_variant_1920' in target._fields and record.image_1920:
        target_updates['image_variant_1920'] = record.image_1920

    # Descriptions
    if 'description_purchase' in record._fields and 'description_purchase' in target._fields and record.description_purchase:
        target_updates['description_purchase'] = record.description_purchase

    if 'description_sale' in record._fields and 'description_sale' in target._fields and record.description_sale:
        target_updates['description_sale'] = record.description_sale

    # Holded custom fields
    if 'x_studio_codigo_fabrica' in record._fields and 'x_studio_codigo_fabrica' in target._fields:
        target_updates['x_studio_codigo_fabrica'] = record.x_studio_codigo_fabrica or False

    if 'x_studio_holded_url' in record._fields and 'x_studio_holded_url' in target._fields:
        target_updates['x_studio_holded_url'] = record.x_studio_holded_url or False

    if 'x_studio_holded_created' in record._fields and 'x_studio_holded_created' in target._fields:
        target_updates['x_studio_holded_created'] = record.x_studio_holded_created or False

    # Botanical tags
    if 'x_studio_botanic_name' in record._fields:
        if 'x_studio_botanic_name' in target._fields:
            target_updates['x_studio_botanic_name'] = [(6, 0, record.x_studio_botanic_name.ids)]
        elif 'x_studio_variant_botanic_name' in target._fields:
            target_updates['x_studio_variant_botanic_name'] = [(6, 0, record.x_studio_botanic_name.ids)]

    # Migration note
    if 'x_studio_migration_note' in target._fields:
        existing_note = target.x_studio_migration_note or ""
        if existing_note:
            target_updates['x_studio_migration_note'] = existing_note + "\n\n" + migration_note_text
        else:
            target_updates['x_studio_migration_note'] = migration_note_text

    target.write(target_updates)

    # 3.5. Копируем supplierinfo (обученные vendor codes) на новый variant
    # Патч от 2026-04-18: без этого шага learned vendor codes оставались
    # на архивной карточке и Make.com бот терял матчинг по supplier_sku.
    old_supplierinfos = env['product.supplierinfo'].search([
        ('product_tmpl_id', '=', record.id)
    ])
    for si in old_supplierinfos:
        si.copy({
            'product_tmpl_id': target.product_tmpl_id.id,
            'product_id': target.id,
        })

    # 4. Архивируем старую карточку
    record.write({
        'active': False,
    })
