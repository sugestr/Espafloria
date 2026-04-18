<!-- v: 1 | updated: 2026-04-18T15:45Z -->
# 04. Миграция из Holded

Статус: 🟢 **PROD** (категории + 1983 товара + фото) / 🟡 **READY** (albaran импорт начат, основной прогон впереди).

---

## Стратегия миграции

**Гибрид:** bulk импорт карантинного слоя + JIT-подход к созданию новых карточек.

**Слои:**
1. **Исторический слой** — карантинная категория `⛔ Карантин Holded` (id=207), все старые карточки. Не продаются (`sale_ok=False`), держатся для истории закупок/продаж за 2026 год.
2. **Рабочий слой** — новый каталог на variants. Пока 12 карточек (начало). Мигрируются из карантина через [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md).

---

## Что уже импортировано

| Сущность | Количество | Статус |
|---|---|---|
| Категории | 79 под `⛔ Карантин Holded` | ✅ |
| Карточки товара (templates) | 1983 в карантине + 10 служебных + 12 новых | ✅ |
| Фото товаров | по brief: основные главные фото загружены | ✅ |
| Botanical tags | создано меню, штатные product.tag | ✅ |
| Albaran / pedido | 188 импортированы (~90% draft без цен) | 🟡 |

**Фото:** вы указали что **первые фотки уже загружены**. Последующие update карточек — **без колонки `Image`**, иначе Odoo попытается перезагрузить.

---

## Архитектурные решения

### 1. Категории через полный путь, не parent/child

**Было:** импорт через `Name + Parent Category` → Odoo не матчил родителей, конфликты иерархии.

**Стало:** одна колонка с полным путём:
```
⛔ Карантин Holded / DECORACION Y ADORNOS / ACCESORIOS DECORATIVOS
```

Odoo сам выстраивает дерево.

### 2. Категории vs Tags — разделение учёта и поиска

**Проблема:** в Holded один товар мог быть в нескольких категориях (мульти-категоризация). Odoo требует одну `Product Category`.

**Решение:**
- `Product Category` (одна) — учёт, склад, налоги, отчёты
- `x_studio_botanic_name` (many2many на `product.tag`) — поиск для флористов

**Пример:**
- Category: `PLANTAS EN MACETAS`
- Botanical Tags: `EUPHORBIA`, `SUCULENTA`

### 3. Внешние ID вместо имён

Для устойчивого повторного импорта и связей:

| Сущность | Ключ маппинга |
|---|---|
| product.template | External ID формата `holded_<holded_id>` |
| product.category | External ID в отдельной колонке |
| account.tax | **Database ID** (по номеру) — имена типа `10% G` неоднозначны (есть Sales и Purchase) |
| purchase.order.line.product_id | **Products / External ID** (= variant, не template) |

### 4. JIT vs Bulk для рабочего каталога

- **Bulk (быстрый):** для твёрдого товара (вазы, декор) — как есть, с остатками из Holded
- **JIT (пооперационный):** для цветов/горшечки — новая карточка создаётся при первой реальной закупке

---

## Кастомные поля Holded на продуктах

| Поле | Модель | Назначение |
|---|---|---|
| `x_studio_codigo_fabrica` | product.template (+related на product.product) | Артикул производителя (для fallback-матчинга в reconciliation engine) |
| `x_studio_holded_url` | product.template (+related) | Ссылка на исходный Holded URL |
| `x_studio_holded_created` | product.template (+related) | Дата создания в Holded |
| `x_studio_botanic_name` | product.template (+related) | Ботанические теги (many2many → product.tag) |

**Миграционные поля (для toolkit):**
- `x_studio_legacy_source`, `x_studio_target_variant`, `x_studio_migration_status`, `x_studio_migration_note`
- `x_studio_variant_legacy_source`, `x_studio_variant_migration_status`

См. [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md).

**⚠️ Осталось as deprecated (Studio protection не даёт удалить):**
- `x_studio_many2many_field_4qh_1jkvk330u` («[DEPRECATED] New Tags») — битый related, не использовать

---

## Маппинги полей при импорте

### Template import

| Odoo поле | Источник |
|---|---|
| `id` | External ID = `holded_<holded_id>` |
| `name` | Name из Holded |
| `default_code` | Internal Reference (SKU) |
| `barcode` | Barcode |
| `categ_id/id` | Category External ID (lookup по category-sheet) |
| `supplier_taxes_id/.id` | Purchase Taxes / **Database ID** (не name!) |
| `taxes_id/.id` | Sales Taxes / **Database ID** |
| `image_1920` | Main image (base64, через CSV) |
| `x_studio_codigo_fabrica` | Значение из Holded |
| `x_studio_holded_url` | Ссылка на Holded |

