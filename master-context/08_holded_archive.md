<!-- v: 2 | updated: 2026-05-02T19:30Z -->
# 08. Holded archive — миграция каталога и .py исходники

**Что в файле:** документ миграции каталога из Holded в Odoo Online + Python-исходники одноразовых скриптов (image import, tax fix). Используется как baseline для боевого cutover.

> 📌 **Holded остаётся как архив старых записей** до финального cutover. Финал cutover см. [01_project § 6 этап 7](01_project.md).

---

## 1. Текущее состояние карантина (на 2026-05-02)

| Сущность | Количество | Статус |
|---|---|---|
| Категории под `⛔ Карантин Holded` (id=207) | 79 | ✅ |
| Карточки товара (templates) | ~2106 | ✅ |
| └ Holded flat templates | 2025 | ✅ |
| └ VBOX варианты (flat-импорт) | 81 (21 parent × 2-6 size) | ✅ |
| Фото на карточках | ~119 (38 parex/holded + 81 variants) | ✅ |
| Налоги (sale + purchase, EU intracomunitario) | ✅ настроены | ✅ |
| `sale_ok=False` на всём карантине | ✅ применено | ✅ |
| Botanical tags | штатные `product.tag` | ✅ |
| Albaran / pedido | 173 historical в backlog | 🟡 |

---

## 2. Архитектурные решения миграции

### 2.1. Категории через полный путь

**Было:** `Name + Parent Category` → Odoo не матчил родителей, конфликты иерархии.

**Стало:** одна колонка с полным путём, Odoo сам выстраивает дерево:
```
⛔ Карантин Holded / DECORACION Y ADORNOS / ACCESORIOS DECORATIVOS
```

### 2.2. Категории vs Tags — разделение учёта и поиска

**Проблема:** в Holded один товар мог быть в нескольких категориях. Odoo требует **одну** `Product Category`.

**Решение:**
- `Product Category` (одна) — учёт, склад, налоги, отчёты.
- `x_studio_botanic_name` (m2m → `product.tag`) — поиск для флористов.

**Пример:** `Category=PLANTAS EN MACETAS`, `Botanical Tags=[EUPHORBIA, SUCULENTA]`.

### 2.3. Внешние ID вместо имён

| Сущность | Ключ маппинга |
|---|---|
| product.template | External ID `holded_<holded_id>` |
| product.category | External ID в отдельной колонке |
| account.tax | **Database ID** (по номеру) — имена `10% G` неоднозначны (Sales и Purchase) |
| purchase.order.line.product_id | **Products / External ID** (= variant, не template) |

### 2.4. JIT vs Bulk

- **Bulk (быстрый):** для твёрдого товара (вазы, декор) — как есть, с остатками из Holded.
- **JIT (пооперационный):** для цветов / горшечки — новая карточка создаётся при первой реальной закупке.

---

## 3. Tax mapping (financial formulas)

### 3.1. Domestic (испанский поставщик)

| Тип | Sales | Purchase |
|---|---|---|
| 21% Goods | 5 | 7 |
| 21% Service | 6 | 8 |
| 10% Goods | 82 | 68 |
| 10% Service | 98 | 70 |
| 0% Service | 89 | 56 |
| 5% / "topt" | — | 62 |

### 3.2. EU intracomunitario (поставщик из ЕС, не Испания)

**Sale tax** — всегда испанский domestic (продажа физлицам в Барселоне). EU/EX префикс на sale **НЕ нужен**.

**Purchase tax — EU prefix обязателен** для intracomunitario (reverse charge):

| Тип | Purchase EU |
|---|---|
| 21% EU Goods | **10** |
| 21% EU Service | 9 |
| 10% EU Goods | 20 |

**Применение:** При оприходовании bill'а от EU-поставщика Odoo генерит self-account input + output VAT (Modelo 303), запись в Modelo 349. Чистый эффект на P&L = 0 (НДС обнуляется).

