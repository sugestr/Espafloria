<!-- v: 3 | updated: 2026-05-02T23:30Z -->
# 05. Каталог и миграция (v2.2)

**Что в файле:** migration toolkit v2.2 (UI trigger + execute + automation), 4 правила миграции (бывшие §20-23 в старом 99), category tree, ID-registry мигрированных карточек (пусто после reset), validation matrix (исторические тесты toolkit), post-migration procedures, rollback. Структуры карточек и кастомные поля Holded — здесь же.

**Status:** 🟡 READY — каталог обнулён (только нормированные карточки в карантине, 0 мигрированных). Migration toolkit v2.2 верифицирован валидационным набором ниже (§9), готов к новому циклу миграции при появлении target skeletons.

---

## 1. Философия миграции — 4 правила

### 1.1. История не переносится
Старая карточка остаётся как **историческая запись**. Старые pedido / RFQ / продажи **по-прежнему ссылаются на неё**. После миграции — `active=False`, `default_code/barcode` получают префикс `OLD_`.

Новая карточка (target variant): настоящий SKU/barcode + копия learned vendor codes + ссылка на legacy source.

**Не делается:** перепривязка старых документов, «слияние» старой в variant, копирование `mail.message` / chatter.

### 1.2. При миграции копируем `product.supplierinfo` на target
Patched 2026-04-18. Иначе learned vendor codes теряются и Make.com бот перестаёт матчить supplier_sku.

Дедупликация по `(partner_id, product_code)` против уже существующих на target.

### 1.3. Target variant не может быть из карантина
Domain на `x_studio_target_variant` явно исключает `child_of 207`. Плюс защита в коде server action 1176 (guard 8).

### 1.4. SKU/barcode префикс `OLD_` на архивной
`default_code` / `barcode` старой → `OLD_<original>`. Освобождает unique constraint для target и помечает как legacy.

---

## 2. Архитектура v2 (3 объекта)

Паттерн **UI-trigger → flag → automation → execute**:

| Объект | ID | Model | Роль |
|---|---|---|---|
| **UI Trigger** | `ir.actions.server` 1145 | `product.template` | Actions→Migrate menu. Flat-source guard + выставляет `migrate_now=True` на variant → триггерит automation |
| **Execute v2.2** | `ir.actions.server` 1176 | `product.product` | ВСЯ миграционная логика (single source of truth) |
| **Automation** | `base.automation` 6 | `product.product` | `trigger=on_create_or_write`, watched `x_studio_migrate_now` (id 27133), filter `[migrate_now=True, target!=False, status!=archived]`, action `[1176]` |

**Snapshot files** (см. [99 §2](99_invariants.md)):
- `add/05_migrate_variant_action.py` ↔ 1145
- `add/05_migrate_variant_v2.2.py` ↔ 1176

### 2.1. Два пути запуска (паритет подтверждён)

**UI:**
```
Inventory → Products → source → Replace With Variant: <target> → Save
→ Actions → "Migrate to selected variant"
→ 1145 флипает flag → automation → 1176
```

**MCP/API:**
```python
odoo.update_record('product.product', SOURCE_VARIANT_ID, {
    'x_studio_migrate_now': True,
    'x_studio_target_variant': TARGET_VARIANT_ID,
})
# Automation срабатывает synchronously → миграция выполнена
```

---

## 3. Что переносит v2.2

### 3.1. Всегда (unconditional) — на target

**Template-level:**
- `x_studio_legacy_source` = `source_template.id`
- `x_studio_migration_status` = `'migrated'`
- `available_in_pos` = **True** ← v2.2 (миграция = готовность к продаже)

**Variant-level:**
- `x_studio_variant_legacy_source` = `source.id`
- `x_studio_variant_migration_status` = `'migrated'`
- `x_studio_migration_note` — полная история (append, разделитель `\n\n`)