### Purchase line import (для albaran→pedido)

**Критично:** для строк заказа Odoo принимает **только** `product.product` External ID, **не** template.

```
order_line/product_id/id    → variant External ID (export as "Products / External ID")
order_line/product_qty      → Quantity
order_line/name             → Custom Description
order_line/price_unit       → Price
```

---

## Tax mapping (financial formulas)

| Holded (%) | Sales Tax ID | Purchase Tax ID |
|---|---|---|
| 21% | 5 | 7 |
| 10% | 82 | 68 |
| 5% | — | 62 |
| "topt" | — | 62 |

**⚠️ Это отличается от Make.com бота**, где используются tax IDs 7/8/68/70. Там бот различает ещё services vs goods:
- 10% service → 70, good → 68
- 21% service → 8, good → 7

То есть полная таблица:
- Sales 21% → 5
- Sales 10% → 82
- Purchase 21% goods → 7
- Purchase 21% services → 8
- Purchase 10% goods → 68
- Purchase 10% services → 70
- Purchase 5% / topt → 62

---

## Категории в Карантине

Полный список (79 шт, корневая id=207):

```
⛔ Карантин Holded
├── Consumibles (расходники)
├── DECORACION Y ADORNOS
│   └── ACCESORIOS DECORATIVOS, ...
├── EMBALAJE (упаковка)
├── ENTREGA
├── FLORES CORTADAS    ← bill policy: "purchase"
│   └── (много сортов: Rosa, Tulipan, Crisantemo, ...)
├── PLANTAS EN MACETAS  ← bill policy: "purchase"
│   ├── CACTUS
│   ├── PLANTAS AROMÁTICAS
│   ├── PLANTAS BULBOSAS
│   ├── PLANTAS CON FLORES
│   └── ...
└── PRODUCTOS ESPECIALES
    ├── DECORACION
    ├── PRODUCTO DESCONOCIDO
    ├── PRODUCTO POR ENCARGO
    ├── RAMO DESCONOCIDO
    ├── REDONDEO (для POS округления)
    └── SERVICIO DE FLORISTA
```

**IDs важных категорий:**
- 207 — `⛔ Карантин Holded` (root)
- 212 — `FLORES CORTADAS` — **цветы, на `purchase_method='purchase'`**
- 213 — `PLANTAS EN MACETAS` — **горшечка, на `purchase_method='purchase'`**

---

## Python-скрипты (в `/code/`)

| Файл | Что делает |
|---|---|
| `image_import_from_urls.py` | Качает изображения по URL (например Google Drive) → resize (1200×1200) → JPEG quality 82 → base64 → CSV для Odoo |
| `image_import_from_holded_api.py` | Берёт Holded ID → запрос к Holded API `/products/{id}/image` → тот же pipeline → CSV |
| `split_big_csv.py` | Режет CSV с картинками на batch'и по 100 строк (обход «Content too large») |

**Usage:**
```bash
# 1. generate from URLs
python image_import_from_urls.py    # input: img.xlsx → output: odoo_images_import.csv
# 2. generate from Holded API
python image_import_from_holded_api.py  # input: holded-ids.csv → output: odoo_images_from_holded.csv
# 3. split for import
python split_big_csv.py  # 100 rows per file
```

---

## Google Sheets артефакты

| Sheet | Назначение | Ссылка |
|---|---|---|
| Holded-Odoo - products | ETL справочник товаров (SKU lookup, tax mapping, category paths) | [link](https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE) |
| albaran-holded | ETL для albaran → pedido, lookup variant External ID | [link](https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58) |

### Ключевые Google Sheets формулы

**Конечная категория (последняя в иерархии):**
```excel
=IF(COUNTA('Все товары'!K2:Q2)=0; "⛔ Карантин Holded"; INDEX(FILTER('Все товары'!K2:Q2; 'Все товары'!K2:Q2<>""); 1; COUNTA(FILTER('Все товары'!K2:Q2; 'Все товары'!K2:Q2<>""))))
```

**Category External ID lookup:**
```excel
=IF(F2=""; ""; IFERROR(INDEX(cat!$A:$A; MATCH(TRIM(CLEAN(SUBSTITUTE(F2; "⛔ "; ""))); cat!$C:$C; 0)); ""))
```