**Текущие EU-поставщики:**
- Parex / SHISHI AS (Эстония, Tallinn) — все 831 parex карточки на `21% EU G`

### 3.3. Спец. карточки (non-holded)

| Карточка | Sales | Purchase |
|---|---|---|
| 🌹 Работа по сборке букета (id=7848) | 98 (10% S) | 70 (10% S) |
| Standard delivery, POS Discount | 82 (10% G) | 68 (10% G) |
| eWallet, Gift Cards, Anticipo | 89 (0% S) | 56 (0% S) |
| REDONDEO (POS) | 89 (0% S) | 56 (0% S) |

### 3.4. Invariant: sale_rate = purchase_rate

Per [99_invariants.md], для каждой карточки `sale tax %` ДОЛЖЕН совпадать с `purchase tax %` (исключая EU/domestic mix, где % одинаковый, отличается только префикс EU). Проверка quick-test'ом по export'у — 0 mismatches.

---

## 4. Категории в Карантине (полный список, 79 шт, root id=207)

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
- 207 — `⛔ Карантин Holded` (root).
- 212 — `FLORES CORTADAS` (на `purchase_method='purchase'`).
- 213 — `PLANTAS EN MACETAS` (на `purchase_method='purchase'`).

---

## 5. Маппинги полей при импорте

### 5.1. Template import (flat карточки)

| Odoo поле | Источник | Важное |
|---|---|---|
| `id` | External ID = `holded_<holded_id>` | Odoo сам префиксит `__import__.` |
| `Name` | Name из Holded | заглавная N в импорте |
| `default_code` | Internal Reference (SKU) | **lookup-ключ для pedido/sale** |
| `barcode` | Barcode | вторичный lookup |
| `categ_id/id` | Category External ID | через external ID |
| `supplier_taxes_id/.id` | Purchase Taxes / **Database ID** | EU id=10/20 для parex |
| `taxes_id/.id` | Sales Taxes / **Database ID** | sale всегда domestic |
| `image_1920` | Main image (base64) | XLSX лучше CSV для emoji |
| `Description` | стандартный multi-line формат (см. §5.4) | заглавная D |
| `x_studio_codigo_fabrica` | Codigo de fabrica из Holded | для bot fallback-матчинга |
| `x_studio_holded_url` | https://app.holded.com/products/{id} | trace |
| `x_studio_holded_created` | dd/mm/yyyy (из MongoDB ObjectId timestamp) | trace |
| `Sales` (sale_ok) | **False** для карантина | `sale_ok=True` ломает POS-каталог |
| `Purchase` (purchase_ok) | True | для оприходования |
| `Active` | True | |
| `Product Type` | Goods | |
| `Track Inventory` | True | |

### 5.1.1. Ключевой invariant: lookup matching для будущих pedido/sale

`default_code` (Internal Reference) — **главный ключ matching'а** при импорте pedido/sale из Holded. Любой вариант/размер должен иметь **уникальный** SKU точно как в Holded источнике (`46562-V25`, `4741293465591-14`).

### 5.1.2. Variant flat-import (вместо Odoo-нативных variants)

Для Holded карточек с вариантами (color/size sets — VBOX боксы и т.д.):
- **Каждый вариант = отдельный flat product.template** (не product.product вариант)
- Уникальный `default_code` = variant SKU из Holded (`46562-V25`)
- Уникальный `barcode` = variant barcode из Holded (`V25-BoxRound3.rndtube`)
- Parent описывается в `Description` ("Variante V25cm del set 46562 (1 из 3 en el set)")
- External ID = `holded_<parent_id>_V<size>`
- Cost = set_cost / N (per-component split, обычно уже сделано в Holded)

**Phantom BOM (mrp module)** — отложен до сборки чистого каталога. Сейчас flat-подход проще и достаточен для pedido/sale matching.

### 5.1.3. CSV vs XLSX encoding gotcha (КРИТИЧНО)

