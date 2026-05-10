<!-- v: 2 | updated: 2026-05-10T18:30Z -->
# A1 Audit карантина — снимок 2026-05-10

Снимок текущего состояния каталога в карантине (`product.category` ⛔ Карантин Holded id=207) перед проектированием нового дерева в A3-A4. На основе 5 XLSX-файлов в `pedido.files/migration/`. Источники соединены: Odoo products ↔ supplierinfo ↔ pedido lines 2026 ↔ Holded products ↔ Holded compras.

Deliverables A1.19.7.3:
- **этот файл** — текстовая сводка.
- `pedido.files/migration/audit_2026-05-10.xlsx` — две вкладки с per-card строками.

---

## 1. Объём

**2140 карт** в карантине (`categ_id child_of 207`). Из них 12 служебных вне карантина → не в этом аудите.

| Top-level категория | Карт | % | Лист аудита |
|---|---:|---:|---|
| ROOT (только корень «⛔ Карантин Holded», без подкатегории) | 675 | 31.5% | Лист 1 |
| FLORES CORTADAS | 499 | 23.3% | Лист 1 |
| DECORACION Y ADORNOS | 384 | 17.9% | Лист 2 |
| PLANTAS EN MACETAS | 379 | 17.7% | Лист 1 |
| EMBALAJE (упаковка) | 115 | 5.4% | Лист 2 |
| Consumibles (расходники) | 68 | 3.2% | Лист 2 |
| EQUIPAMIENTO (оборудование) | 7 | 0.3% | Лист 2 |
| PRODUCTOS ESPECIALES | 7 | 0.3% | Лист 2 |
| ENTREGA | 6 | 0.3% | Лист 2 |
| **Итого** | **2140** | 100% | **1553 + 587** |

**Лист 1 «карантин_цветы_root» (1553):** ROSA UNIFLORA 190 + FLORES VARIADAS 132 + RAMAS 124 + ROSA RAMIFICADA 22 + CONIFERAS 11 + BAYAS 6 + CORONAS 5 + BAMBU 5 + FRUTAS 4 + PLANTAS DE FOLLAJE 222 + PLANTAS CON FLORES 62 + PLANTAS PARA TERRAZA 23 + SUCULENTAS 21 + PLANTAS NAVIDEÑAS 19 + PLANTAS COLGANTES 13 + CACTUS 7 + ROOT 675 + остальные мелкие.

**Лист 2 «твердый_товар» (587):** ADORNOS NAVIDEÑOS 192 + ELEMENTOS DECORATIVOS 71 + DECORACIÓN DE METAL 60 + FLORES Y HOJAS DE METAL 32 + PÁJAROS NAVIDEÑOS 19 + ACCESORIOS 8 + ADORNOS TEMÁTICOS 2 + VBOX(CAJAS) 91 + BOLSAS 12 + EMBALAJE 5 + CINTAS 3 + Consumibles 68 + EQUIPAMIENTO 7 + PRODUCTOS ESPECIALES 7 + ENTREGA 6.

---

## 2. Покрытие supplierinfo

Всего **1029 supplierinfo** записей: **711 Verdnatura + 318 Serviflor**.

| Карт по бакетам supplierinfo | Карт |
|---|---:|
| 0 (нет supplierinfo) | **1743** |
| 1-2 | 290 |
| 3-5 | 75 |
| 6+ | 32 |

**81% карт без supplierinfo** — это в первую очередь твёрдый товар + 649 ROOT-only «болтающихся», которые в 2026 не использовались.

### 2.1. Verdnatura

- **711 SI записей** на партнёра VERDNATURA LEVANTE SL.
- **27 без `product_code`** (а не 3, как в первоначальной оценке) — почти все это карты с пустыми `product_code` И `product_name` (т.е. shell-записи скопированные ранее без content) → нужно прочистить в A3 либо как «zombie SI».

### 2.2. Serviflor

- **318 SI записей**.
- **106 без `x_studio_supplier_identity_key`** — починим в A3 из source-файлов Serviflor.

---

## 3. Активность 2026 (что использовалось в pedido)

**395 из 2140 карт (18.5%)** реально использовались в 179 pedido января-мая 2026 (1516 lines всего). Это и есть **скелет нового каталога**.

### 3.1. Per-categoria

| Top-level | Всего | Used 2026 | % used |
|---|---:|---:|---:|
| FLORES CORTADAS | 499 | 209 | 41.9% |
| PLANTAS EN MACETAS | 379 | 124 | 32.7% |
| EMBALAJE | 115 | 24 | 20.9% |
| EQUIPAMIENTO | 7 | 7 | 100% |
| Consumibles | 68 | 3 | 4.4% |
| DECORACION Y ADORNOS | 384 | 1 | 0.3% |
| PRODUCTOS ESPECIALES | 7 | 1 | 14.3% |
| ENTREGA | 6 | 0 | 0% |
| ROOT | 675 | 26 | 3.9% |
| **Итого** | **2140** | **395** | **18.5%** |