**Sales tax by %:**
```excel
=IF(ISNUMBER(SEARCH("21"; 'Все товары'!W2)); 5; IF(ISNUMBER(SEARCH("10"; 'Все товары'!W2)); 82; IF(ISNUMBER(SEARCH("5"; 'Все товары'!W2)); ""; "")))
```

**Purchase tax by %:**
```excel
=IF(ISNUMBER(SEARCH("21"; 'Все товары'!X2)); 7; IF(ISNUMBER(SEARCH("10"; 'Все товары'!X2)); 68; IF(OR(ISNUMBER(SEARCH("5"; 'Все товары'!X2)); ISNUMBER(SEARCH("topt"; 'Все товары'!X2))); 62; "")))
```

**Google Drive URL → downloadable:**
```excel
=IFERROR("https://drive.usercontent.google.com/download?id="&REGEXEXTRACT(B2;"[?&]id=([^&]+)")&"&export=view";"")
```

**SKU → variant External ID lookup:**
```excel
=IFERROR(XLOOKUP(TO_TEXT(TRIM(I2)); exID!D:D; exID!J:J); "__export__.product_product_10_1d32eb89")
```
(fallback = заглушка «НОВЫЙ ТОВАР» id=10)

---

## Ограничения и workarounds

### 1. Odoo import relation fields
- Строки заказа принимают **только** `product.product` External ID, НЕ template
- Лимит на поиск — нет имени, только ID
- Решение: экспортировать справочник из Odoo, lookup в Excel → External ID

### 2. Product tags UI из коробки
- Модель `product.tag` есть, но меню в Inventory не было
- Решение: через Technical/Models создать menu `Inventory / Botanical Tags`
- Поле на товаре через Studio: many2many на `product.tag`, widget `many2many_tags`
- В list view виджет надо **явно** переключить, иначе показывается как «No records» / «1 record»

### 3. Image import
| Метод | Результат |
|---|---|
| Google Drive URL | ❌ Server-side timeout, редиректы, нестабильность |
| base64 в Google Sheets ячейке | ❌ Лимит 50 000 символов на ячейку |
| base64 в XLSX | ❌ Excel обрезает длинный текст → invalid image |
| **CSV + resize 1200×1200 + JPEG 82** | ✅ Рабочий путь |
| Большой CSV разом | ❌ Odoo «Content too large» |
| **CSV батчами по 100** | ✅ Работает |

### 4. Update продуктов БЕЗ фото
- Если делаете update существующих карточек — **исключайте колонку `Image`** из CSV
- Иначе Odoo попытается перезагрузить картинки, долго + риск падения

### 5. Studio Autocompletion Fields
- Попытка добавить `x_studio_codigo_fabrica` в Autocompletion Fields product search view
- Стандартный product search продолжил искать только по default_code, name, barcode, display_name
- **Решение:** для поиска по codigo_fabrica нужен `name_search` override в custom module (пока не написан)
- **Временно:** короткий codigo всё ещё держим в `name`

### 6. Purchase Analysis длинные имена
- Штатные аналитические экраны не переносят длинные product names → обрезается
- Варианты: сократить name, или custom report (не приоритет)

### 7. Missing Order Reference при импорте purchase
- Odoo требует обязательное `name`
- Решение: использовать Vendor Reference как Order Reference

### 8. Unmatched SKUs
- Не все товары Holded находятся в Odoo справочнике
- Решение: fallback на заглушку `__export__.product_product_10_...` (product_id = 10)
- Потом вручную переназначить

---

## Open work / не завершено

- ⬜ **Импорт всех albaran** за 2026 год — в понедельник 21 апреля сажаем сотрудника
- ⬜ **Импорт всех факту** (Verdnatura специфика: товары отдельно, цены в factura)
- ⬜ **Импорт всех продаж** за 2026 год — садить **только на старые** (архивные или карантинные) карточки
- ⬜ **Добавить codigo_fabrica в name_search** — нужен custom module
- ⬜ **Extra images / gallery** — пока только main image
- ⬜ **Supplier pricelist history** — не переносится при миграции (будет доработан `Migrate` action)

---

## См. также

- [02_makecom_bot.md](02_makecom_bot.md) — как бот использует `x_studio_codigo_fabrica` и `product.supplierinfo` из Holded
- [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md) — перенос карантинной карточки в новый variant
- [08_current_state_snapshot.md](08_current_state_snapshot.md) — текущее состояние базы