CSV с эмодзи (🚫, ✅) или кириллицей **ломаются Odoo auto-detect** — кодировка определяется как "johab"/Latin-1, UTF-8 байты декодируются как мусор (🚫 → "ðŸš«"). После такого импорта name поля каждой карточки записаны искажёнными.

**Решение:** для любых данных с эмодзи/кириллицей использовать **XLSX**, не CSV. Excel хранит unicode нативно. Все файлы импорта связанные с карантинными названиями — XLSX.

**Workaround если уже сломано:** сделать XLSX restoration с `id` + правильным `Name` (без emoji-corruption), импортнуть → имена восстановятся.

### 5.1.4. Update без перезаписи лишнего

Импорт колонок ТОЛЬКО которые меняются. Например:
- Налоги поправить → `id` + `taxes_id/.id` + `supplier_taxes_id/.id` (без `Name`!)
- Фото добавить → `id` + `image_1920` (без `Name`!)
- Описание → `id` + `Description`

Включение лишних колонок (особенно `Name` с эмодзи) рискует encoding bug'ом и перезаписью.

### 5.2. Purchase line import: albaran → pedido

**Критично:** строки заказа Odoo принимает **только** `product.product` External ID, **не** template.

```
order_line/product_id/id    → variant External ID (export as "Products / External ID")
order_line/product_qty      → Quantity
order_line/name             → Custom Description
order_line/price_unit       → Price
```

С flat-подходом (см. 5.1.2) `product_id` = template's auto-generated `product.product` (1 variant per template). Match по SKU работает.

### 5.3. Mass update through MCP

Для bulk-fix полей (sale_ok=False на всём карантине, налоги, etc.) — `mcp__odoo__update_records` (плюральный) принимает list of IDs + values. До 1000 за раз. Альтернатива — `ir.actions.server` с raw write + self-delete (см. CHANGELOG history).

### 5.4. Description формат (стандартный для карантина)

```
Codigo de fabrication: <factory_code>
Holded Creado: <dd/mm/yyyy>
Link: https://app.holded.com/products/<holded_id>
<Variante V<size>cm del set <parent_sku> (1 из N en el set)>  ← только для variants
Parex: <5-digit_short_code>  ← если совпадает с parex.csv
```

Сгенерирован через формулу из Google Sheets или Python из xlsx-источника.

---

## 6. Кастомные поля Holded

| Поле | Модель | Назначение |
|---|---|---|
| `x_studio_codigo_fabrica` | template (+related variant) | Артикул производителя (для fallback-матчинга в reconciliation engine) |
| `x_studio_holded_url` | template (+related) | Ссылка на исходный Holded URL |
| `x_studio_holded_created` | template (+related) | Дата создания в Holded |
| `x_studio_botanic_name` | template (+related) | Ботанические теги (m2m → `product.tag`) |

---

## 7. Google Sheets артефакты

| Sheet | Назначение | Ссылка |
|---|---|---|
| Holded-Odoo - products | ETL справочник товаров (SKU lookup, tax mapping, category paths) | [link](https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE) |
| albaran-holded | ETL для albaran → pedido, lookup variant External ID | [link](https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58) |

