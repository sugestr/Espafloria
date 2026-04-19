<!-- v: 4 | updated: 2026-04-19T23:45Z -->
# 06. Catalog Migration Toolkit v2.2

Статус: 🟢 **PROD** — 10 карточек мигрировано (6 доставок + 4 цветка), 100% success. Тесты покрыли edge cases: 1/10/40+ codigos, 1/4 supplierinfo, UOM Units/Paquete, UI и MCP триггеры дают идентичный результат.

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

**Не делается:** перепривязка старых документов, «слияние» старой в variant, копирование `mail.message` / chatter.

---

## Архитектура v2 (3 объекта)

Миграция построена на паттерне **UI-trigger → flag → automation → execute**:

| Объект | ID | Model | Роль |
|---|---|---|---|
| **UI Trigger** | `ir.actions.server` 1145 | `product.template` | Actions→Migrate menu. Flat-source guard + выставляет `migrate_now=True` на variant → триггерит automation |
| **Execute v2.2** | `ir.actions.server` 1176 | `product.product` | ВСЯ миграционная логика (single source of truth) |
| **Automation** | `base.automation` 6 | `product.product` | `trigger=on_create_or_write`, watched `x_studio_migrate_now` (id 27133), filter `[migrate_now=True, target!=False, status!=archived]`, action `[1176]` |

**Два пути запуска (паритет подтверждён):**
- **UI:** Inventory/Purchase → карточка source → заполнить `Replace With Variant` → Save → Actions → "Migrate to selected variant" → 1145 флипает flag → automation → 1176
- **MCP/API:** `update_record('product.product', SOURCE_VARIANT_ID, {migrate_now: True, target_variant: TARGET_VARIANT_ID})` → automation → 1176

**Source of truth:** `migrate_variant_action.py` (UI trigger, mirror 1145), `migrate_variant_v2.2.py` (execute, mirror 1176). См. [99 §41](99_invariants.md).

---

## Что переносит v2.2

### Всегда (unconditional) — на target:
**Template-level:**
- `x_studio_legacy_source` = source_template.id
- `x_studio_migration_status` = 'migrated'
- `available_in_pos` = **True** ← NEW в v2.2 (миграция = готовность к продаже)

**Variant-level:**
- `x_studio_variant_legacy_source` = source.id
- `x_studio_variant_migration_status` = 'migrated'
- `x_studio_migration_note` — полная история (append, разделитель `\n\n`)

### Copy-if-empty — только если target пусто:

| Поле | Уровень | Условие |
|---|---|---|
| `default_code` (SKU) | variant | source не пусто |
| `barcode` | variant | source не пусто |
| `description_purchase` | variant | source не пусто |
| `description_sale` | variant | source не пусто |
| `image_variant_1920` | variant | **multivariant target** + пусто + source image есть |
| `image_1920` | template | **flat target** + пусто + source image есть |
| `x_studio_codigo_fabrica` | template | target пусто |
| `x_studio_holded_url` | template | target пусто |
| `x_studio_holded_created` | template | target пусто |
| `list_price` | template | **target = 0.0** ⚠️ см. [99 §38](99_invariants.md) |
| `standard_price` | template | target = 0.0 |

### Merge (union):
- `x_studio_botanic_name` (m2m) — target теги не затираются, source добавляются через `(6, 0, union)`

### Supplierinfo (learned vendor codes):
- Копируются через `si.copy()` (автоматом: partner_id, product_code, product_name, price, uom_id, date_start, date_end, currency_id, sequence, min_qty, delay, company_id)
- **Дедупликация** по `(partner_id, product_code)` против уже существующих на target
- `product_id` в copy: `False` для flat target, `target.id` для multivariant

### На source (после переноса):
- SKU / barcode получают префикс `OLD_` (освобождает unique constraint)
- `x_studio_migration_status` = 'archived'
- `active` = False (write на template level, cascade на variant — см. [99 §42](99_invariants.md))
- `x_studio_migrate_now` = False (try/except на случай если archived variant не даёт write)

---

## Форма target: flat vs multivariant

```python
target_is_flat = len(target_template.product_variant_ids) == 1
```