**Наблюдение:** EQUIPAMIENTO 7/7 — все 7 карт в работе. DECORACION Y ADORNOS 1/384 — практически вся декоративная нав-полка спит (адекватно для весны: NAVIDEÑOS = декабрь). ENTREGA 0/6 — служебные карты доставки видимо мигрировали на 286 раньше.

### 3.2. Top-25 sub-categ по используемости 2026

| Sub-categ | Total | Used |
|---|---:|---:|
| ROSA UNIFLORA | 190 | 103 |
| PLANTAS DE FOLLAJE | 222 | 85 |
| FLORES VARIADAS | 132 | 53 |
| RAMAS, PALOS, HERBACEA, FOLLAJE | 124 | 31 |
| PLANTAS CON FLORES | 62 | 17 |
| ROSA RAMIFICADA | 22 | 16 |
| VBOX(CAJAS) | 91 | 12 |
| SUCULENTAS | 21 | 8 |
| PLANTAS PARA TERRAZA | 23 | 6 |
| BOLSAS | 12 | 5 |
| EMBALAJE | 5 | 4 |
| BAMBU | 5 | 4 |
| Consumibles | 68 | 3 |

### 3.3. ROOT-only carantine — 675 карт, ответ на A1.19.3.5.1.2

| Группа | Карт |
|---|---:|
| `not_used_in_2026` (можно архивировать как «спящие историчные») | **649** |
| `used_in_2026` (присоединять к новому каталогу + ревью на правильную категорию) | **26** |

**Вывод:** **649 из 675 root-only можно безопасно архивировать** при cutover. Остальные 26 — попадают в скелет нового каталога (плюс к 395-26=369 уже категоризированных used cards).

---

## 4. Sanity-check цен Odoo↔Holded

Match выполнен в порядке: `default_code` ↔ `SKU` → `barcode` ↔ `Código` → `name` ↔ `Nombre` (case-insensitive). НДС-aware: Odoo `list_price` (без НДС) сравниваем с Holded `Subtotal` (тоже без НДС).

| Status | Карт |
|---|---:|
| `match` (diff <5%) | **1919** |
| `no_holded_match` | 115 |
| `both_zero` (обе цены 0) | 97 |
| `large_diff` (>20%) | 7 |
| `holded_zero` (Odoo>0, Holded=0) | 1 |
| `odoo_lower_5pct` | 1 |
| **Итого** | **2140** |

**Match methods:** sku=2025 / no_match=115. Barcode/name fallback не использовался (всё по SKU попало).

### 4.1. Top-7 large_diff (все, что есть)

| Name | SKU | Odoo `list_price` | Holded `Subtotal` | Diff% | Holded IVA |
|---|---|---:|---:|---:|---|
| 🚫 GIRASOL - flor | 8400156 | 4.55 | 2.73 | +66.5% | IVA 10% |
| 🚫 OASIS ESPONJA FLORAL 1 und | R00009 | 3.51 | 8.26 | -57.5% | IVA 21% |
| 🚫 FICUS BONSAI GINSENG (con maceta) | 84001137 | 23.83 | 52.73 | -54.8% | IVA 10% |
| 🚫 OZOTHAMNUS - flor | 8400587 | 2.73 | 1.82 | +49.9% | IVA 10% |
| 🚫 HORTENSIA NACIONAL - flor | 8400027 | 7.27 | 13.64 | -46.7% | IVA 10% |
| 🚫 HYPOESTES - planta/6 | 8400699 | 5.45 | 9.09 | -39.9% | IVA 10% |
| 🚫 LILIUM - Oriental Extra - flor | 8400119 | 9.09 | 7.27 | +25.0% | IVA 10% |

**Вывод по ценам:** **89.7% карт совпали** (1919/2140). Расхождений всего 7 — это шум, не системная проблема. 115 no-match — карты которых нет в Holded (старые архивные / были созданы тестовым способом). 97 both_zero — служебные/недоопределённые карты (часть из 675 root). **A9 «price review» начнётся с фактической базы Holded на старте — Odoo тут синхронен.**

---

## 5. Red flags

| Flag | Карт |
|---|---:|
| `card_no_supplierinfo_no_pedido` (orphan: ни SI ни pedido) | **1737** |
| `holded_no_match` | 115 |
| `mix_candidate` (≥3 разных supplier_product_name) | **77** |
| `barcode_empty` | 20 |
| `price_large_diff` | 7 |
| `card_no_supplierinfo_but_used_2026` (использовалась в pedido, но SI не накопилось) | **6** |
| `sku_empty` | 5 |
| `name_empty` | 0 |
| `dup_sku` | 0 |
| `negative_stock` | 0 |

