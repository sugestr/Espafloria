<!-- v: 2 | updated: 2026-04-19T15:00Z -->
# 06. Catalog Migration Toolkit

Статус: 🟢 **PROD** (server action работает) / 🟡 **READY** (инфраструктура готова, массовая миграция не запущена).

---

## Философия миграции

**Главное правило: историю не переносим.**

Старая карточка (из карантина):
- Остаётся в системе как **историческая запись**
- Старые pedido / RFQ / продажи **по-прежнему ссылаются на неё**
- **Архивируется** (`active=False`) после миграции
- Её `default_code` / `barcode` заменяются на `OLD_<old>` чтобы не конфликтовать с новой

Новая карточка (target variant):
- Получает настоящий SKU / barcode
- Копию всех learned vendor codes (`product.supplierinfo`)
- Ссылку на legacy source
- Становится единственным активным владельцем SKU

**Не делается:**
- Перепривязка старых документов
- «Слияние» старой в variant (физически невозможно в Odoo)
- Копирование mail.message / chatter

---

## Server Action: `Migrate to selected variant` (id=1145)

**Модель:** `product.template`
**Тип:** Execute Code
**Binding:** product form + list view
**Кнопка:** видна когда `x_studio_target_variant` заполнено и карточка не архивная

**Полный код:** см. `migrate_variant_action.py` (обновлён 2026-04-18 с патчем copy supplierinfo).

### Что делает action:

**1. Валидация target:**
```python
if not record.x_studio_target_variant:
    raise UserError("Fill 'Replace With Variant' first.")
target = record.x_studio_target_variant
if target.id == record.id:
    raise UserError("Target variant cannot be the same record.")
if not target.active:
    raise UserError("Target variant is archived.")
if target.x_studio_variant_legacy_source:
    raise UserError("This variant has already been used as a migration target.")
# target не в карантинной ветке
if target.product_tmpl_id.categ_id.id in quarantine_ids:
    raise UserError("You cannot migrate into a quarantine category.")
```

**2. Освобождение SKU/barcode на старой карточке:**
```python
record.write({
    'default_code': 'OLD_' + old_code,  # 8400010 → OLD_8400010
    'barcode':     'OLD_' + old_barcode,
    'x_studio_migration_status': 'archived',
})
```

**3. Формирование migration note** (текстовая справка на новой карточке):
```
Migrated from old product:
[8400010] 🚫 CRISANTEMO RAMI - MIX -flor
Old category: ⛔ Карантин Holded / FLORES CORTADAS / ...
Old SKU: 8400010
Old barcode: ...
Old codigo fabrica: ...
Holded created: 2024-03-15
Holded URL: https://...
```

**4. Перенос данных в target variant:**
- `default_code` (bare, без OLD_)
- `barcode` (bare)
- `image_variant_1920` (именно в variant, не в template!)
- `description_purchase`, `description_sale`
- `x_studio_codigo_fabrica`, `x_studio_holded_url`, `x_studio_holded_created`
- `x_studio_botanic_name` (many2many tags)
- `x_studio_migration_note` (append, если уже был)
- `x_studio_variant_legacy_source = record.id`
- `x_studio_variant_migration_status = 'migrated'`

**5. 🆕 Копирование supplierinfo (patch 2026-04-18):**
```python
old_supplierinfos = env['product.supplierinfo'].search([
    ('product_tmpl_id', '=', record.id)
])
for si in old_supplierinfos:
    si.copy({
        'product_tmpl_id': target.product_tmpl_id.id,
        'product_id': target.id,
    })
```

**Почему copy, а не write:**
- Старая архивная карточка сохраняет свои supplierinfo → историю в chatter старых pedido не ломаем
- Новая получает копии → Make.com бот найдёт learned vendor codes для reconciliation
- Дубли в БД не создают проблемы, они различимы по `product_tmpl_id`

**6. Архивация старой карточки:**
```python
record.write({'active': False})
```

---

## Поля миграционного toolkit

### На `product.template` (source-side)

| Поле | Тип | Назначение |
|---|---|---|
| `x_studio_target_variant` | many2one → product.product | Куда мигрировать |
| `x_studio_migration_status` | selection | `quarantine` / `mapped` / `migrated` / `archived` |
| `x_studio_legacy_source` | many2one → product.product | (была запись, теперь не обязательна) |

### На `product.product` (target variant-side)

| Поле | Тип | Назначение |
|---|---|---|
| `x_studio_variant_legacy_source` | many2one → product.template | Ссылка на исходную (архивную) карточку |
| `x_studio_variant_migration_status` | selection | `migrated` (после action) |
| `x_studio_migration_note` | text | Текстовая history-справка |
| `x_studio_botanic_name` | many2many → product.tag | Ботанические теги (related от template) |

### Selection values для migration_status:

| Value | Label | Смысл |
|---|---|---|
| `quarantine` | quarantine | В карантине, не обработана |
| `ready` | **mapped** | `x_studio_target_variant` выбран, готова к миграции |
| `migrated` | migrated | Мигрирована |
| `archived` | archived | Старая карточка архивирована |

---

## Domain для поля Replace With Variant

```python
[
    ('active', '=', True),
    ('x_studio_variant_legacy_source', '=', False),
    '!', ('product_tmpl_id.categ_id', 'child_of', 207)
]
```

**Защита:**
1. Только активные variants
2. Только не использованные как target (избегаем повторной миграции)
3. Не из карантина (не мигрировать в него же)

**⚠️ Гоча:** domain через `('product_tmpl_id.categ_id.complete_name', 'not ilike', ...)` в many2one popup оказался нестабилен — отрезал почти всё. Рабочий путь — через `child_of` по ID.

---

## SOP: миграция одной карточки

**На старой карточке:**
1. Убедиться, что это source из карантина (`categ_id` child_of 207)
2. Создать или выбрать нужный **target variant** (в новом каталоге, не в карантине)
3. В поле **Replace With Variant** выбрать target
4. Сохранить карточку
5. Нажать кнопку **Migrate to selected variant**

**Проверка после выполнения:**
- Source card:
  - [ ] `default_code = OLD_<old>`
  - [ ] `barcode = OLD_<old>`
  - [ ] `x_studio_migration_status = archived`
  - [ ] `active = False`
- Target variant:
  - [ ] Получил старые SKU / barcode (без префикса OLD_)
  - [ ] `x_studio_variant_legacy_source = <ID старой>`
  - [ ] `x_studio_variant_migration_status = migrated`
  - [ ] `x_studio_migration_note` заполнен
  - [ ] `x_studio_botanic_name` перенесён
  - [ ] **Копии `product.supplierinfo` появились на новом `product_tmpl_id`**
- Старые pedido / продажи по-прежнему открывают старую карточку ✅

---

## Что НЕ переносится (open work)

| Не переносится | План | Приоритет |
|---|---|---|
| `product.pricelist.item` (sales pricelist) | Проверить, есть ли такие | низкий |
| Vendor pricelist rules | Проверить | низкий |
| `mail.message` chatter | By design — остаётся на старой | — |
| Attachments на старой карточке | By design — остаётся | — |
| `stock.putaway.rule` | Проверить | низкий |

---

## Массовая миграция (не реализована)

Сейчас action работает **на одну карточку за раз**. Для массовой миграции нужно:

**🔴 CONCEPT:**
- Batch-wizard (выбрать 100 карточек + уже назначенные target → прогнать action на всех)
- Queue-механизм (фоновая очередь, чтобы не вешать UI)

**Текущая альтернатива:**
- Открыть list view карантинных карточек с `x_studio_target_variant != False`
- Выделить все → server action «Migrate to selected variant» через binding
- Работать частями (по 20-50 за раз, наблюдая)

---

## Типовые проблемы и кейсы

### Пример 1: awkward internal wording

**Было:** у старой карточки name = `[8400253] 🚫 MARFULL - rama`
**Новая target variant:** `Photinia Red Robin foliage`
**Holded learned code:** supplier_sku `193815` → привязан к старой

**После миграции:**
- Supplierinfo `193815` скопирован на новую (Photinia Red Robin)
- Бот при следующей закупке с `supplier_sku=193815` найдёт learned code на новой
- Reconciliation engine v3.5 **не снижает confidence** из-за имени (`MARFULL` vs `Photinia`) — главное что learned code match

### Пример 2: Одна старая → несколько новых variants

**Сейчас не поддерживается** — поле `x_studio_target_variant` = one-to-one.

Если нужно разбить старую «[8400010] CRISANTEMO RAMI MIX» на варианты («Purple», «Yellow», «White»):
- Создать новую template с variants
- Мигрировать только на один variant (например «Mix»)
- Остальные варианты — пусты (история не ехала), но будут использоваться для новых закупок

**Альтернатива (future):** расширить action на one-to-many через отдельное поле / wizard.

### Пример 3: Fabrication code переносится, но не default_code

Сейчас action переносит:
- `default_code` (SKU) → да, в target
- `x_studio_codigo_fabrica` → да
- `seller_ids.product_code` (supplierinfo, после 18 апреля patch) → **да, скопировано**

Всё что use в Make.com боте для evidence priority — **переносится**.

---

## См. также

- [02_makecom_bot.md](02_makecom_bot.md) — как бот использует `product.supplierinfo` для learned codes
- [04_holded_migration.md](04_holded_migration.md) — откуда берутся карточки в карантине
- [08_current_state_snapshot.md](08_current_state_snapshot.md) — сколько карточек ожидают миграции (1983)
- `migrate_variant_action.py` — полный код action