### 3.2. Copy-if-empty — только если target пусто

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
| `list_price` | template | **target = 0.0** (ВАЖНО, см. § 4.1) |
| `standard_price` | template | target = 0.0 |

### 3.3. Merge (union)
- `x_studio_botanic_name` (m2m) — target теги не затираются, source добавляются через `(6, 0, union)`.

### 3.4. Supplierinfo (learned vendor codes)
- Копируются через `si.copy()` (автоматом: partner_id, product_code, product_name, price, uom_id, date_start, date_end, currency_id, sequence, min_qty, delay, company_id).
- **Дедупликация** по `(partner_id, product_code)` против уже существующих на target.
- `product_id` в copy: `False` для flat target, `target.id` для multivariant.

### 3.5. На source (после переноса)
- SKU / barcode → префикс `OLD_` (освобождает unique constraint).
- `x_studio_migration_status` = `'archived'`.
- `active` = `False` (write на template level, cascade на variant — [99 §G6](99_invariants.md)).
- `x_studio_migrate_now` = `False` (try/except на случай если archived variant не даёт write).

---

## 4. SOP: создание target skeleton

Перед миграцией target template должен существовать. Правила skeleton:

### 4.1. `list_price=0.0` ВСЕГДА явно
Odoo ставит `list_price=1.0` default при create. Copy-if-empty не сработает (1.0 truthy → `not 1.0 = False` → цена с source НЕ переедет).

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

В UI после save проверить sales_price=0.00 (если 1.00 — вручную 0).

**Альтернативный фикс (НЕ применён):** правило `target.list_price <= 1.0` — но 1.0 может быть осмысленной ценой.

### 4.2. Правильные налоги
- Цветы срезанные (`Flores Cortadas/*`): `taxes_id=[82]` (10% G sale), `supplier_taxes_id=[68]` (10% G purchase).
- Услуги (доставки): `taxes_id=[5]` (21% G sale), supplier tax 21%.
- Аксессуары (керамика, упаковка): `taxes_id=[5]` (21% G).

Post-migration bulk tax adjust — см. [01_project § 5.2.6](01_project.md).

### 4.3. Type и storable
- Цветы: `type="consu"`, `is_storable=True`.
- Доставки/услуги: `type="service"`.
- `invoice_policy="order"`, `purchase_method="purchase"` (bill по заказу для цветов — см. [03_inventory § Bill control](03_inventory_pipeline.md)).

### 4.4. Категория
Target template в **не-карантинной** категории. Иначе guard 8 заблокирует миграцию.

### 4.5. `available_in_pos` — не важно что ставишь
Скрипт v2.2 всё равно перепишет в True.

### 4.6. НЕ заполнять заранее SKU / codigo / картинку / list_price>0
Они переедут с source. Если указать — source данные не запишутся (copy-if-empty).
**Исключение:** CSV-import с ценами до миграции сохранит их (respект manual corrections).

---

## 5. Форма target: flat vs multivariant

```python
target_is_flat = len(target_template.product_variant_ids) == 1
```

| Форма | Картинка | Supplierinfo copy |
|---|---|---|
| **Flat** (1 template = 1 variant) | `template.image_1920` | `product_id=False` (привязка ко всему template) |
| **Multivariant** (1 template = N variants) | `variant.image_variant_1920` | `product_id=target.id` (привязка к конкретному variant) |

**Почему так:** POS тайлы читают template-level image для flat, variant-level для multivariant — чтобы варианты отличались визуально на кассе.

**Toolkit верифицирован на flat→flat** (см. §9 Validation matrix). Multivariant target ещё не тестировался — ждёт первую multivariant-миграцию (Rosa Red Naomi с attributes 40/50/60 cm).

---

## 6. Guards (защита от ошибок)

Скрипт raise `UserError` в случаях:

1. Source не flat (multi-variant source не поддерживается).
2. `Replace With Variant` не заполнен.
3. Target = source (self-migration).
4. Target и source из одного template (migration loop).
5. Target archived (template или variant).
6. Source уже migrated (`status='archived'`).
7. Target уже используется как destination для другого source.
8. Target template в карантинной категории (`child_of 207`).

UserError пробрасывается через automation к UI — пользователь видит понятное сообщение.

---

## 7. Category tree (создано 2026-04-19)

```
287 Flores Cortadas (root, NEW)
├── 288 Rosa Uniflora (m2o roses, 1 template per variety)
├── 289 Ramas y Follaje (branches: eucalipto, marfull, etc.)
└── 290 Flores Variadas (mixed: chrysanthemum mix, etc.)

286 Deliveries (root, существовал)

207 ⛔ Карантин Holded (root, legacy, ~1500 archived-mass + unmigrated)
```

**POS Category (`pos_categ_ids`) — отдельное дерево**, не настроено. Блокер UX кассира — см. [01_project § 5.2.7](01_project.md).

---

## 8. ID Registry — мигрированные карточки

После reset каталога — **пусто**. Migration toolkit v2.2 на месте и верифицирован (см. §9 Validation matrix), но мигрированных карточек 0.

При следующем цикле миграции — таблица заполняется построчно: `source variant → target template / target variant`, с указанием SKU, codigos count, supplierinfo count, формы (flat/multivariant), категории (286 Deliveries / 288/289/290 Flores subcat). Шаблон строки:

```
| Source | SKU | → | Target tmpl | Target variant | Name | categ | codigos | supplierinfo |
```

---

## 9. Validation matrix

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

**Не покрыто:**
- Multivariant target — ждёт первую multivariant карточку (rose attributes).
- Multivariant source — explicit `UserError`.
- Migration с `pos_categ_ids` — пока POS categories не настроены.
- Bulk wizard — сейчас одиночные write.

---

## 10. Кастомные поля Holded на `product.template` + `product.product`

### 10.1. Holded heritage (legacy fields)

| Поле | Tmpl | Variant (related) | Назначение |
|---|---|---|---|
| `x_studio_codigo_fabrica` | ✅ | ✅ | Legacy supplier code from Holded |
| `x_studio_holded_url` | ✅ | ✅ | Ссылка на Holded |
| `x_studio_holded_created` | ✅ | ✅ | Дата создания |
| `x_studio_botanic_name` | ✅ | ✅ | Botanical tags (m2m → product.tag) |

### 10.2. Migration fields (для toolkit)

| Поле | Tmpl | Variant | Назначение |
|---|---|---|---|
| `x_studio_legacy_source` | ✅ | ✅ | Миграция: откуда приехала (template.m2o → product.product) |
| `x_studio_target_variant` | ✅ | ✅ | Миграция: куда мигрировать |
| `x_studio_migration_status` | ✅ | ✅ | Статус (quarantine/mapped/migrated/archived) |
| `x_studio_migration_note` | — | ✅ | Текст-справка на target (append) |
| `x_studio_variant_legacy_source` | — | ✅ | (product.product only) |
| `x_studio_variant_migration_status` | — | ✅ | (product.product only) |
| `x_studio_migrate_now` | — | ✅ (id 27133) | Boolean flag-trigger для automation 6 |

### 10.3. Deprecated (не удалить, Studio protection)

- `x_studio_many2many_field_4qh_1jkvk330u` — label `[DEPRECATED] New Tags`. Битый related, не использовать.

---

## 11. Post-migration procedures

### 11.1. После каждой миграции через UI

1. Проверить Migration section на target template (`Replace With Variant` = OLD_..., Status=migrated).
2. Проверить цены (sales/cost соответствуют source).
3. Проверить Purchase tab → supplierinfo (vendor codes переехали).
4. Проверить POS availability (вкл после v2.2).
5. В открытой POS session → меню → Reload Data (тайлы обновляются).

### 11.2. Массовые операции после миграции каталога

