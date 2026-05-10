<!-- v: 1 | updated: 2026-05-10T22:00Z -->
# A4 Catalog Design v1 — снимок 2026-05-10

Draft нового каталога Espafloria на 395 use-cards 2026: **312 templates** (261 flat + 51 multivariant), **97 MIX-cards** распределены на 3 ценовых tier (cheap/standard/premium), **1745 спящих карт** идут в archive batch при cutover. **0 custom Studio-полей** — только штатное Odoo 19 (`product.attribute` + `product.tag` + `product.category` + `pos.category`). Готов для ревью owner'ом, дальше → A5 pilot multivariant.

> **Source of truth:** транскрипт обсуждений + `kb/add/05_2026-05-10_audit_quarantine.md` + `kb/add/05_2026-05-10_migration_plan.md`. **Per-card данные** — в `pedido.files/migration/migration_map_2026-05-10.xlsx`.

---

## 1. Принципы (короткое напоминание из плана)

A4.1.1. **0 Studio-полей.** Используем штатные Odoo 19 механизмы:
- `product.attribute` + `product.attribute.value` для **вариант-генерирующих** атрибутов (Длина, Размер горшка, MIX Tier).
- `product.tag` (m2m через `product_tag_ids`) для **метаданных** (имена ЧИСТЫЕ — `Rosa`, `rojo`, `Holland`, `mix-cheap`).
- `product.category` для иерархии **учёта** (analytics, finance).
- `pos.category` для UX **кассира** (тематические вкладки).

A4.1.2. **Bill control** уже зафиксирован в плане §4.7:
- Срезка + горшечка → `purchase_method=purchase` (платим бумагу).
- Декорация / упаковка / расходники / оборудование / доставка → `purchase_method=receive` (платим факт).

A4.1.3. **MIX-tier обязателен.** На каждой MIX-карте — `mix-cheap` / `mix-standard` / `mix-premium` тег, независимо от того написано MIX в имени или нет.

A4.1.4. **Имена tags чистые, без префиксов.** Категория тега различается через `color` hex (см. §6).

A4.1.5. **Цены `list_price`** — из текущего Holded `Subtotal` (без НДС). Если Holded=0 → ×3 cost (placeholder, owner ревьюит).

A4.1.6. **Default_code и barcode наследуются** от донорской карты для миграции v2.2 (toolkit `add/05_migrate_variant_v2.2.py`).

---

## 2. Дерево учётной категории (`product.category`)

Строим **поверх существующего** skeleton (что уже создано до A4):
- `Flores Cortadas` (id 287)
- `Flores Cortadas / Rosa Uniflora` (id 288)
- `Flores Cortadas / Ramas y Follaje` (id 289)
- `Flores Cortadas / Flores Variadas` (id 290)
- `Embalaje` (id 292)
- `Espafloria Internal` (id 291)
- `Deliveries` (id 286)

**Расширяемое дерево (новое = `[NEW]`):**

```
Flores Cortadas (287)
├─ Rosa Uniflora (288)               → 80 карт
├─ Rosa Ramificada [NEW]             → 19 карт
├─ Flores Variadas (290)             → 69 карт
├─ Ramas y Follaje (289)             → 36 карт
├─ Bambu [NEW]                       → 4 карт
└─ Bayas y Frutas [NEW]              → 1 карта

Plantas en Macetas [NEW]
├─ Plantas de Follaje [NEW]          → 86 карт
├─ Plantas con Flores [NEW]          → 17 карт
├─ Suculentas y Cactus [NEW]         → 10 карт
├─ Plantas para Terraza [NEW]        → 6 карт
├─ Plantas Colgantes [NEW]           → 3 карт
└─ Plantas Aromáticas y Frutales [NEW] → 2 карт

Embalaje (292)
├─ VBOX [NEW]                        → 12 карт
├─ Bolsas [NEW]                      → 5 карт
├─ Oasis y Esponjas [NEW]            → 2 карт
├─ Cintas [NEW]                      → 1 карта
└─ Tarjetas [NEW]                    → 0 (резерв)

Equipamiento [NEW]                   → 7 карт
Consumibles [NEW]                    → 3 карт
Productos Especiales [NEW]           → 28 карт
```