**Flat target (1 template = 1 variant):**
- Картинка → `template.image_1920` (POS тайлы читают template-level, см. [99 §39](99_invariants.md))
- Supplierinfo copy с `product_id=False` (привязка ко всему template)

**Multivariant target (1 template = N variants):**
- Картинка → `variant.image_variant_1920` (чтобы варианты отличались визуально на кассе)
- Supplierinfo copy с `product_id=target.id` (привязка к конкретному variant)

Все 10 мигрированных карточек — flat→flat. Multivariant target на реальных данных ещё не тестировался (будет при миграции Rosa Red Naomi с attributes 40/50/60 cm).

---

## Guards (защита от ошибок)

Скрипт raise `UserError` в следующих случаях:

1. Source не flat (multi-variant source не поддерживается)
2. `Replace With Variant` не заполнен
3. Target = source (self-migration)
4. Target и source из одного template (migration loop)
5. Target archived (template или variant)
6. Source уже migrated (`status='archived'`)
7. Target уже используется как destination для другого source
8. Target template в карантинной категории (`child_of 207`)

UserError пробрасывается через automation к UI — пользователь видит понятное сообщение.

---

## SOP: создание target skeleton

Перед миграцией target template должен существовать (через UI, MCP, или CSV-import).

### Rule 1: `list_price=0.0` ВСЕГДА явно
Odoo ставит `list_price=1.0` default при create. Copy-if-empty не сработает — 1.0 truthy. Цена с source НЕ переедет (инвариант [99 §38](99_invariants.md)).

```python
env['product.template'].create({
    "name": "Rosa Red Naomi - flor",
    "categ_id": 288,
    "list_price": 0.0,  # ← ОБЯЗАТЕЛЬНО
    "type": "consu",
    "is_storable": True,
    ...
})
```

В UI после save проверить что sales_price=0.00 (если 1.00 — вручную 0).

### Rule 2: Правильные налоги
- Цветы срезанные (`Flores Cortadas/*`): `taxes_id=[82]` (10% G sale), `supplier_taxes_id=[68]` (10% G purchase)
- Услуги (доставки): `taxes_id=[5]` (21% G sale), supplier tax 21%
- Аксессуары (керамика, упаковка): `taxes_id=[5]` (21% G)

Post-migration bulk tax adjust — см. [09](09_open_work.md).

### Rule 3: Type и storable
- Цветы срезанные: `type="consu"`, `is_storable=True`
- Доставки/услуги: `type="service"` (`is_storable` не нужно)
- `invoice_policy="order"`, `purchase_method="purchase"` (bill по заказу для цветов — см. [99 §18](99_invariants.md))

### Rule 4: Категория
Target template в не-карантинной категории. Иначе guard 8 заблокирует миграцию.

### Rule 5: `available_in_pos` — не важно что ставишь
Скрипт v2.2 всё равно перепишет в True.

### Rule 6: НЕ заполнять заранее SKU / codigo / картинку / list_price>0
Они переедут с source. Если указать — source данные не запишутся (copy-if-empty). **Исключение:** CSV-import с ценами до миграции сохранит их (респект manual corrections).

---

## Category tree (создано 2026-04-19)

```
287 Flores Cortadas (root, NEW)
├── 288 Rosa Uniflora (m2o roses, 1 template per variety)
├── 289 Ramas y Follaje (branches: eucalipto, marfull, etc.)
└── 290 Flores Variadas (mixed: chrysanthemum mix, etc.)

286 Deliveries (root, существовал)

207 ⛔ Карантин Holded (root, legacy, ~1500 archived-mass + unmigrated)
```

**POS Category (`pos_categ_ids`) — отдельное дерево**, не настроено ещё. Это блокер для UX кассира — см. [09 P0](09_open_work.md) и [99 §40](99_invariants.md).

---

## ID Registry — 10 мигрированных карточек (2026-04-19)

### Deliveries (все flat→flat, categ 286)