- **Налоги bulk:** `categ_id child_of 287` → sale tax 82, purchase 68; категории services → tax 5, покупной 21%.
- **POS категории bulk set:** напр. `categ_id=288` → `pos_categ_ids` включают «🌹 Rosas». Зависит от настройки `pos.category`.
- **Make.com bot OLD_ awareness:** bot должен понимать archived карточки с OLD_ для старых pedido. См. [02_makecom_bot § OLD_ SKU awareness](02_makecom_bot.md).

### 11.3. Перед массовой миграцией — тест на 1 записи

Migration / bulk-update полей / массовое изменение `purchase_method` — сначала **ОДНА** запись, проверка результата, потом batch. (Это инженерное правило применяется ко всем bulk операциям, не только к миграции.)

### 11.4. Rollback (если миграция пошла не так)

```python
# Восстановить source template (снять archive, убрать OLD_)
env['product.template'].browse(SOURCE_TMPL_ID).with_context(active_test=False).write({
    'active': True,
    'default_code': ORIGINAL_SKU,  # без OLD_ префикса
    'barcode': ORIGINAL_BARCODE,
    'x_studio_migration_status': False,
    'x_studio_target_variant': False,
})
# Удалить/архивировать target template + copied supplierinfo → повторить
```

Проверено на delivery rollback — синхронизация template/variant active корректная.

---

## 12. Известные баги (исторические, в коде уже исправлены)

### 12.1. BUG-1: `list_price` default 1.0 блокирует перенос
**Симптом:** после миграции target.list_price=1.0 вместо source.
**Причина:** Odoo `create` ставит default 1.0; copy-if-empty правило `if old and not target` → `not 1.0 = False` → цена НЕ записывается.
**Fix:** Rule § 4.1 — ВСЕГДА `list_price: 0.0` явно.

### 12.2. BUG-2: `available_in_pos` не переносился (fixed в v2.2)
**Симптом v2.1:** target не появляется в POS даже если source была `available_in_pos=True`.
**Fix v2.2:** `available_in_pos=True` добавлен в `tmpl_vals` безусловно.

---

## 13. Quick reference

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

## 14. Future work

| # | Что | Статус |
|---|---|---|
| 14.1 | Multivariant target — тест на первой rose-multivariant | 🔴 |
| 14.2 | Multivariant source — сейчас raise UserError | 🔴 |
| 14.3 | Bulk migration UI (multi-select, batch) — для ~1500 активных карточек | 🔴 |
| 14.4 | Dry-run mode — preview без write | 🔴 |
| 14.5 | Migration log model — сейчас история в `x_studio_migration_note` (text); для аудита лучше отдельная `migration.log` модель | 🔴 |

---

## 15. Revision history

- **v1** — монолитный action 1145 на `product.template`, с patch copy supplierinfo (2026-04-18).
- **v2** — split на UI trigger 1145 + execute 1176 + automation 6, image fix flat/multivariant, template-level migration fields, цены transfer.
- **v2.1** — patch list_price/standard_price transfer, migration fields на template visible в UI.
- **v2.2 (current)** — `available_in_pos=True` always, migration_note включает «Old available in POS», stress-test dedup подтверждён (2026-04-19).

---

## См. также

- [02_makecom_bot.md](02_makecom_bot.md) — как бот использует supplierinfo для learned codes + OLD_ SKU awareness TODO.
- [08_holded_archive.md](08_holded_archive.md) — откуда берутся карточки в карантине + .py исходники image import.
- [07_state_snapshot.md](07_state_snapshot.md) — текущая migration progress.
- [99_invariants.md](99_invariants.md) — § 2 (scripts archive), § G6 (archive template-level), § G7 (Studio fields template-level).
- `add/05_migrate_variant_action.py` — mirror action 1145 (UI trigger).
- `add/05_migrate_variant_v2.2.py` — mirror action 1176 (execute).