### 7.1. Ключевые формулы Google Sheets

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
=IF(ISNUMBER(SEARCH("21"; 'Все товары'!W2)); 5; IF(ISNUMBER(SEARCH("10"; 'Все товары'!W2)); 82; ""))
```

**Purchase tax by %:**
```excel
=IF(ISNUMBER(SEARCH("21"; 'Все товары'!X2)); 7; IF(ISNUMBER(SEARCH("10"; 'Все товары'!X2)); 68; IF(OR(ISNUMBER(SEARCH("5"; 'Все товары'!X2)); ISNUMBER(SEARCH("topt"; 'Все товары'!X2))); 62; "")))
```

**Google Drive URL → downloadable:**
```excel
=IFERROR("https://drive.usercontent.google.com/download?id="&REGEXEXTRACT(B2;"[?&]id=([^&]+)")&"&export=view";"")
```

**SKU → variant External ID lookup (с fallback):**
```excel
=IFERROR(XLOOKUP(TO_TEXT(TRIM(I2)); exID!D:D; exID!J:J); "__export__.product_product_10_1d32eb89")
```
(fallback = заглушка «НОВЫЙ ТОВАР» id=10)

---

## 8. Ограничения и workarounds (для боевой миграции)

### 8.1. Odoo import relation fields
- Строки заказа принимают **только** `product.product` External ID, НЕ template.
- Решение: экспортировать справочник из Odoo, lookup в Excel → External ID.

### 8.2. Product tags UI из коробки
- Модель `product.tag` есть, но меню в Inventory не было.
- Решение: через Technical/Models создать menu `Inventory / Botanical Tags`. Поле через Studio: m2m на `product.tag`, widget `many2many_tags`. В list view виджет переключить явно (иначе показывается «No records»).

### 8.3. Image import

| Метод | Результат |
|---|---|
| Google Drive URL | ❌ Server-side timeout, редиректы |
| base64 в Google Sheets ячейке | ❌ Лимит 50 000 символов |
| base64 в XLSX | ❌ Excel обрезает длинный текст |
| **CSV + resize 1200×1200 + JPEG 82** | ✅ Рабочий путь |
| Большой CSV разом | ❌ Odoo «Content too large» |
| **CSV батчами по 100** | ✅ Работает |

### 8.4. Update продуктов БЕЗ фото
При update — **исключать** колонку `Image` из CSV. Иначе Odoo попытается перезагрузить картинки.

### 8.5. Studio Autocompletion Fields
Стандартный product search не ищет по `x_studio_codigo_fabrica`. Для поиска по codigo_fabrica нужен `name_search` override в custom module — на Online не поедет, нужен Odoo.sh. **Временно:** короткий codigo держим в `name`.

### 8.6. Purchase Analysis длинные имена
Штатные analytical screens обрезают длинные product names. Варианты: сократить name, или custom report.

### 8.7. Missing Order Reference при импорте purchase
Odoo требует обязательное `name`. Решение: использовать Vendor Reference как Order Reference.

### 8.8. Unmatched SKUs
Не все товары Holded находятся в Odoo справочнике. Решение: fallback на `__export__.product_product_10_...` (product_id = 10), потом вручную переназначить.

---

## 9. Python-исходники (одноразовые скрипты)

> Эти скрипты были в `legacy_migrations/`. Сохраняем здесь как code blocks для компактности — отдельная папка не нужна.

### 9.1. `image_import_from_holded_api.py`

**Назначение:** качает изображения по Holded API endpoint `/products/{id}/image`, ресайз 1200×1200 JPEG quality 82, base64, в CSV для Odoo import. Используется когда есть Holded API key (предпочтительный путь, без redirect-проблем).

**Зависимости:** `pip install requests pillow`

**Env:** `HOLDED_API_KEY` — API key из Holded account settings.

**Input:** `holded-ids.csv` с колонками `holded_id`, `External ID`, `Name`.

**Output:** `odoo_images_from_holded.csv`.

```python
"""
Image Import from Holded API → Odoo CSV
"""

import base64
import csv
import io
import os
from typing import Optional

import requests
from PIL import Image

INPUT_CSV = "holded-ids.csv"
OUTPUT_CSV = "odoo_images_from_holded.csv"
TARGET_SIZE = (1200, 1200)
JPEG_QUALITY = 82

HOLDED_API_KEY = os.environ.get("HOLDED_API_KEY")
if not HOLDED_API_KEY:
    raise RuntimeError("Set HOLDED_API_KEY env variable")

HOLDED_API_BASE = "https://api.holded.com/api/invoicing/v1"
HEADERS = {
    "key": HOLDED_API_KEY,
    "Accept": "application/json",
}


