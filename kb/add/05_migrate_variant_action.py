# ============================================================================
# MIGRATION SCRIPT v2 - UI TRIGGER (id=1145, model=product.template)
# ============================================================================
# Запускается из UI: Purchase → Products → карточка → Actions → Migrate to selected variant
#
# Короткий скрипт: находит variant, выставляет x_studio_migrate_now=True,
# автоматика "Auto migrate on flag (v2)" срабатывает и вызывает
# "Migrate: execute (v2)" — единый источник истины для миграционной логики.
#
# Синхронно: автоматика выполняется в той же транзакции, UserError из execute
# пропагируется к юзеру если что-то не так с target/защитами.
# ============================================================================

for template in records:
    if len(template.product_variant_ids) != 1:
        raise UserError("Source must be flat (1 template = 1 variant). Multi-variant sources are not supported.")

    variant = template.product_variant_ids[0]

    if not template.x_studio_target_variant:
        raise UserError("Fill 'Replace With Variant' first.")

    # Флипаем флаг в variant — automation срабатывает синхронно и делает миграцию.
    variant.write({'x_studio_migrate_now': True})
