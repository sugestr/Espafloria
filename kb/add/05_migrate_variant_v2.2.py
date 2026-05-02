# ============================================================================
# MIGRATION SCRIPT v2.2 - EXECUTE
# ============================================================================
# Mirror: Odoo ir.actions.server id=1176 (model=product.product, usage=ir_actions_server)
# Trigger: base.automation id=6 "Auto migrate on flag (v2)"
#          trigger=on_create_or_write, watched=x_studio_migrate_now (id 27133)
#          filter: [migrate_now=True, target_variant!=False, migration_status!=archived]
#
# Работает на product.product (variant recordset).
# Только для flat-source (1 template = 1 variant). Multi-variant source — отказ.
# Target может быть любой (flat или multivariant) — куда кладётся картинка
# определяется формой target:
#   - flat target:         target.product_tmpl_id.image_1920 (POS тайлы читают template)
#   - multivariant target: target.image_variant_1920 (чтобы отличаться от других variant)
#
# ПЕРЕНОСИТСЯ С SOURCE НА TARGET (только если поле target пусто/ноль):
#   template-level: image_1920 (если flat target), x_studio_codigo_fabrica,
#                   x_studio_holded_url, x_studio_holded_created,
#                   list_price, standard_price
#   variant-level:  image_variant_1920 (если multivariant target),
#                   default_code, barcode, description_purchase, description_sale
#
# СТАТУСЫ И ССЫЛКИ НА SOURCE (всегда ставятся, независимо от чего-либо):
#   target template: x_studio_legacy_source=source_template.id,
#                    x_studio_migration_status='migrated',
#                    available_in_pos=True  (v2.2: миграция = готовность к продаже через POS)
#   target variant:  x_studio_variant_legacy_source=source.id,
#                    x_studio_variant_migration_status='migrated'
#   source template: x_studio_migration_status='archived', active=False
#
# botanic_name: MERGE (не затираем теги target, добавляем source)
# supplierinfo: копируется с дедупликацией по (partner_id, product_code)
#              uom_id, date_start, currency_id, sequence, price — всё копируется через copy()
# ============================================================================