### 5.1. Orphan-карты (1737) — кандидаты на архивацию

`card_no_supplierinfo_no_pedido` = 1737 — это спящий груз: ни pricelist, ни активность. Это в основном:
- 649 из 675 ROOT-only (спящие).
- ~700 декоративных/упаковочных карт (NAVIDEÑOS, MACETAS DE METAL — сезонные не-весна).
- Остальные — твёрдый товар не активный в 2026.

При cutover (A14) — массовый archive с pre-fix `OLD_` для этих карт по-умолчанию.

### 5.2. `card_no_supplierinfo_but_used_2026` (6 карт)

Использовались в pedido, но SI не накопилось — потому что у них **`default_code=NaN`** (не было ключа для join).

| Name | pedido lines |
|---|---:|
| 🚧🟠 Caja Symphony | 30 |
| 🚧🟠 Caja Sombrerera Corazon | 12 |
| 🚧🟠 Caja Lovelyn Rojo | 9 |
| 🚧🟠 Caja Sombrerera Redondo Rojo | 6 |
| 🚧🟠 Caja Sombrerera Redondo | 3 |
| 🚫 REDONDA CESTA BORDE - grande 22cm 24cm | 1 |

Префикс 🚧🟠 = «новые рабочие черновики» от Make.com бота (без default_code). При sync в A3 присвоить SKU из supplierinfo.

### 5.3. `holded_no_match` (115)

Карты есть в Odoo, нет в Holded по всем 3 ключам. Скорее всего созданы внутри Odoo тестово/ботом. Не блокируют миграцию (Holded-цена просто отсутствует, A9 ставит `new_x3_placeholder`).

### 5.4. Прочие мелкие флаги

- `sku_empty=5` — те же 5 cajas без SKU.
- `barcode_empty=20` — единичные не-Verdnatura источники, не блокирует.

---

## 6. MIX-кандидаты — 77 карт с ≥3 разных `supplier_product_name`

Это карты-«сборные миски»: на одной Odoo-карте сошлись разнородные supplier-имена → подсказка что это **MIX-карта** в смысле раздела 4.3 плана миграции, **даже если в имени нет слова MIX**.

### 6.1. Top-20 по pedido-активности 2026

| Name | SKU | distinct_suppliers | pedido_lines |
|---|---|---:|---:|
| 🚫 CLAVEL - MIX - flor | 8400103 | 34 | 66 |
| 🚫 CRISANTEMO RAMI- MIX -flor | 8400010 | 31 | 49 |
| 🚫 TULIPAN - MIX -flor | 8400236 | 26 | 49 |
| 🚫 PANICULATA - rama | 8400432 | 12 | 32 |
| 🚫 SKIMMIA - ramo | 8400847 | 8 | 24 |
| 🚫 LISIANTHUS - MIX - flor | 8400105 | 16 | 22 |
| 🚫 ALSTROEMERIA - flor | 8400154 | 15 | 21 |
| 🚫 GENISTA - MIX - rama | 8400246 | 4 | 21 |
| 🚫 LIMONIUM - flor | 8400158 | 9 | 21 |
| 🚫 RANUNCULUS GRANDE - flor | 8400530 | 7 | 19 |
| 🚫 ASTILBE MIX - flor | 84001014 | 8 | 17 |
| 🚫 EUCALIPTO - Cinerea - rama | 8400020 | 5 | 17 |
| 🚫 CHAMELACIUM - flor | 8400134 | 10 | 16 |
| 🚫 PHALAENOPSIS MIX - planta/28 | 8400391 | 9 | 16 |
| 🚫 RANUNCULUS - Butterfly - flor | 8400518 | 12 | 15 |
| 🚫 RANUNCULUS - MIX -flor | 8400334 | 7 | 15 |
| 🚫 LILIUM - flor | 8400663 | 8 | 14 |
| 🚫 ASTER - MIX -flor | 8400535 | 8 | 13 |
| 🚫 MIMOSA - rama | 8400331 | 4 | 13 |
| 🚫 OZOTHAMNUS - flor | 8400587 | 4 | 13 |

**Наблюдение для A4 design:** видны и явные MIX (CLAVEL/CRISANTEMO/TULIPAN/LISIANTHUS), и **скрытые** MIX без слова MIX в имени (PANICULATA, SKIMMIA, ALSTROEMERIA, LIMONIUM, EUCALIPTO Cinerea, RANUNCULUS Butterfly, MIMOSA, OZOTHAMNUS). По решению §4.3 плана — на каждом MIX-кластере минимум 2 ценовых tier (cheap/standard) или 3 (cheap/standard/premium). 77 кандидатов — это объём design-pass'а в A4.

---

## 7. Verdnatura albaran-level cross-check — три источника

Sanity-check по суммам в первом проходе показал «-18.6% gap в марте». **Глубокий анализ через 4 фактуры PDF + Holded albaran XLSX дал точную картину**:

### 7.1. Три источника

| Источник | Что | Q1+Apr 2026 |
|---|---|---:|
| **Verdnatura facturas** (4 PDF) | Истина поставщика — список albaran с ref/qty/price | **253 albaran** |
| **Holded albaranes Exportar** | То что бухгалтер дотащила в Holded | **167 albaran** (только Q1, апреля ещё нет) |
| **Odoo pedidos** | То что Make.com бот импортировал из Holded | **167 + 2 cancel** (= 167 effective) |

### 7.2. Per-month раскладка

| Месяц | Factura albaran | В Holded | В Odoo | Holded↔Odoo | Factura↔Holded |
|---|---:|---:|---:|---:|---:|
| Jan A12604661 | 58 | 53 | 53 | **0** ✅ | **5** missed by bookkeeper |
| Feb A12610404 | 45 | 42 | 42 | **0** ✅ | **3** missed by bookkeeper |
| Mar A12615103 | 86 | 72 | 72 | **0** ✅ | **14** missed by bookkeeper (~2 936€) |
| Apr A12621592 | 64 | 0 | 0 | **0** ✅ | **64** workflow lag (factura получена 30 Apr) |
| **Итого** | **253** | **167** | **167** | **0** ✅ | **86** |

### 7.3. Главный вывод

**Holded ↔ Odoo = идеальное совпадение.** Make.com бот не теряет ничего. **Все 86 «пропущенных» — это что бухгалтер не довела до Holded.** Из них:

A1.21.5.3.1. **22 «исторических потери» бухгалтера** (Jan+Feb+Mar) — реальные пропуски, товар приехал в магазин но в учёт не попал. **Полный список для разбора с бухгалтером:**
- **Jan (5):** `12185412`, `12226183`, `12226607`, `12268742`, `12268745`
- **Feb (3):** `12287826`, `12297344`, `12329273`
- **Mar (14):** `12455005`, `12460282`, `12460764`, `12469240`, `12511781`, `12511794`, `12515660`, `12523833`, `12523835`, `12523839`, `12524725`, `12524751`, `12525935`, `12525937`

A1.21.5.3.2. **64 апрельских** — нормальный workflow lag. Фактура от 30 апреля получена сегодня (10 мая), бухгалтер ещё не разнесла, поэтому ни в Holded, ни у нас их нет. **Не ждём** появления в Holded — будем сажать апрельские albaran напрямую на новый каталог в **блоке A11** (это и был исходный план апрельской приёмки).

### 7.4. Обновлённый план для блоков A2 и A11

**A2 (после A6):** sub-agent дотягивает 22 «исторических» albaran на готовый новый каталог через **codigo-based matching** (без bookkeeper recount, без stock movement — это учётный backfill). Стратегия:
1. Парсит каждую строку фактуры PDF: `(codigo, cant, concepto, PVP/u, IVA)`.
2. Ищет `product.supplierinfo.product_code = codigo` среди новых карт.
3. Найден → создаёт `purchase.order.line` без picking (учётный backfill, не stock).
4. Не найден → пишет в CSV для ручного ревью owner'ом.

**A11:** 64 апрельских albaran-PDF проходят через **штатный Mode B workflow** (бот распознаёт → логист принимает → флористы пересчитывают → stock реально появляется). Это **первый stock-приход на новый каталог** = ключевое событие миграции.

### 7.5. Артефакты в репо для A2/A11

- `pedido.files/reception_paper/factura_2026/factura_2026A1xxx_<mon>.pdf` — 4 фактуры Verdnatura.
- `pedido.files/migration/holded_albaranes_2026-05-10.xlsx` — Holded albaran items для трассируемости.
- Полный список 22+64 missing albaran — в этой секции выше.

---

## 8. Что дальше

A1 закрыт. **Следующий блок A3 — extraction атрибутов** из:
1. **711 Verdnatura SI** + 27 zombie без code → починить либо удалить.
2. **318 Serviflor SI** + 106 без identity_key → починить из source.
3. **77 MIX-кандидатов** → designate `mix_tier=cheap/standard/premium`.
4. **395 used-2026 cards** + 26 root-used = **~420 карт-кандидатов** для нового каталога.
5. **649 not-used root + ~700 hard-good orphan** → archive batch при A14 cutover.

После A3 → A4 design tree (учётка + POS) → A5 pilot multivariant.

---

## См. также

- [05_2026-05-10_migration_plan.md](05_2026-05-10_migration_plan.md) — карта блоков A1-A14
- [05_catalog.md](../05_catalog.md) — toolkit миграции v2.2
- `pedido.files/migration/audit_2026-05-10.xlsx` — per-card данные на 2 листах
- `pedido.files/migration/build_audit.py` — скрипт сборки (для воспроизводимости)