| Source tmpl/variant | SKU | → | Target tmpl | Target variant | Name | Sales | Cost |
|---|---|---|---|---|---|---|---|
| 6840 | BCN-EXPRES | → | 7828 | 7844 | Entrega Express Barcelona | 24.71 € | 15.90 € |
| 6841 | BCN-OTRO | → | 7829 | 7845 | Entrega Otras Ciudades | 0 € | 19.80 € |
| 6842 | BCN-GLOVO | → | 7830 | 7846 | Entrega Taxi o Glovo | 0 € | 0 € |
| 6843 | BCN-1 | → | 7831 | 7847 | Entrega Barcelona Zona 1 | 14.83 € | 9.90 € |
| 6844 | BCN-2 | → | 7832 | 7848 | Entrega Barcelona Zona 2 | 19.79 € | 14.85 € |
| 6845 | BCN-3 | → | 7833 | 7849 | Entrega Barcelona Zona 3 | 28.84 € | 19.80 € |

BCN-OTRO и BCN-GLOVO list_price=0 by design — цена per-sale выставляется кассиром.

### Flores (все flat→flat)

| Source | SKU | → | Target tmpl | Variant | Name | categ | codigos | supplierinfo |
|---|---|---|---|---|---|---|---|---|
| 7696 | 8400749 | → | 7834 | 7850 | Rosa Red Naomi - flor | 288 | 1 (170062) | 1 (299) |
| 7473 | 8400253 | → | 7835 | 7851 | Marfull (Madroño/Photinia) - rama | 289 | 10 в строке | 1 (300) |
| 7446 | 8400020 | → | 7837 | 7853 | Eucalipto Cinerea - rama | 289 | 4 | 1 (301) UOM=Paquete |
| 7304 | 8400010 | → | 7836 | 7852 | Crisantemo Rami Mix - flor | 290 | 40+ | **4** (302-305) |

Все source archived, OLD_ префикс на SKU/barcode, `x_studio_migration_status='archived'`.

---

## Validation matrix

| Edge case | Tested on | Результат |
|---|---|---|
| Simple 1:1:1 (1 codigo, 1 supplier, flat→flat) | ROSA (MCP) | ✅ |
| Multi-codigo SKU в одной строке (10) | MARFULL (MCP) | ✅ |
| UOM Paquete на supplier (≠ Units на template) | EUCALIPTO (MCP) | ✅ UOM переехал через copy() |
| Stress: 40+ codigos + 4 supplierinfo с уникальными product_codes | CRISANTEMO (UI) | ✅ Dedup отработал |
| Service type (доставки) | 6 deliveries (MCP+UI) | ✅ |
| Consu + is_storable (цветы) | 4 flores | ✅ |
| UI trigger vs MCP trigger паритет | CRISANTEMO UI vs MCP | ✅ Идентичный результат |
| Rollback (restore active + clear migration fields) | Deliveries первый прогон | ✅ Full cycle retry |
| Odoo 19 template/variant active desync | Deliveries rollback | ✅ template-level write cascade |

**Не покрыто (для следующих версий):**
- Multivariant target — ждёт первую multivariant карточку (rose attributes)
- Multivariant source — сейчас explicit `UserError` («not supported»)
- Migration с `pos_categ_ids` — пока POS categories не настроены
- Bulk wizard — сейчас одиночные write, не batch

---

## Известные баги и фиксы

### BUG-1: `list_price` default 1.0 блокирует перенос (workaround)
**Симптом:** после миграции target.list_price=1.0 вместо значения с source.
**Причина:** Odoo `create` ставит `list_price=1.0` default. Copy-if-empty rule `if old_list_price and not target.list_price` → `not 1.0 = False` → цена НЕ записывается.
**Fix:** при создании skeleton ВСЕГДА передавать `list_price: 0.0` явно. Закреплено в Rule 1 и [99 §38](99_invariants.md).
**Не применённый alt:** изменить на `target.list_price <= 1.0` — но 1.0 может быть осмысленной ценой, не хотим стирать.

### BUG-2: `available_in_pos` не переносился (fixed в v2.2)
**Симптом (v2.1):** target не появляется в POS даже если source была `available_in_pos=True`.
**Причина:** поле не упоминалось в скрипте.
**Fix v2.2:** `available_in_pos=True` добавлен в `tmpl_vals` безусловно. Обоснование: миграция = готовность к активной продаже. Если user решит иначе — снимет вручную.
**Verified:** CRISANTEMO UI-миграция автоматически подняла флаг.