A4.2.1. **Глубина 2 (Top-level / Sub)** — намеренно неглубоко. Ниже — `product.tag` сам уже даёт фасет (genus/variety). Глубже копать в категориях смысла нет: это убьёт UX в pricelist forms и в reports.

A4.2.2. **`Plantas en Macetas` строим как новый root**, отдельно от старого `⛔ Карантин Holded / PLANTAS EN MACETAS` (id=213). При cutover старое дерево скрывается через archive детей.

A4.2.3. **`Embalaje` — оставляем существующий root id=292**, дополняем sub'ами. Существующий `EMBALAJE (упаковка)` (id=210) уходит в archive.

A4.2.4. **Productos Especiales** — катчолл для нестандартного: декор когда-нибудь продаваемого, services. Сюда же falls back карантинная DECORACION (1 used card), которая в этом проходе не получает отдельного дерева.

---

## 3. Дерево POS-вкладок (`pos.category`)

A4.3.1. **Базовое зеркало** учётного дерева (8 верхних вкладок):

| POS вкладка | Связь с учёткой | Cards |
|---|---|---:|
| 🌹 Rosas | Flores Cortadas / Rosa Uniflora + Rosa Ramificada | 98 |
| 💐 Flores Cortadas | Flores Cortadas / Flores Variadas + Bayas y Frutas | 76 |
| 🌿 Verde y Ramas | Flores Cortadas / Ramas y Follaje + Bambu | 36 |
| 🪴 Plantas en Macetas | Plantas en Macetas / * (все sub) | 124 |
| 📦 Embalaje | Embalaje / * | 24 |
| 🛠️ Equipamiento | Equipamiento | 7 |
| 🧰 Consumibles | Consumibles | 3 |
| ⚙️ Servicios | Productos Especiales | 27 |

A4.3.2. **Тематические псевдо-вкладки (создаются в A8)** — параллельные базовым, любой product может попасть в обе. Membership через `pos_categ_ids` (m2m).

**Постоянные (всегда видимые):**
- 🆕 Новинки — карты, созданные за последние 14 дней.
- 📦 Текущая поставка — `last_pedido_at` за неделю.
- 📦 Прошлая поставка — `last_pedido_at` за прошлую неделю.
- ⏰ Скоро испортится — для срезки старше N дней (TBD механизм в A8).
- 🔥 Акционные — те, у кого `discount_active=true`.

**Сезонные (включаются за 1-2 недели до даты, выключаются после):**
- ❤️ 14 февраля
- 🌷 8 марта (Día de la Mujer)
- 🌻 Día de la Madre (май)
- 🎃 Хеллоуин
- 🎄 Рождество (Nov-Dec)
- 🦋 Sant Jordi (23 апреля)

A4.3.3. **Implementation note:** механизм «динамические вкладки» (cron + flag vs computed/related field) — открытый вопрос плана §4.2, решается в A8.

---

## 4. Семьи карт (top-30 по pedido-частоте 2026)

«Семья» = группа карт с одинаковым `genus + (variety/pack_class)` → кандидат на единый `product.template` с variants.