def fetch_image(holded_id: str) -> Optional[bytes]:
    """GET /products/{id}/image → raw bytes."""
    url = f"{HOLDED_API_BASE}/products/{holded_id}/image"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("image/"):
            return resp.content
        try:
            j = resp.json()
            if isinstance(j, dict) and "image" in j:
                return base64.b64decode(j["image"])
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"  [error] holded_id={holded_id}: {e}")
        return None


def process_image(raw: bytes) -> Optional[str]:
    """Resize + JPEG 82 + base64."""
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return base64.b64encode(out.getvalue()).decode("ascii")
    except Exception as e:
        print(f"  [error] processing: {e}")
        return None


def main():
    ok_count = 0
    err_count = 0

    with open(INPUT_CSV, "r", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["External ID", "Name", "Image"])

            for row in reader:
                holded_id = row.get("holded_id", "").strip()
                ext_id = row.get("External ID", "").strip()
                name = row.get("Name", "").strip()

                if not holded_id or not ext_id:
                    continue

                print(f"Fetching {holded_id} → {ext_id} ({name})")
                raw = fetch_image(holded_id)
                if not raw:
                    err_count += 1
                    continue

                b64 = process_image(raw)
                if not b64:
                    err_count += 1
                    continue

                writer.writerow([ext_id, name, b64])
                ok_count += 1

    print(f"\nDone. OK: {ok_count}, Errors: {err_count}")
    print(f"Output: {OUTPUT_CSV}")
    print("Next step: run split script for batched import.")


if __name__ == "__main__":
    main()
```

### 9.2. `image_import_from_urls.py`

**Назначение:** качает изображения по URL (Google Drive и т.д.), тот же pipeline (resize 1200×1200 JPEG 82 + base64). Backup путь когда Holded API недоступен.

**Зависимости:** `pip install openpyxl requests pillow`

**Input:** `img.xlsx` с колонками `Image` (URL), `External ID`, `Name`.

**Output:** `odoo_images_import.csv`.

```python
"""
Image Import from URLs → Odoo CSV
"""

import base64
import csv
import io
import re
from typing import Optional

import openpyxl
import requests
from PIL import Image

INPUT_XLSX = "img.xlsx"
OUTPUT_CSV = "odoo_images_import.csv"
TARGET_SIZE = (1200, 1200)
JPEG_QUALITY = 82
MAX_BYTES = 5 * 1024 * 1024  # 5 MB safety cap

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OdooImage/1.0)"
}


def extract_gdrive_id(url: str) -> Optional[str]:
    """Extract Google Drive file ID from various URL formats."""
    patterns = [
        r"[?&]id=([a-zA-Z0-9_-]+)",
        r"/d/([a-zA-Z0-9_-]+)",
        r"/file/d/([a-zA-Z0-9_-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def normalize_url(url: str) -> str:
    """Convert Google Drive share URLs to direct download."""
    gid = extract_gdrive_id(url)
    if gid:
        return f"https://drive.usercontent.google.com/download?id={gid}&export=view"
    return url


def download_and_process(url: str) -> Optional[str]:
    """Download image, resize, return base64 string or None on error."""
    try:
        url = normalize_url(url)
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()

        content = resp.content
        if len(content) > MAX_BYTES:
            print(f"  [skip] too large: {len(content)} bytes")
            return None

        img = Image.open(io.BytesIO(content))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        b64 = base64.b64encode(out.getvalue()).decode("ascii")
        return b64

    except Exception as e:
        print(f"  [error] {e}")
        return None


def main():
    wb = openpyxl.load_workbook(INPUT_XLSX)
    ws = wb.active

    headers = {cell.value: idx for idx, cell in enumerate(ws[1])}
    url_col = headers.get("Image")
    ext_id_col = headers.get("External ID")
    name_col = headers.get("Name", 0)

    if url_col is None or ext_id_col is None:
        raise ValueError("Required columns 'Image' and 'External ID' not found")

    ok_count = 0
    err_count = 0

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["External ID", "Name", "Image"])

        for row in ws.iter_rows(min_row=2, values_only=True):
            url = row[url_col]
            ext_id = row[ext_id_col]
            name = row[name_col] if name_col is not None else ""

            if not url or not ext_id:
                continue

            print(f"Processing {ext_id}: {name}")
            b64 = download_and_process(str(url))

            if b64:
                writer.writerow([ext_id, name or "", b64])
                ok_count += 1
            else:
                err_count += 1

    print(f"\nDone. OK: {ok_count}, Errors: {err_count}")
    print(f"Output: {OUTPUT_CSV}")
    print("Next step: run split script to create batches for Odoo import.")