---

## Post-migration procedures

### После каждой миграции через UI:
1. Проверить Migration section на target template (`Replace With Variant` = OLD_..., Status=migrated)
2. Проверить цены (sales/cost соответствуют source)
3. Проверить Purchase tab → supplierinfo (vendor codes переехали)
4. Проверить POS availability (должно быть вкл после v2.2)
5. В открытой POS session → меню → Reload Data (тайлы обновляются)

### Массовые операции после миграции каталога:
- **Налоги bulk:** `categ_id child_of 287` → sale tax 82, purchase 68; категории services → tax 5 и покупной 21%. См. [09](09_open_work.md).
- **POS категории bulk set:** напр. `categ_id=288` → `pos_categ_ids` включают "🌹 Rosas". Зависит от [09](09_open_work.md) настройки `pos.category`.
- **Holded/bot OLD_ awareness:** bot должен понимать archived carddocument с OLD_ для старых pedido. См. [02](02_makecom_bot.md).

### Rollback (если миграция пошла не так):
```python
# Восстановить source template (снять archive, убрать OLD_)
env['product.template'].browse(SOURCE_TMPL_ID).with_context(active_test=False).write({
    'active': True,
    'default_code': ORIGINAL_SKU,  # без OLD_ префикса
    'barcode': ORIGINAL_BARCODE,
    'x_studio_migration_status': False,
    'x_studio_target_variant': False,
})
# Удалить/архивировать target template + copied supplierinfo → повторить миграцию
```

Проверено на delivery rollback — синхронизация template/variant active корректная.

---

## Quick reference

**MCP миграция:**
```python
# 1. Target skeleton создан (с list_price=0.0!)
# 2. Флипаем 2 поля на source variant
odoo.update_record('product.product', SOURCE_VARIANT_ID, {
    'x_studio_migrate_now': True,
    'x_studio_target_variant': TARGET_VARIANT_ID,
})
# Automation срабатывает synchronously → миграция выполнена
```

**UI миграция:**
```
Inventory → Products → (найти source) → Replace With Variant: <target>
→ Save → Actions (шестерёнка) → Migrate to selected variant
```

**Проверка результата (MCP):**
```python
odoo.search_records('product.template',
    domain=[['id', '=', TARGET_TMPL_ID]],
    fields=['default_code', 'list_price', 'x_studio_codigo_fabrica',
            'x_studio_legacy_source', 'x_studio_migration_status',
            'available_in_pos', 'seller_ids'])
```

---

## Future work (не в v2.2)

- [ ] **Multivariant target** — тест на первой rose-multivariant
- [ ] **Multivariant source** — сейчас raise UserError
- [ ] **Bulk migration UI** (multi-select, batch) — для массовой миграции ~100-200 активных карточек
- [ ] **Dry-run mode** — preview without write
- [ ] **Migration log model** — сейчас история в `x_studio_migration_note` (text field); для аудита лучше отдельная `migration.log` модель

---

## Revision history

- **v1** — монолитный action 1145 на `product.template`, с patch copy supplierinfo (2026-04-18)
- **v2** — split на UI trigger 1145 + execute 1176 + automation 6, image fix flat/multivariant, template-level migration fields, цены transfer
- **v2.1** — patch list_price/standard_price transfer, migration fields на template visible в UI
- **v2.2 (current)** — `available_in_pos=True` always, migration_note включает "Old available in POS", stress-test dedup подтверждён (2026-04-19)

---

## См. также

- [02_makecom_bot.md](02_makecom_bot.md) — как бот использует supplierinfo для learned codes + OLD_ SKU awareness TODO
- [04_holded_migration.md](04_holded_migration.md) — откуда берутся карточки в карантине
- [08_current_state_snapshot.md](08_current_state_snapshot.md) — текущая migration progress
- [99_invariants.md](99_invariants.md) — §38-43 (новые инварианты из сессии)
- `migrate_variant_action.py` — mirror action 1145 (UI trigger)
- `migrate_variant_v2.2.py` — mirror action 1176 (execute)