for source in records:
    source_template = source.product_tmpl_id

    # ======== ГАРДЫ ========
    if len(source_template.product_variant_ids) != 1:
        raise UserError("Source must be flat (1 template = 1 variant). Multi-variant sources are not supported by this migration script.")

    target = source.x_studio_target_variant
    if not target:
        raise UserError("Fill 'Replace With Variant' on the source card first.")

    target_template = target.product_tmpl_id

    if target.id == source.id:
        raise UserError("Target cannot be the source itself.")

    if target_template.id == source_template.id:
        raise UserError("Source and target must belong to DIFFERENT templates. Migration within one template is a loop.")

    if not target.active or not target_template.active:
        raise UserError("Target is archived. Unarchive before migrating.")

    if source.x_studio_migration_status == 'archived':
        raise UserError("Source already migrated (status=archived). Cannot migrate twice.")

    if target.x_studio_variant_legacy_source:
        raise UserError("Target is already used as migration destination for another source.")

    if target_template.categ_id:
        quarantine_ids = env['product.category'].search([('id', 'child_of', 207)]).ids
        if target_template.categ_id.id in quarantine_ids:
            raise UserError("Cannot migrate into quarantine category.")

    # ======== ФОРМА TARGET (flat или multivariant) ========
    target_is_flat = len(target_template.product_variant_ids) == 1

    # ======== СБОР ДАННЫХ ИЗ SOURCE ========
    old_code = source.default_code or ""
    old_barcode = source.barcode or ""
    old_name = source.display_name or ""
    old_categ_name = source_template.categ_id.complete_name if source_template.categ_id else ""
    old_codigo_fabrica = source_template.x_studio_codigo_fabrica or ""
    old_holded_url = source_template.x_studio_holded_url or ""
    old_holded_created = str(source_template.x_studio_holded_created) if source_template.x_studio_holded_created else ""
    old_image = source_template.image_1920
    old_desc_purchase = source.description_purchase or ""
    old_desc_sale = source.description_sale or ""
    old_botanic_ids = source_template.x_studio_botanic_name.ids if source_template.x_studio_botanic_name else []
    old_list_price = source_template.list_price or 0.0
    old_standard_price = source_template.standard_price or 0.0
    old_available_in_pos = source_template.available_in_pos

    # ======== MIGRATION NOTE ========
    note_parts = ["Migrated from old product:", old_name]
    if old_categ_name:
        note_parts.append("Old category: " + old_categ_name)
    if old_code:
        note_parts.append("Old SKU: " + old_code)
    if old_barcode:
        note_parts.append("Old barcode: " + old_barcode)
    if old_codigo_fabrica:
        note_parts.append("Old codigo fabrica: " + old_codigo_fabrica)
    if old_holded_created:
        note_parts.append("Holded created: " + old_holded_created)
    if old_holded_url:
        note_parts.append("Holded URL: " + old_holded_url)
    if old_list_price:
        note_parts.append("Old sales price: " + str(old_list_price))
    if old_standard_price:
        note_parts.append("Old cost: " + str(old_standard_price))
    note_parts.append("Old available in POS: " + str(old_available_in_pos))
    migration_note = "\n".join(note_parts)

    # ======== ОБНОВЛЕНИЕ TARGET (variant-level) ========
    target_vals = {
        'x_studio_variant_legacy_source': source.id,
        'x_studio_variant_migration_status': 'migrated',
    }

    # SKU / barcode — переносим. Действует для любого target (flat/multi)
    # Освобождение на source сделаем позже, иначе unique constraint упадёт
    if old_code:
        target_vals['default_code'] = old_code
    if old_barcode:
        target_vals['barcode'] = old_barcode

    # Descriptions
    if old_desc_purchase:
        target_vals['description_purchase'] = old_desc_purchase
    if old_desc_sale:
        target_vals['description_sale'] = old_desc_sale

    # Migration note (variant text field) — append, не затираем
    existing_note = target.x_studio_migration_note or ""
    target_vals['x_studio_migration_note'] = (existing_note + "\n\n" + migration_note) if existing_note else migration_note

    # Картинка на variant — только если multivariant target И поле пусто И source имеет фото
    if old_image and not target_is_flat and not target.image_variant_1920:
        target_vals['image_variant_1920'] = old_image

    # ======== ОСВОБОЖДЕНИЕ SKU НА SOURCE (перед письмом target) ========
    # Порядок: сначала освободить SKU на source (OLD_ префикс), потом выдать target
    source_sku_free = {}
    if old_code:
        source_sku_free['default_code'] = 'OLD_' + old_code
    if old_barcode:
        source_sku_free['barcode'] = 'OLD_' + old_barcode
    if source_sku_free:
        source.sudo().write(source_sku_free)

    # Теперь пишем на target variant
    target.sudo().write(target_vals)

    # ======== ОБНОВЛЕНИЕ TARGET TEMPLATE ========
    # ВСЕГДА: legacy_source (ссылка на source template) + migration_status='migrated'
    # Эти поля на template важны для UI: видны на форме в разделе MIGRATION,
    # показывают откуда пришла карточка и её статус.
    # v2.2: available_in_pos=True ставится всегда — сам факт миграции означает
    # что карточка готова к активной продаже через кассу. Если user потом
    # решит иначе — снимет флаг вручную.
    tmpl_vals = {
        'x_studio_legacy_source': source_template.id,
        'x_studio_migration_status': 'migrated',
        'available_in_pos': True,
    }

    # Картинка на template — только если flat target И поле пусто И source имеет фото
    if old_image and target_is_flat and not target_template.image_1920:
        tmpl_vals['image_1920'] = old_image

    # codigo_fabrica — только если target пусто
    if old_codigo_fabrica and not target_template.x_studio_codigo_fabrica:
        tmpl_vals['x_studio_codigo_fabrica'] = old_codigo_fabrica

    # Holded metadata — только если target пусто
    if old_holded_url and not target_template.x_studio_holded_url:
        tmpl_vals['x_studio_holded_url'] = old_holded_url
    if old_holded_created and not target_template.x_studio_holded_created:
        tmpl_vals['x_studio_holded_created'] = old_holded_created

    # Цены — только если target 0 (уважение к уже импортированным ценам)
    # list_price = sales price, standard_price = cost
    # ⚠️ Odoo ставит list_price=1.0 по умолчанию на новом template — см. invariant #38.
    # При создании skeleton ВСЕГДА явно передавать list_price: 0.0, иначе правило
    # "copy only if empty" не сработает (1.0 truthy) и цена с source не переедет.
    if old_list_price and not target_template.list_price:
        tmpl_vals['list_price'] = old_list_price
    if old_standard_price and not target_template.standard_price:
        tmpl_vals['standard_price'] = old_standard_price

    # Botanical tags — merge (не затираем target теги, добавляем source)
    if old_botanic_ids:
        existing_ids = set(target_template.x_studio_botanic_name.ids) if target_template.x_studio_botanic_name else set()
        merged = list(existing_ids | set(old_botanic_ids))
        tmpl_vals['x_studio_botanic_name'] = [(6, 0, merged)]

    target_template.sudo().write(tmpl_vals)

    # ======== ПЕРЕНОС SUPPLIERINFO С ДЕДУПЛИКАЦИЕЙ ========
    # Bot обученные vendor codes должны переехать на target.
    # Дедуп по (partner_id, product_code) против тех что уже есть на target template.
    # copy() автоматически переносит все поля включая uom_id, date_start, currency_id, sequence, price.
    existing_keys = set()
    for si in target_template.seller_ids:
        existing_keys.add((si.partner_id.id, si.product_code or ""))

    old_supplierinfos = env['product.supplierinfo'].search([
        ('product_tmpl_id', '=', source_template.id)
    ])
    for si in old_supplierinfos:
        key = (si.partner_id.id, si.product_code or "")
        if key in existing_keys:
            continue
        # Для flat target product_id=False (привязываем ко всему template)
        # Для multivariant — привязываем к конкретному variant
        si.sudo().copy({
            'product_tmpl_id': target_template.id,
            'product_id': False if target_is_flat else target.id,
        })
        existing_keys.add(key)

    # ======== АРХИВИРОВАНИЕ SOURCE ========
    # Сначала ставим статус, затем архивируем (два write из-за Odoo sync особенностей).
    # ⚠️ invariant #42: archive делать только через template-level write, cascade на variant работает корректно.
    source_template.sudo().write({'x_studio_migration_status': 'archived'})
    source_template.sudo().write({'active': False})

    # Сбрасываем флаг чтобы автоматика не зациклилась.
    try:
        source.sudo().write({'x_studio_migrate_now': False})
    except Exception:
        # Если archived variant не разрешает write — игнорируем
        pass