if __name__ == "__main__":
    main()
```

### 9.3. `split_big_csv.py`

**Назначение:** режет CSV с base64-картинками на батчи по N строк (обход Odoo «Content too large»).

**Usage:** `python split_big_csv.py` или `INPUT_CSV="X.csv" BATCH_SIZE=100 python split_big_csv.py`.

```python
"""
Split big CSV into batches of N rows.
"""

import csv
import os

INPUT_CSV = os.environ.get("INPUT_CSV", "odoo_images_import.csv")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))


def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    base = os.path.splitext(INPUT_CSV)[0]
    batch_num = 1
    rows_in_batch = 0
    batch_file = None
    batch_writer = None
    header = None
    total_rows = 0

    with open(INPUT_CSV, "r", encoding="utf-8", newline="") as f_in:
        reader = csv.reader(f_in)
        for idx, row in enumerate(reader):
            if idx == 0:
                header = row
                continue

            if rows_in_batch == 0:
                fname = f"{base}_batch_{batch_num:02d}.csv"
                batch_file = open(fname, "w", encoding="utf-8", newline="")
                batch_writer = csv.writer(batch_file)
                batch_writer.writerow(header)
                print(f"Writing {fname}")

            batch_writer.writerow(row)
            rows_in_batch += 1
            total_rows += 1

            if rows_in_batch >= BATCH_SIZE:
                batch_file.close()
                batch_num += 1
                rows_in_batch = 0
                batch_file = None
                batch_writer = None

        if batch_file:
            batch_file.close()

    total_batches = batch_num if rows_in_batch == 0 else batch_num
    print(f"\nDone. Split {total_rows} rows into {total_batches} batches of {BATCH_SIZE}.")
    print(f"Import each {base}_batch_XX.csv into Odoo one by one.")


if __name__ == "__main__":
    main()
```

### 9.4. Usage chain (для повторной миграции)

```bash
# 1. По Holded API (предпочтительно, нужен HOLDED_API_KEY):
HOLDED_API_KEY=xxx python image_import_from_holded_api.py
# → odoo_images_from_holded.csv

# 2. По URL (backup путь):
python image_import_from_urls.py
# → odoo_images_import.csv

# 3. Split на batch'и для импорта:
python split_big_csv.py
# → *_batch_01.csv, _batch_02.csv, ...

# 4. Import в Odoo по одному файлу через Settings → Import.
```

---

## 10. Open для боевой миграции

| # | Что | Статус |
|---|---|---|
| 10.1 | Extra images / gallery | 🔴 (пока только main image) |
| 10.2 | Supplier pricelist history | 🔴 (не переносится при миграции) |
| 10.3 | Импорт продаж 2026 на старые карточки (карантинные / архивные) | 🔴 |
| 10.4 | Импорт factura 2026 со сверкой с Holded totals | 🔴 |
| 10.5 | Финальный cutover Holded → архив | 🔴 (см. [01_project § 6 этап 7](01_project.md)) |

---

## См. также

- [05_catalog.md](05_catalog.md) — миграция карантинных карточек в новый каталог (toolkit v2.2).
- [02_makecom_bot.md](02_makecom_bot.md) — как бот использует `x_studio_codigo_fabrica` и `product.supplierinfo`.
- [01_project.md § 6](01_project.md) — этапы roadmap (включая cutover).
- [99_invariants.md § 2](99_invariants.md) — scripts archive в репо.