**Распределение форм по 312 templates:**
- **flat** (1 card → 1 template): 261 шт.
- **1-axis multivariant** (несколько cards в template + axis Длина/Размер): 51 шт.
- **2-axis multivariant**: 0 шт. (возможно появится после ревью owner'ом)
- **split** (формально могли бы быть в одной семье, но логично разделить): 14 семей (32 cards) — оставлены отдельными templates

**Top-30 семей по pedido_lines_count_2026:**

| # | Семья (genus / variety) | Cards | Lines | Qty | Form | Template name | New categ | MIX | Цена€ | Cost€ |
|--:|---|--:|--:|--:|---|---|---|---|--:|--:|
| 1 | Clavel | 1 | 66 | 2655 | 1-axis | Clavel Solomio Cas SEL | Flores Variadas | yes | 1.82 | 0.36 |
| 2 | Tulipa | 4 | 63 | 4370 | 1-axis | Tulipa | Flores Variadas | yes | 3.19 | 0.61 |
| 3 | Chrysanthemum | 2 | 58 | 1535 | split | Chrysanthemum CR Molly Yellow | Flores Variadas | yes | 2.73 | 0.62 |
| 4 | Ranunculus | 3 | 49 | 2079 | 1-axis | Ranunculus | Flores Variadas | yes | 2.73 | 1.01 |
| 5 | Hydrangea | 3 | 33 | 690 | 1-axis | Hydrangea | Flores Variadas | yes | 5.45 | 0.85 |
| 6 | Phalaenopsis | 6 | 33 | 255 | 1-axis | Phalaenopsis | Plantas con Flores | yes | 28.64 | 12.86 |
| 7 | Limonium | 2 | 33 | 1100 | split | Limonium N NOR Scarlet Diamond | Flores Variadas | yes | 1.82 | 0.54 |
| 8 | Gypsophila (PANICULATA) | 1 | 32 | 925 | 1-axis | Gypsophila PAN Roja MA 30 gr | Flores Variadas | yes | 2.73 | 0.53 |
| 9 | Caja Symphony | 1 | 30 | 285 | flat | Caja Symphony | Embalaje / VBOX | no | 5.79 | — |
| 10 | Cera (CHAMELACIUM) | 2 | 29 | 1015 | 1-axis | Cera Cera Adi | Flores Variadas | yes | 1.82 | 0.48 |
| 11 | Eucalyptus | 3 | 29 | 116 | 1-axis | Eucalyptus | Ramas y Follaje | yes | 1.82 | 3.26 |
| 12 | Skimmia | 1 | 24 | 185 | 1-axis | Skimmia J Rubella | Ramas y Follaje | yes | 1.82 | 4.97 |
| 13 | Genista | 2 | 23 | 179 | 1-axis | Genista Retama Rosa 200 gr | Ramas y Follaje | yes | 1.74 | 1.80 |
| 14 | Eustoma (LISIANTHUS) | 1 | 22 | 420 | 1-axis | Eustoma Doble Corelli Coral | Flores Variadas | yes | 3.64 | 1.57 |
| 15 | Lilium | 3 | 21 | 280 | 1-axis | Lilium | Flores Variadas | yes | 5.45 | 1.93 |
| 16 | Alstroemeria | 1 | 21 | 746 | 1-axis | Alstroemeria Si Sofiena | Flores Variadas | yes | 2.73 | 0.71 |
| 17 | Palma | 6 | 18 | 108 | 1-axis | Palma | Flores Variadas | yes | 4.55 | 1.56 |
| 18 | Astilbe | 1 | 17 | 400 | 1-axis | Astilbe Vision Pink | Flores Variadas | yes | 1.82 | 0.52 |
| 19 | Rosa / Explorer EXT | 2 | 16 | 650 | 1-axis | Rosa RS Explorer EXT | Rosa Uniflora | yes | 4.09 | 0.82 |
| 20 | Ficus | 11 | 16 | 65 | 1-axis | Ficus | Plantas de Follaje | no | 52.73 | 16.75 |
| 21 | Crassula | 4 | 15 | 81 | 1-axis | Crassula OVATA | Suculentas y Cactus | yes | 20.91 | 10.43 |
| 22 | Paeonia | 2 | 15 | 720 | 1-axis | Paeonia Gardenia | Flores Variadas | yes | 4.55 | 2.76 |
| 23 | Narcissus | 4 | 13 | 132 | split | (4 распала) | Plantas de Follaje | yes | 16.37 | 8.17 |
| 24 | Acacia (MIMOSA) | 1 | 13 | 94 | 1-axis | Acacia | Ramas y Follaje | yes | 1.82 | 5.89 |
| 25 | Dracaena | 6 | 13 | 78 | 1-axis | Dracaena | Plantas de Follaje | no | 30.00 | 11.88 |
| 26 | Aspidistra | 3 | 13 | 720 | split | (3 распала) | Ramas y Follaje | yes | 0.45 | 0.22 |
| 27 | Aster | 1 | 13 | 325 | 1-axis | Aster Paquita | Flores Variadas | yes | 1.82 | 0.26 |
| 28 | Clematis | 1 | 12 | 390 | 1-axis | Clematis Amazing Kibo | Flores Variadas | yes | 1.82 | 0.34 |
| 29 | Caja Sombrerera Corazon Rojo | 1 | 12 | 81 | flat | Caja Sombrerera Corazon | Embalaje / VBOX | no | 12.30 | — |
| 30 | Anthurium | 5 | 12 | 78 | 1-axis | Anthurium | Plantas con Flores | no | 16.36 | 6.71 |

A4.4.1. **Comments per top family:**
- **Tulipa (#2):** 4 cards — Novi Sun MIX, Fe Happy Clown, Avignon Parrot, Red Princess Double. Различные **сорта** (variety) одного genus. Решение: один template `Tulipa` с axis `Длина (см): [4, 30, 36, 60]`. **Variant-уровень** будет хранить variety через тег. Owner ревьюит — может захотеть split на 2 templates (MIX vs single-variety).
- **Chrysanthemum (#3):** split на 2 (CR Molly Yellow + крупный rami) — генез разный. Owner может захотеть merge.
- **Hydrangea (#5):** 3 cards — flor pequeño/5, flor pequeño/3, NACIONAL flor. Все срезка → 1 template `Hydrangea` с длинами 50/60. Sister cards `HORTENSIA T10/T14 - planta` уехали в `Plantas en Macetas / Plantas para Terraza` отдельно (пакет другой).
- **Phalaenopsis (#6):** 6 cards с разными размерами горшков 18-67см → 1 template с axis `Размер горшка (см)`. Premium tier — `Phalaenopsis MIX 35cm` за ~25€, cheap tier — `MIX 22cm` за ~12€.
- **Ficus (#20):** 11 cards (самая большая potted-семья) — Ginseng cerámica, Microcarpa Maya, Lyrata, разные размеры горшков 12-267см. Один template `Ficus` с axis pot size. **Confidence MEDIUM** — owner может захотеть split на Ficus Ginseng vs Ficus Microcarpa vs остальное.
- **Palma (#17):** 6 cards — variety от 12см бумажной solapa до 190см срезки большой. **multi_length_conflict** — owner ревьюит.
- **Rosa / Explorer EXT (#19):** только 2 cards (50cm + 60cm). Multivariant с длинами 50/60.

A4.4.2. **Полная Top-312 templates** — в `migration_map_2026-05-10.xlsx`, лист «new_templates».

---

## 5. Variant attributes registry

A4.5.1. **3 атрибута**, все в `create_variant=dynamic` (Odoo не создаёт все combinations сразу — только при использовании).

| Attribute | Display | Values | Cards using | Применимо к |
|---|---|---|---:|---|
| **Длина (см)** | radio | `[3, 4, 10, 12, 14, 15, 20, 25, 26, 28, 30, 33, 35, 36, 38, 40, 41, 45, 50, 52, 55, 60, 62, 65, 70, 75, 80, 90, 100, 150, 190]` (31 значение) | 187 | Срезка (все Flores Cortadas) |
| **Размер горшка (см)** | radio | `[5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 35, 36, 38, 39, 42, 47, 50, 60, 67, 78, 84, 114, 124, 154, 188, 267]` (38 значений) | 86 | Горшечная (Plantas en Macetas) |
| **MIX Tier** | radio | `[cheap, standard, premium]` (3 значения) | 97 | MIX-карты — accessible только для семей с `is_mix_candidate=yes` |

A4.5.2. **«Цвет» как variant attribute убран** из плана. Cards с явным mono-color (rojo, blanco) — color едет тегом. Cards с multi-color (mix) — это уже MIX-tier story. Пилот A5 не нужно усложнять 3-axis вариантами.

A4.5.3. **Существующие 29 product.attribute в Odoo registry** (из ранних test-проходов sub-agent'а на test-card 7304 CRISANTEMO RAMI MIX) — нужно почистить. Полезные: id=11 Color (dynamic), id=13 Altura (dynamic), id=15 Maceta (dynamic). Лишние (no_variant): id=14 UD Venta, id=17 Nº Tallos, id=18-29 (Tamaño Botón, Botón Mínimo, Diámetro, Peso/Tallo, Longitud Brote, Ancho Superior/Inferior, Grosor, Peso, Tamaño Caja). **Owner ревьюит** перед чисткой.

A4.5.4. **Лучше:** в A5 (pilot) создаём **новые** 3 attribute: «Длина (см)», «Размер горшка (см)», «MIX Tier» с правильным `create_variant=dynamic` и переходим на них. Старые id=13/15 могут остаться в registry (Odoo не позволяет easy delete если есть values), мы их просто не используем.

---

## 6. Tags registry

A4.6.1. **8 категорий тегов**, имена ЧИСТЫЕ (без префиксов `Genus:` / `Color:` / итд). **Категория различается через `color` hex** (Odoo product.tag.color, integer 0-11 или hex selection).

| Категория | hex / int | Тэгов | Top-5 |
|---|---|---:|---|
| **Genus** (ботанический род) | `#3C3C3C` (existing 215) + новые ~50 | ~265 | Rosa (98), Ficus (13), Dracaena (8), Anthurium (7), Palma (6) |
| **Variety** (сорт/cultivar) | `#5B8FF9` (новый) | ~316 | Set de 7 unidades Cesta Chenna (7), pintado (5), negro (4), BONS Ginseng Cerámica (3), Lucky Bamboo Espiral (3) |
| **Color** (физический цвет) | `#FF6B6B` (новый) | 16 | rosa (69), verde (60), blanco (45), rojo (45), amarillo (21) |
| **Origin** (страна origin) | `#4ECDC4` (новый) | 5 | Holland (19), Kenya (15), Israel (3), Italy (2), Colombia (1) |
| **Light** (свет для растения) | `#FFD93D` (новый) | 3 | sombra (87), media (17), sol (16) |
| **MixTier** (ценовой tier) | `#A06CD5` (новый) | 3 | mix-cheap (67), mix-standard (17), mix-premium (13) |
| **Treatment** (обработка) | `#95E1D3` (новый) | 2 | teñido (3), natural (1) |
| **PackMode** (тип упаковки от поставщика) | `#F38181` (новый) | 2 | unit, pack (резерв) |

A4.6.2. **Существующие 215 product.tag в Odoo (`#3C3C3C` все)** — это **ботанические рода** уже созданные ранее. Переиспользуем под Genus. Дополним недостающими ~50: Tulipa, Chrysanthemum, Hydrangea (как тег, не cat), Phalaenopsis, etc.

A4.6.3. **Color tags потенциально конфликтуют со словом** (rosa = и цвет и genus Rosa). Решение: **case-sensitive** — тег `Rosa` (Genus) ≠ тег `rosa` (Color). Odoo unique-constraint name+create_uid позволяет дубли с разным капс, но для UX — рискованно. **Альтернатива:** color tag = `color-rosa` (всё-таки префикс). Owner ревьюит.

A4.6.4. **mix-cheap / mix-standard / mix-premium** — единственный случай где префикс остаётся (через дефис), потому что `cheap/standard/premium` — слишком общие слова для тега.

A4.6.5. **Полный список 544 предложенных тегов** — в `a3_extracted_attributes_2026-05-10.xlsx` лист «proposed_tags_catalog».

---

## 7. MIX-tier mapping

A4.7.1. **97 MIX-cards распределены на 3 tier:**
- **mix-cheap** (`< 5€` или `< 8€` для горшечной): **67** карт
- **mix-standard** (`5-15€` срезка / `8-20€` горшечная): **17** карт
- **mix-premium** (`> 15€` срезка / `> 20€` горшечная): **13** карт

A4.7.2. **Top-15 MIX-cards по объёму закупок 2026:**

| # | Old name | Genus | Tier | Цена | Cost | Pedido lines |
|--:|---|---|---|--:|--:|--:|
| 1 | CLAVEL - MIX - flor | Clavel | cheap | 1.82 | 0.36 | 66 |
| 2 | TULIPAN - MIX -flor | Tulipa | cheap | 1.82 | 0.36 | 49 |
| 3 | CRISANTEMO RAMI- MIX -flor | Chrysanthemum | cheap | 2.73 | 0.67 | 49 |
| 4 | PANICULATA - rama | Gypsophila | cheap | 2.73 | 0.53 | 32 |
| 5 | SKIMMIA - ramo | Skimmia | cheap | 1.82 | 4.97 | 24 |
| 6 | LISIANTHUS - MIX - flor | Eustoma | cheap | 3.64 | 1.57 | 22 |
| 7 | LIMONIUM - flor | Limonium | cheap | 1.82 | 0.56 | 33 |
| 8 | GENISTA - MIX - rama | Genista | cheap | 1.65 | 3.33 | 21 |
| 9 | ALSTROEMERIA - flor | Alstroemeria | cheap | 2.73 | 0.71 | 21 |
| 10 | RANUNCULUS GRANDE - flor | Ranunculus | cheap | 4.55 | 1.01 | 19 |
| 11 | ASTILBE MIX - flor | Astilbe | cheap | 1.82 | 0.52 | 17 |
| 12 | EUCALIPTO - Cinerea - rama | Eucalyptus | cheap | 1.82 | 3.51 | 17 |
| 13 | PHALAENOPSIS MIX - planta/28 | Phalaenopsis | premium | 25.45 | 15.78 | 16 |
| 14 | CHAMELACIUM - flor | Cera | cheap | 1.82 | 0.45 | 16 |
| 15 | RANUNCULUS - Butterfly - flor | Ranunculus | cheap | 2.73 | 0.98 | 15 |

A4.7.3. **Algorithm (для скрипта):**
```
mix_tier =
  if pack_class == 'cut':
     'cheap'    if list_price < 5
     'standard' if 5 <= list_price < 15
     'premium'  if list_price >= 15
  if pack_class == 'potted':
     'cheap'    if list_price < 8
     'standard' if 8 <= list_price < 20
     'premium'  if list_price >= 20
```

A4.7.4. **Open question (плана §11.6):** sub-agent предложил 3 tier во всех случаях. Owner ревьюит:
- (a) для срезки 2 tier (cheap/standard) или 3?
- (b) для горшечной 3 tier (cheap/standard/premium) или другие границы?

A4.7.5. **На пилоте A5** возьмём 1-2 MIX-cards (например `Phalaenopsis MIX` 28cm cheap + 35cm premium) и проверим end-to-end сценарий tier-перевода.

---

## 8. Sleeping cards (1745) — что НЕ войдёт в новый каталог

A4.8.1. **Распределение по причинам архивации:**

| Reason | Карт | Пояснение |
|---|--:|---|
| `not_used_in_2026` | 1526 | Не использовались в 179 pedido 2026. По умолчанию — archive batch при cutover (A14). |
| `seasonal_dormant` | 211 | NAVIDEÑOS / VALENTINE / HALLOWEEN / MOTHERS — спят, активируются перед сезоном. |
| `manual_review_needed` | 8 | Имеют SI, но не использовались — sub-agent просит owner'а glance. |

A4.8.2. **По top_categ:**

| Top categ (старая) | В archive |
|---|--:|
| ROOT (только корень карантина) | 649 |
| DECORACION Y ADORNOS | 383 |
| FLORES CORTADAS | 290 |
| PLANTAS EN MACETAS | 255 |
| EMBALAJE (упаковка) | 91 |
| Consumibles (расходники) | 65 |
| PRODUCTOS ESPECIALES | 6 |
| ENTREGA | 6 |
| **Итого** | **1745** |

A4.8.3. **Workflow archive в A14:**
1. Bulk-script проходит по всем 1745 карт.
2. Префикс имени `OLD_` (для бот OLD_-awareness в Make.com).
3. `archive=True` на template (Odoo каскадирует на variants — см. invariant G6).
4. `migration_status='archived'` (Studio-поле).
5. Старые pos_categ_ids очищаются (карты исчезают из POS UI).

A4.8.4. **Лист `archive_candidates`** в `migration_map_2026-05-10.xlsx` содержит все 1745 строк с колонкой `seasonal_window` для возможного re-activate перед сезоном.

A4.8.5. **NAVIDEÑOS-семья (~211)** — отдельная вкладка в плане A14: archive с `seasonal_window=Christmas`. В октябре re-activate batch.

---

## 9. Open questions for owner review (top-20)

> Sub-agent зафиксировал кейсы, где он сомневался или принял спорное решение. Owner ревьюит и правит **прямо в `migration_map_2026-05-10.xlsx`** — колонка `notes` + изменение `migration_action`.

A4.9.1. **MIX tier границы (плана §11.6).** 3 tier предложено для всех. Owner: 2 или 3 для срезки? Для горшечной?

A4.9.2. **23 multi_length_conflict карт** — supplier evidence показывает несколько длин на одну Odoo-карту, но в Odoo это flat. Sub-agent предлагает 1-axis variants. Owner: согласен или хочет split на отдельные cards?
   - Top: ALSTROEMERIA, ASTER MIX, ASTILBE MIX, ASTRANTIA, CHAMELACIUM, CLAVEL MIX, CLEMATIS, CRISANTEMO RAMI MIX, CYMBIDIUM, DELPHINIUM MIX, LILIUM, LISIANTHUS MIX, MIMOSA, PANICULATA, PANICUM, RANUNCULUS Butterfly, ROSA RAMIFICADA mambo, RS Explorer EXT, RSR ROSA RAMI MIX, SKIMMIA, TULIPAN MIX, TULIPÁN SANT VALENTÍN.

A4.9.3. **Tulipa (4 cards в одном template).** Sub-agent объединил в `Tulipa` с axis `Длина (см)`. Owner: разные varieties (Novi Sun MIX vs Fe Happy Clown vs Avignon Parrot vs Red Princess Double) — оставить 1 template или split на 2 (MIX vs single-variety)?

A4.9.4. **Ficus (11 cards в одном template).** Genus single-template с pot sizes 12-267см. Owner: split на Ficus Ginseng vs Ficus Microcarpa vs Lyrata vs остальное?

A4.9.5. **Palma (6 cards).** multi_length_conflict 12см↔190см — оставить 1 template или **split на cut palma vs potted palma** (12см обычно decorative bunch, 190см это срезка большая)?

A4.9.6. **Phalaenopsis (6 cards).** Sub-agent предлагает один template с axis `Размер горшка [18, 22, 28, 35, 42, 67]` + MIX Tier по price. Owner: проверить что 67см ≠ другая категория (например stand) и не должна быть отдельной картой.

A4.9.7. **Hydrangea — split flor vs planta.** 3 cards идут в Flores Variadas, 2 cards в Plantas para Terraza. Sub-agent оставил по pack_class. Owner: согласен или объединить как Genus level?

A4.9.8. **«Color tag» vs «Variety tag» case-sensitivity:** `Rosa` (Genus) vs `rosa` (Color). Owner: использовать case-sensitive имена или делать color tags через `color-rosa` префикс?

A4.9.9. **`product.attribute` registry — clean up.** 29 attributes в registry от прошлых test-runs. Owner: удалить старые id=14-29 (no_variant) или оставить как есть и создать новые 3 (Длина / Размер горшка / MIX Tier)?

A4.9.10. **5 Cajas без default_code** (🚧🟠 prefix from Make.com бот). При миграции — присвоить SKU из supplierinfo? Или оставить без default_code?

A4.9.11. **115 cards no_holded_match** — нет в Holded. Sub-agent ставит `new_x3_placeholder`. Owner: какие — уже used 2026? (10 из 395 used cards — без Holded match).

A4.9.12. **DECORACION 1 used card** — куда определяется? Сейчас sub-agent кинул в Productos Especiales. Owner: оставить там или сделать минимальное `Decoración` дерево?

A4.9.13. **8 manual_review_needed** archive cards — имеют supplierinfo, но не использовались в 2026. Owner: посмотреть глазом — это только seasonal или реально ненужные.

A4.9.14. **POS вкладка «Cajas» (12 cards)** — отдельной themed-вкладки для cajas нет. Они под `📦 Embalaje`. Owner: сделать отдельную `🎁 Cajas` или достаточно того что есть?

A4.9.15. **Rosa Ramificada vs Rosa Uniflora** — сейчас по сабкатегу. Owner: достаточная гранулярность или есть ещё типы (Spray, Garden Roses)?

A4.9.16. **Chrysanthemum split (2 cards)** — sub-agent оставил отдельно. Owner: merge в один template Chrysanthemum?

A4.9.17. **65 review_too_cheap** (margin <2x) — преимущественно горшечная. Owner: реально ли там margin низкая или это потому что Holded цена с НДС и мы сравнивали без?

A4.9.18. **11 review_too_expensive** (margin ≥8x) — top: ASCLEPIA 0.91€/0.06€, ASPIDISTRA Falcatus 0.45€/0.05€. Owner: проверить что это не сбой mapping (например cost от другой карты).

A4.9.19. **Image strategy для multivariant.** На template — supplier-фото, на variant — то же фото или другой ракурс? (open vопрос плана §8.3)

A4.9.20. **Динамические POS-вкладки реализация.** Cron+toggle vs `available_in_pos`+computed-fields vs другое. Решается в A8 (open вопрос плана §4.2).

---

## 10. Что дальше

A4.10.1. **После owner-review этого draft:**
- Owner правит `migration_map_2026-05-10.xlsx` (особенно колонки `migration_action`, `new_template_name`, `new_categ_path`, `new_variant_attributes`, `mix_tier`, `notes`).
- Spomena в чате — что было скорректировано.
- Sub-agent / owner закрывает **A4** и переходит к **A5 pilot multivariant**.

A4.10.2. **A5 pilot scope** — 1-2 multivariant template end-to-end через v2.2:
- Например `Rosa Red Naomi 50/60/70` или `Phalaenopsis MIX 22/28/35`.
- Создать template + variants в Odoo, перенести `default_code` + `barcode` от донорской карты, валидировать stock/POS/pricelist behaviour.
- Если успешно — A6 bulk skeleton + migration of remaining cards.

A4.10.3. **Параллельно** (не блокирует A5):
- A8: создать `pos.category` структуру + 3 product.attribute (Длина / Размер горшка / MIX Tier).
- Tag registry — добавить ~50 недостающих genus tags + новые категории (Color, Origin, Light, MixTier, Treatment, PackMode, Variety).

A4.10.4. **Не делаем сейчас:** Не пишем в Odoo в рамках A4. Не создаём category / tags / attributes — это в A8 после ревью.

---

## См. также

- [05_2026-05-10_migration_plan.md](05_2026-05-10_migration_plan.md) — карта блоков A1-A14 + принятые решения
- [05_2026-05-10_audit_quarantine.md](05_2026-05-10_audit_quarantine.md) — A1 снимок (источник 395 used + 1745 sleeping)
- [05_catalog.md](../05_catalog.md) — toolkit миграции v2.2
- `pedido.files/migration/migration_map_2026-05-10.xlsx` — per-card данные на 3 листах
- `pedido.files/migration/build_a4_design.py` — pipeline сборки (для воспроизводимости)
- `pedido.files/migration/a3_extracted_attributes_2026-05-10.xlsx` — A3 attributes basis
