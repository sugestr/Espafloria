<!-- v: 20 | updated: 2026-05-03T00:00Z -->
# Verdnatura Reception — Agent Specification

**Audience:** autonomous reconciliation agent (subagent) обрабатывающий Verdnatura albaranes 2026.

**Goal:** разобрать pedido (обучить карточки, упорядочить supplierinfo, расставить цвета) и закрыть его (`state=purchase` + picking done) с точным совпадением суммы paper.Total. Если уверенно закрыть нельзя — оставить красным с activity.

---

## §0. EXECUTIVE SUMMARY (read this first)

Pedido = диалог трёх источников:
- **Paper PDF от Verdnatura** = единственная истина по бумаге (refs, qty, price, IVA, address).
- **Holded import в Odoo** = бухгалтерский ввод. Полезен ровно в двух местах: (a) выбор `product_id` (на какую карту положили), (b) физический пересчёт qty (`x_studio_expected_qty`). Всё остальное (price, line.name, supplier_sku) — игнор.
- **Algorithm decisions** = бот переписывает что нужно, оставляет что верно.

**Hard rules (нарушение = bug):**

**HR1.** Без paper PDF не закрываем — никогда.

**HR2.** Никогда не сравниваем Holded цену с paper. Paper price пишется silent на каждой строке.

**HR3.** Каждое решение per строка — decisive: **A (change)** / **B (silent accept)** / **C (blocker)**. Никаких половинных «orange и продолжим если не уверен».

**HR4.** `author_id=56` на ВСЕХ chatter messages. Через `mcp__odoo__create_record('mail.message', {...})`, **не** `message_post` (та escape'ит HTML).

**HR5.** `tracking_disable=True, mail_create_nolog=True, mail_notrack=True` на ВСЕХ writes/buttons под bot.

**HR6.** **Wrong match worse than unmatched.** Лучше оставить строку красной с activity, чем притянуть неправильный товар.

**HR7. Не выдумывать решение лишь бы закрыть.** Если бот реально не уверен — красный + activity, без попыток подобрать «правдоподобное». Closing rate ≠ метрика качества.

---

## §1. INPUT / OUTPUT CONTRACT

### §1.1 Inputs (два режима)

**Pass1 mode** (default — массовый разбор):
- `pedido_id` (int) — `purchase.order.id` в Odoo
- `paper_pdf_path` — `/Users/andriy/Documents/espafloria.odoo/pedido.files/reception_paper/verdnatura_<docNum>.pdf`

PDF уже прицеплен к pedido в `ir.attachment` через bulk pre-step (см. `09_reception_INSTR_attach_pdf.md`). Агент читает с диска через `pdftotext`, не лезет в attachment.

**Pass2 mode** (для красных после owner-резолва):
- `pedido_id` + `owner_resolution_text` (string, простой язык)
- Активируется явным input (см. §H для разбора).

### §1.2 Output success
- `purchase.order.state` = `'purchase'`
- Все `picking_ids[].state` = `'done'`
- `amount_total ≈ paper.Total ±0.05€` (см. §G hard gates)
- 1× `mail.message` (author=56, через direct create) — summary 3-слойный
- 1× `mail.activity` если есть `🟠`/`🔴` строки (yellow silent)
- Все `stock.move.x_studio_review_color ∈ {2, 3, 8, 10}` или 0 (если delta within MINOR)

### §1.3 Output blocker (легальный finalize-stop)
- `purchase.order.state` = `'draft'` или picking ещё не done
- `mail.activity` создан с описанием блокера простым языком
- НЕ trigger 1217
- Pedido попадает в pass2 queue

---

## §2. CONSTANTS

| Параметр | Value |
|---|---|
| Verdnatura `partner_id` | **42** (внимание: `23` — посторонняя запись, **НЕ использовать**) |
| Claude AI Reconciliation `partner_id` (author) | **56** |
| Andriy `user_id` (activity owner) | **2** |
| `res_model_id` для `purchase.order` | **819** |
| `activity_type_id` (To-Do) | **4** |
| Tax IDs: 10% R goods / service | **68** / 70 |
| Tax IDs: 21% G goods / service | **7** / 8 |
| UoM Tallo/Units | **1** |
| UoM Paquete | **31** |
| Carantine root category | **207** (см. §A4) |
| Action server 1217 (finalize trigger) | **1217** |
| Next free SKU formula | `MAX(product.template.default_code regex '^84001\d{3}$') + 1` (НЕ hardcode) |
| review_color palette | 1=red, 2=orange, 3=yellow, 8=dark-blue, 10=green |
| MINOR_THRESHOLD (soft delta) | **5 stems** |
| Sum gate допуск | **±0.05€** (см. §G) |

---

## §3. CORE PIPELINE (10 steps)

### Step 1 — Detect mode
Если на входе `owner_resolution_text` непустой → **Pass2 mode**, перейти на §H. Иначе — Pass1 mode, продолжать.

### Step 2 — Parse paper PDF
```bash
pdftotext -layout <paper_pdf_path> -
```
Extract:
- **Dirección de entrega** (для §A1 warehouse match). Не путать с **Datos fiscales** («MUNTANER 260» — регистрация, не shipping).
- Per-line: `Ref`, `Cant`, `Concepto`, `Productor`, `PVP`, `IVA` (R/G), `Importe`, под-строка с атрибутами (`COLOR`, `ALTURA`, `MACETA`, **`UD VENTA`** — критично для pack/stem, `PESO`, `Nº FLORES` etc.)
- `Subtotal` + IVA cuota + `Total`.

**Validity check**: если pdftotext не содержит keywords {`Cant`, `Concepto`, `Total`} → BLOCKER C (битый PDF).

Sanity: `Σ(Cant × PVP) ≈ Subtotal`; `Subtotal × (1 + IVA) ≈ Total`.

### Step 3 — Warehouse address check (§A1)
Сравни paper «Dirección de entrega» с `purchase.order.picking_type_id.warehouse_id`.
- **Match** → продолжаем нормально.
- **Mismatch** → **НЕ блокер разбора**. Создаём activity «🟠 адрес бумаги X, pedido висит на Y — какой склад правильный?». Финализацию **дожидаемся owner** (через pass2).

### Step 4 — Pull Odoo lines
```python
mcp__odoo__search_records('purchase.order.line',
  domain=[['order_id','=',pedido_id]], order='id asc')
```

### Step 5 — Identity match per Odoo line (§A2)
Для каждой Odoo line найти соответствующую paper line. Strict identity gate + flexibility — см. §A2.

### Step 6 — Per-line decisions (§B)
Для каждой строки **6 решений:**
1. **Card** (§B1) — keep / reassign / создать новую / blocker
2. **Quantity** (§B2) — paper-truth с tolerance
3. **Pack vs stem** (§B3)
4. **Tax** (§B4) — производная от карточки
5. **Price** (§B5) — paper PVP silent
6. **Name** (§B6) — sync `[paper.ref] paper.concepto (paper.productor)`

Write в purchase.order.line:
```python
update_record('purchase.order.line', line_id, {
    'product_id': new_variant_id,           # если reassign (§B1A)
    'name': f'[{paper.ref}] {concepto} ({productor})',
    'product_qty': paper.cant,              # paper-truth (для pack: число пачек)
    'price_unit': paper.PVP,                # silent
    'uom_id': 31 if is_pack else 1,
    'tax_ids': [[6, 0, [tax_id]]],
    'x_studio_supplier_sku': paper.ref,
    'x_studio_supplier_product_name': full_concepto_with_attrs,
    'x_studio_expected_qty': florist_count,  # для pack: stems от Holded recount
    'x_studio_item_comment': formatted_comment_3layer,  # см. §C4
})
```

### Step 7 — Detect bookkeeper errors (§F)
Применить 4 детектора (digit-loss / lost line / extra line / substitution) к строкам. Каждый детектор — оранж + reassign/add/zero, **если бот уверен**. Если не уверен — красный (HR7).

### Step 8 — Learn supplierinfo + enrich template (§A3)
Для каждой не-blocker строки upsert supplierinfo (paper.ref + price + uom_id + date_start). Enrich template (description_purchase, x_studio_codigo_fabrica). Mandatory chatter на template с **причиной создания** (если new card) — см. §C5.

Native attributes (§A6) — placeholder, applied когда attribute setup готов.

### Step 9 — Pre-flight + hard gates (§G)
Проверить hard gates. Если хоть один не прошёл — **НЕ trigger 1217**, легальный blocker, activity.

### Step 10 — Trigger action 1217
```python
update_record('purchase.order', pedido_id, {'x_studio_claude_finalize': True})
sleep 10
```
Verify: `state='purchase'` AND `picking.state='done'` → SUCCESS. Иначе FAIL → §E retry.

### Step 11 — Post 3-layer summary + activity (§C2 + §C3) — **AGGREGATE, не re-analyze**

**Принцип:** к этому моменту все правки уже сделаны. Бот **не пересчитывает** paper-vs-Odoo для summary. Источник — **working context самого агента** (он помнит каждое per-line решение из шагов 5-7 текущего pedido). Re-read из Odoo (`item_comment` + `review_color` per stock.move) — только fallback на restart / retry / pass2 после прерывания.

```python
# Из working context агента (нулевая стоимость):
counts = group per-line decisions by color
patterns = group decisions by detector_tag (digit_loss / lost_line / extra_line / substitution / pack_conv / reassign / mix_consolidate / mix_split / new_card)
orange_list, red_list, clean_list = filter decisions by color
summary_html = format per §C2
if any(color in {2, 1}): activity_html = format per §C3
```

Direct create `mail.message` (НЕ message_post — escape'ит HTML). Activity — **только** при `🟠`/`🔴` (yellow silent).

---

## §A — REFERENCE TABLES

### §A1 Warehouse mapping

| Paper «Dirección de entrega» содержит | Warehouse | picking_type_id |
|---|---|---|
| **Olimpic** / **Castelldefels** | Blau (id 4) | 28 (`BLA/IN/`) |
| **Augusta** / **Augusta 109 (bis)** | Plaza (id 2) | 10 (`PLA/IN/`) |
| **Diagonal** / **Macinista** / **Sant Martí** | Gloria (id 3) | 19 (`GLO/IN/`) |
| **Muntaner 260** | Temporal (id 5) | 37 (`TMP/IN/`) — закрытый магазин, scrap planned |
| Прочее / пусто | flag → owner activity | — |

Mismatch — НЕ блокер разбора, ждём финализации до pass2 с owner-ответом.

### §A2 Identity matching

#### §A2.1 Strict identity gate
Match только когда specific narrow species/type plausibly the same.

**OK:** rose↔rose, chrysanthemum↔chrysanthemum, eucalyptus cinerea↔eucalyptus cinerea, photinia↔photinia, bouquet↔bouquet (только при strong direct evidence).

**Reject:** rose↔tulip, photinia↔madroño, eucalyptus cinerea↔eucalyptus parvifolia (разные species — не match, не MIX), цветок↔растение горшечное, ваза↔роза.

#### §A2.2 Broad tokens НЕ identity
`bouquet`, `bqt`, `mix`, `tropical`, `assorted`, `decorative`, `floral`, `greenery` — generic, сами по себе **не** establish identity.

#### §A2.3 Identity flexibility (внутри narrow block)
Когда specific identity passes gate, эти различия НЕ ломают match: variety/cultivar/color/producer/style wording/legacy Odoo naming.

Примеры OK: freesia soleil↔freesia rosario; rose Mondial↔rose Pretty Pillow; bamboo прямой↔bamboo крученный; photinia red robin↔generic «PHOTINIA» (если supplierinfo подтверждает).

#### §A2.4 Evidence priority (от сильного к слабому)
1. **Learned codigo** — `supplierinfo(partner=42, product_code=paper.ref)` указывает на template совпадающий с Odoo line.product_id
2. **Operator hit** — `x_studio_operator_hit == paper.ref`
3. **Existing assignment** — бухгалтер's product_id если identity passes
4. **Fabrication code** — `paper.ref` substring в `x_studio_codigo_fabrica`
5. **Default code** — `paper.ref == default_code`
6. **Semantic similarity** — fuzzy concepto. Last resort.

#### §A2.5 Match-method discipline
Label всегда **сильнейшее actual evidence**. Precedence: `supplierinfo_code > fabrication_code > default_code > semantic_name`. Никогда не label `semantic` если есть code hit.

#### §A2.6 Confidence bands
- 0.92-0.98 — direct learned vendor code
- 0.88-0.95 — direct operator hit
- 0.84-0.91 — fabrication/default code OR very strong specific identity (HIGH threshold для §B1)
- 0.74-0.83 — clean specific identity без direct code
- 0.62-0.73 — weaker assigned-card / semantic
- <0.62 — обычно unmatched

**HIGH = ≥0.84.** Не downgrade learned vendor code или operator hit потому что Odoo card name ugly/legacy.

#### §A2.7 Preserve existing card
Сохраняем assigned product_id когда identity passes gate AND нет clearly stronger competing candidate. Reject только при hard species conflict OR явно лучший candidate на сильнейшем evidence. **Quantitative threshold:** existing card имеет ≥1 supplierinfo с близкой ценой (±50% от paper.PVP) → keep (consolidate OK).

#### §A2.8 Matching algorithms (после identity gate passed)
1. **Positional 1:1** — paper line[i] ↔ Odoo line[i], если N=M и порядок не нарушен
2. **Match по qty (N=M, порядок сбит)** — переставь Odoo строки чтобы paper.cant матчила line.product_qty; tie-breaker — concepto similarity
3. **Match по концепту fuzzy** — substring/Levenshtein на concepto ↔ template.name OR default_code (если identity gate проходит)
4. **Multi-paper → 1 Odoo MIX consolidate** — N paper строк (одного species) на одну MIX-карту, sum paper.cant ≈ Odoo product_qty. Match подтверждён, MIX корректна (см. §B1a)

Если ни один не даёт надёжный match → unmatched + activity (НЕ blocker C если строка чистая, blocker C только при concrete identity risk).

### §A3 Supplierinfo + template enrichment

**Цель:** карточка после reconcile = обученная для будущих pedidos.

#### §A3.1 Когда учим
**Учим все non-blocker строки.** Не учим **только blocker C** (где идентификация не подтверждена). После owner-резолва на pass2 — учим финальную карточку.

Card type (placeholder/quarantine/normal) **не критерий**. Не теряем data на любую decisively-обработанную строку.

#### §A3.2 Supplierinfo upsert (create OR update existing empty)
**До create — search:** `product.supplierinfo([['partner_id','=',42],['product_tmpl_id','=',tmpl_id],['product_code','in',[False, '']]])`. Если найдена пустая default — **обновляем её** вместо дубликата. Иначе — create new.

| Field | Value |
|---|---|
| `partner_id` | 42 |
| `product_tmpl_id` | template-id |
| `product_code` | paper.ref (**критично — без этого не обучена**) |
| `product_name` | `<concepto> (<productor>) <key_attrs>` |
| `price` | paper.PVP per uom |
| `min_qty` | 1 |
| `date_start` | paper.FECHA |
| **`uom_id`** | **31 для pack, 1 для stem.** Без этого Odoo берёт template.uom_id и цена интерпретируется неправильно. |

#### §A3.3 Template enrichment (одновременно с supplierinfo)
| Field | Когда писать | Value |
|---|---|---|
| `description_purchase` | Всегда если empty | `Auto-enriched from paper {ref} {date}: {concepto} ({productor}). Атрибуты: {ALTURA/COLOR/MACETA/PESO/Nº FLORES — те что есть}` |
| `x_studio_codigo_fabrica` | Если empty — записать paper.ref. Если non-empty — append через `;` если ref не уже там | sequence Verdnatura refs обслуженных этой картой |

**Mandatory chatter log на template** при ЛЮБОМ изменении (description/codigo/name/supplierinfo) — см. §C5. **Особенно** при создании новой карточки — обязательно ПРИЧИНА (см. §C5).

#### §A3.4 Card rename (опционально через activity)
Если name явно generic (`🚫 RSR ROSA RAMI - MIX`) — **не переименовывать автоматически**, добавить 🟠 activity «Переименовать X → Y? Например `🚫 ROSA Mondial+Pretty Pillow MIX`».

#### §A3.5 Multi-ref на одну card (MIX consolidate)
Если N paper.ref'ов матчат одну Odoo MIX-card — создаём **N supplierinfo записей** на тот же template с разными product_code. Это **feature, не bug** — карточка обучается N codigo одновременно. MIX между поставщиками (Verdnatura + Serviflor + Rillo с разными codigo на одну template) тоже OK — не разрушать чужие supplierinfo.

### §A4 Carantine categories
- 207 — root «⛔ Карантин Holded»
- 210 — EMBALAJE
- 211 — ENTREGA
- 212 — FLORES CORTADAS (срезка)
- 213 — PLANTAS EN MACETAS (горшечные)
- 214-279 — спец. подразделы
- 280 — DECORACION
- 281 — PRODUCTO DESCONOCIDO

### §A5 Card create (§B1A когда нужна new card)

**Полный checklist полей** — карантинная карта = **прото-боевая**, заполняем как для чистого каталога:

| Field | Value |
|---|---|
| `name` | `🚧🟠 <paper.concepto>` |
| `default_code` | `MAX(default_code regex '^84001\d{3}$') + 1` |
| `barcode` | `default_code` если categ=212 (FLORES CORTADAS); manufacturer barcode допустим если categ ∈ {213, 280, 210} |
| `categ_id` | по типу (§A4) |
| `type` | `'product'` |
| `list_price` | 0 |
| `standard_price` | paper.PVP |
| `uom_id` / `uom_po_id` | 1 (Tallo) или 31 (Paquete) по UD VENTA |
| `purchase_method` | `'receive'` |
| `description_purchase` | `Auto-created by Claude AI <date> from paper {ref} {concepto} {productor}. Атрибуты: {paper sub-line attrs}` |
| `x_studio_codigo_fabrica` | paper.ref |
| **`image_1920`** | `set_binary_field(source='https://cdn.verdnatura.es/image/catalog/1600x900/<paper.ref>')`, 404 → leave empty |

После create — **mandatory chatter с ПРИЧИНОЙ** (см. §C5) + supplierinfo upsert (§A3).

### §A6 Native Odoo product.attribute mapping

**Status:** PLACEHOLDER. До setup `product.attribute` в Studio — атрибуты в `description_purchase` (§A3.3). После setup — read-and-link к existing values на template, не на variant.

---

## §B — DECISION TREES

**Decisive rule:** A (change) / B (silent accept) / C (blocker). Никаких половинных. Если не уверен — C (HR7).

### §B1 Card decision (per line) — симметричная ревизия

```
match = identity_match_result(paper, odoo_line)

if match.confidence ≥ HIGH AND match.product_id == odoo_line.product_id:
    → KEEP product_id silent. No marker.

elif match.confidence ≥ HIGH AND alternative_card exists:
    → VARIANT A: reassign product_id. 🟠 orange.
    Item_comment: "🟠 Бухгалтер положил на X, в бумаге Y. Перенёс."

elif match.confidence < HIGH AND нет clear alternative:
    → BLOCKER C 🔴. Не trigger 1217. 
    Activity: "Не нашёл подходящей карты для <paper.concepto>. Создать новую?
              Если да — где (карантин 212/213/...)? Owner: ответь."

elif существующий placeholder card (⛔НОВЫЙ ТОВАР / FLOR EXOTICA):
    → search существующие robo-cards (84001*, 84009*) → reassign если нашёл
    → если ничего не нашёл AND identity ясен → create new в карантине (§A5) + reassign 🟠
    → если identity не ясен → BLOCKER C 🔴

else:
    → проверить §B1a MIX vs §B1b distinct (симметрично)
```

#### §B1a MIX preferred (consolidate)

Дефолт = keep как у бухгалтера. Перетасовка distinct→MIX только при сильной причине ниже.

**MIX consolidate OK silent (без оранжа) когда ВСЕ ТРИ:**
- Same species, varying cultivar/variety/color/producer (CL разных сортов = Dianthus caryophyllus разных cultivar; PHAL разных variants — Phalaenopsis cultivars). **НЕ** разные species (EUC cinerea ≠ EUC parvifolia — НЕ MIX).
- Price ratio ≤ 1.5: `max(prices_on_card) / min(prices_on_card)`
- Sales usage — продаются клиенту как один SKU

**Триггер для distinct → MIX перетасовки** (orange action): N paper строк одного species, identity-flexibly различимые, ratio цены ≤1.5, эти строки сейчас раскиданы по N distinct картам с примерно одинаковой ценой. Редко. Если хоть один критерий не выполнен → keep как у бухгалтера.

На MIX-карту учим N разных Verdnatura ref через supplierinfo (§A3.5). MIX между поставщиками — feature.

Карту можно/нужно переименовать на инклюзивное имя (например `BAMBU прямой и крученный`, `Salix tinted family`). **Не используй слово «MIX»** в name если есть конкретное описание форм.

#### §B1b Distinct cards (split — Variant A)

Дефолт = keep. Перетасовка MIX→distinct только когда хотя бы одно AND identity diff явный:
- Premium variety (цена ×1.5+ от средней по семье) с visible identity diff (Monstera Variegata Thai vs обычная Monstera)
- Продаются как separate SKU (клиент выбирает по сорту/цвету)
- Business-критично для аналитики маржи

Action: Variant A — найти existing distinct card OR create new (§A5) + reassign + 🟠 orange.

#### §B1c Search before create (mandatory)
Перед `create new card`:
1. Search robo-cards (icons `🤖🚧` / `🚧🟠` / `🚧` / `🤖`, ranges 84001152+, 84009*)
2. Search чистая зона: исключающее `🚫` префикс, по `name ilike paper.concepto`
3. Если нашёл точное identity → reassign (Variant A с existing)
4. Только если нет нигде → create new (§A5)

### §B2 Quantity decision (per line)

#### Detect pack/stem
```python
is_pack = (
    'UD VENTA Paquete' in paper.attributes
    OR known_pack_product(concepto)  # Mimosa, Skimmia, EUC, Lentisco, Acacia, Ranunculus pequeño, etc.
    OR (existing supplierinfo for ref имеет uom Paquete)
    OR (paper.qty vs Odoo.qty имеют ratio ≥3 без явных stem signals)
)
```

#### Tolerance
```python
if is_pack:
    tolerance = min(max(15, int(paper.qty * 0.30)), paper.qty)
else:  # stem
    tolerance = max(4, int(paper.qty * 0.05))
```

#### Decision matrix (упрощённая, 3 случая для stem)
| Сравнение | Action | review_color |
|---|---|---|
| Δ ≤ tolerance в любую сторону | accept что есть silent | ✅ green |
| Odoo > paper, Δ > tolerance, ≤ MAJOR_THRESHOLD | accept Odoo silent (бухгалтер пересчитал, +N от поставщика) | 🟡 yellow (silent в комментарии, без activity) |
| Odoo < paper, Δ > tolerance | paper-truth override + activity «бумага говорит +N, физически проверь» | 🟡 yellow |
| Δ ekstrем (>50% paper) AND нет signals pack/digit-loss | проверить §F детекторы (digit-loss / lost / extra). Если детектор не сработал → BLOCKER C | 🔴 red |

`MAJOR_THRESHOLD = max(15, int(paper.qty * 0.30))`.

#### Decision matrix (pack)
| Сравнение | Action | review_color |
|---|---|---|
| Pack pure paper-match (paper.cant == Odoo.paq) + UoM=Paquete + expected_qty filled | accept | ✅ green + 📦 |
| Pack with Δ ≤ tolerance | accept | ✅ green + 📦 |
| **Pack-conversion alone** — бухгалтер импорт сделал в stems, бот переводит в paq + UoM=31 + expected_qty=stems, без Δ qty | **silent green + 📦 — НЕ orange** | ✅ green + 📦 |
| Pack with Δ > tolerance на pack qty | paper-truth override + activity | 🟠 orange + 📦 |

### §B3 Pack treatment (когда `is_pack=True`)

Pack count и stem count = два независимых числа. **НЕ** используем `uom.factor` для конвертации (плавающее число штук в пачке).

| Field | Value |
|---|---|
| `product_qty` | paper.cant (количество **пачек**) |
| `uom_id` | 31 (Paquete) |
| `price_unit` | paper.PVP per paq |
| `x_studio_expected_qty` | florist physical stems (Holded recount) |
| Phase A2 (action 1217): | `stock.move.quantity = expected_qty` (точные штуки), `stock.move.x_studio_received_packs = paper.cant` |

Backorder не создаём. Если пришло 17 stems вместо 20 — silent accept.

📦 icon в item_comment line 1: `✅ Пачки <name>. N пачек × ~M stems = total шт на склад.`

**Если `expected_qty` пустое на pack line:** BLOCKER C — без recount нельзя положить точные штуки на склад, activity «нет recount от бухгалтера, нужен ручной пересчёт».

### §B4 Tax decision

**Принцип:** налог = производная от карточки (правильно учили — налог правильный). Доп проверка по бумаге.

- paper IVA = R 10% → `tax_ids = [[6, 0, [68]]]` (goods) или 70 (service)
- paper IVA = G 21% → `tax_ids = [[6, 0, [7]]]` (goods) или 8 (service)
- Если Odoo line имеет другой / пустой tax → переписать.

### §B5 Price — silent paper-truth

Всегда: `price_unit = paper.PVP`. **Никаких markers** в item_comment, **никаких сравнений** с Holded (Holded цена = шум). Округление до 5 центов = подгонка, silent overwrite.

Если paper.PVP = 0 (очень редко) → flag для owner, **не write** 0.

### §B6 Name sync
`name = f'[{paper.ref}] {paper.concepto} ({paper.productor})'`. Переписываем если:
- ref в текущем name `[xxx]` ≠ paper.ref
- name пустой / generic placeholder
- card был reassigned

Sync — НЕ отдельный orange trigger. Часть пакета изменений по строке.

### §B7 Color assignment matrix (по итогу 6 решений per line)

| Цвет | ID | Когда |
|---|---|---|
| 🟢 green | **10** | Perfect OK: paper.qty матчит Odoo.qty (точно или within MINOR), identity confirmed. Включая accept-Holded ≤MINOR positive delta, pack-conversion within tolerance (📦) |
| 🤖 dark blue | **8** | **Robot clean fill** — бот заполнил пустую/generic Phase A (line пришла из Holded import без supplier_sku или без expected_qty), positional match + learned codigo подтвердил identity, без content-changing правок |
| 🟡 yellow | **3** | **Silent diagnostic** — Δ>tolerance с paper-truth override на stem, либо детектор digit-loss сработал. **Activity НЕ создаётся** (yellow silent в item_comment). Gate проходит. |
| 🟠 orange | **2** | **Substantial auto-fix** — reassign card / split MIX / consolidate в MIX / create new card / pack-conversion с Δ>tolerance / lost line добавлена / extra line обнулена / substitution исправлена. **Activity создаётся** для ревью. Gate проходит. |
| 🔴 red | **1** | **Blocker C** — identity не подтверждён, нет alternative для placeholder reassign, битый PDF, sum gate не сошёлся, expected_qty пустое на pack line. **Activity создаётся** для owner. Gate **блокирует** финализацию. |

**Pseudocode (first match wins):**
```python
# 1. Hard blockers
if identity hard-conflict OR placeholder без alternative OR expected_qty пустой на pack OR sum gate fail:
    color = 1  # red

# 2. Substantial structural fixes
elif (card reassigned) OR (new card created) OR (MIX consolidate from distinct) OR (MIX split to distinct) OR (pack-conversion with Δ>tolerance) OR (lost line added) OR (extra line zeroed) OR (substitution corrected):
    color = 2  # orange

# 3. Silent diagnostic
elif (Δ>tolerance с paper-truth override на stem) OR (digit-loss detector triggered):
    color = 3  # yellow (silent, no activity)

# 4. Robot clean fill
elif (Phase A on Odoo line was empty/generic before bot's write — нет supplier_sku OR нет expected_qty originally — AND bot confirmed identity via supplierinfo):
    color = 8  # dark blue

# 5. Default green
else:
    color = 10  # green
```

**Important:** silent paper-truth `price_unit = paper.PVP` (per §B5) **не считается** правкой для color logic — это no-op. Только content-changing правки триггерят non-green.

---

## §C — TEXT FORMAT

### §C0 Универсальный 3-слойный шаблон + язык

Owner на мобильном. Везде где робот пишет текст человеку — **3 слоя**:

1. **Слой 1 — простыми словами по смыслу.** За 5 секунд понять что произошло. Эмодзи в начале (✅/🟡/🟠/🔴/📦/🚧/⛔). **БЕЗ жаргона:** ❌ `Phase A2`, `UoM=31`, `picking BLA/IN/00064`, `tax_ids`. **С жаргоном:** ✅ имена магазинов (Olimpic / Plaza / Gloria / Augusta / Diagonal), «пакетный товар», «потерял строку», «недосчитал», сумма в €.
2. **Слой 2 — точно по цифрам и данным.** Куда / зачем / как. Бумага: ref, qty, price, importe, IVA, attributes.
3. **Слой 3 — `[Лог]` для машины.** Кросс-ссылки, structured key=value.

Применяется на: `item_comment` / `mail.message` (pedido + template) / `mail.activity.note`.

### §C2 Summary message (mail.message на pedido, HTML)

AGGREGATE из working context (см. Step 11). НЕ re-analyze paper-vs-Odoo.

**Шаблон 3-слойный:**

```html
<!-- Слой 1: opening простыми словами -->
<p><b>🤖 Что случилось:</b></p>
<p>Verdnatura прислала <N> строк товара на <X>€ для магазина <name>.
Бухгалтер импортировал <M> строк (<diff: «правильно» / «на K больше» / «K строк потерял»>).
Бот: <1-2 предложения о главных правках простым языком — например «4 пакетных обработал, 1 потерянную строку добавил, на 2 поправил подмену товара»>.</p>

<!-- Слой 2: точно по цифрам -->
<p><b>Что в результате:</b></p>
<ul>
  <li>K крупных правок — описание паттерна</li>
  <li>L pack-only — clean (зелёные с 📦)</li>
  <li>M clean — без правок</li>
  <li>Сумма pedido <X>€ ↔ бумага <Y>€ ✅</li>
  <li>Picking <code> done на warehouse <name> ✅</li>
  <li>N supplierinfo обучены</li>
</ul>

<p><b>🟠 K крупных (нужен ревью):</b></p>
<ol>
  <li><b>[Ref] Concepto</b> — что было / что стало plain language</li>
</ol>

<p><b>✅ Чистых N:</b></p>
<ul>
  <li>📦 Ref Concepto (если pack)</li>
  <li>Ref Concepto (если stem)</li>
</ul>

<!-- Слой 3: лог -->
<p><code>[Лог] session=&lt;short_id&gt; algo=v20 closed=&lt;UTC ISO8601&gt;</code></p>
```

### §C3 Activity note (mail.activity note, HTML)

**Только при наличии 🟠 или 🔴 строк** (yellow silent). **Тоже AGGREGATE** из тех же `orange_list` / `red_list` собранных в Step 11 — не пересчитываем.

```html
<p><b>Pedido <docNum> — простыми словами:</b></p>
<p>1-2 предложения почему оранжевые/красные (из patterns + counts).</p>
<ol>
  <li><b>[Ref] Concepto</b> — что было / что стало (orange) ИЛИ <b>?</b> что бот не знает (red).</li>
</ol>
<p><code>[Лог] color=2|1 line_ids=...</code></p>
```

`summary` заголовок: `🟠 Pedido <docNum>: K крупных правок на ревью` или `🔴 Pedido <docNum>: K блокеров — нужно решение`.

### §C4 Item_comment per line (plain text 3-слойный)

**📦 emoji prefix mandatory для pack lines** (любого статуса). Owner должен сразу видеть в pedido list что строка пакетная.

```
Слой 1: ОБЗОР simple language. Один из:
  - "✅ Paper match: <concepto> <qty>×<price>€"  (stem clean)
  - "✅📦 Пачки <name>. <paq>×~<stems_per_paq>=<total> шт на склад."  (pack clean)
  - "🟠 Бухгалтер X, бумага Y. Поправил."  (substantial fix)
  - "🟠📦 Бухгалтер X пачек, бумага Y пачек. Поправил."  (pack with Δ>tolerance)
  - "🟠 Бот добавил потерянную строку (<concepto> 30 шт)."  (lost line)
  - "🟠 Бот обнулил лишнюю строку (нет на бумаге)."  (extra line)
  - "🟠 Бот поправил подмену: бухгалтер положил X, бумага Y."  (substitution)
  - "🟡 Paper-truth +N stems. Owner: физически проверь."  (paper>Odoo moderate)
  - "🟡 Бот поправил с 9 на 19 — похоже бухгалтер потерял разряд."  (digit-loss)
  - "🔴 BLOCKER: <причина>. Owner: <вопрос>."  (red)
  - "🔴📦 BLOCKER: нет recount от бухгалтера на pack товар."  (pack red)

Слой 2: Бумага factual.
  "Бумага: <qty> <pак|шт> × <price>€ = <importe>€ (Verdnatura ref X, IVA Y%, ALTURA Z)."

Слой 3: [Лог] machine-readable.
  "[Лог] supplier_sku=X expected_qty=N price=Y paper_match=<reason> [card=...] [old_card=...] [detector=digit_loss|lost_line|extra_line|substitution]"
```

### §C5 Template chatter (на product.template)

**Mandatory** при любом изменении карточки роботом (description_purchase, codigo_fabrica, name, supplierinfo create/update).

**Особенно при создании новой карточки — 3 слоя с ОБЯЗАТЕЛЬНОЙ ПРИЧИНОЙ:**

```html
<p><b>🚧 Создал новую карту</b></p>
<p>Не нашёл подходящей в каталоге. Бухгалтер положил на placeholder ⛔НОВЫЙ ТОВАР, я создал distinct в карантине чтобы в будущем эти строки шли на правильную карту.</p>

<p><b>Где искал:</b> robo-cards (84001*, 84009*), чистая зона по concepto, learned supplierinfo codes Verdnatura. Не нашёл нигде.</p>

<p><b>Что создал:</b> карточку в карантине FLORES CORTADAS (212), default_code=84001345, name='🚧🟠 Acacia Mimosa Bola', с фоткой Verdnatura.</p>

<p><code>[Лог] paper_ref=165920 pedido=12491307 search=robo,clean,supplierinfo categ=212 seq=84001345 image_url=cdn.verdnatura.es/.../165920</code></p>
```

При обычном update existing template — короче:
```html
<p>🤖 Robot edit (pedido <docNum>): обновил supplierinfo (codigo 165920, price 0.55€, uom Paquete). From paper ref 165920 [2026-04-15]: Acacia Mimosa Bola.</p>
```

---

## §D — ACTION 1217 CONTRACT (server-side)

Mirrored в `kb/add/09_reception_action_1217.py`. Триггер: write `x_studio_claude_finalize=True` на `purchase.order`.

### §D1 Branches
| Branch | Trigger condition | Что делает |
|---|---|---|
| **ROLLBACK** | `note` substring `ROLLBACK_HOLDED_API` | reverse done picking → button_draft → clear Phase A на лайнах |
| **RETRY** | `state='purchase'` AND есть picking не в `done`/`cancel` | soft-gate (≤MINOR_THRESHOLD=5) → button_validate(skip_backorder=True) |
| **DRAFT** | `state='draft'` | pre-flight (amount>0, all lines have supplier_sku) → button_confirm → Phase A2 → soft-gate → button_validate |

### §D2 DRAFT branch detail
1. `pedido.with_context(NO_TRACK).button_confirm()` → `state=purchase`, picking создан.
2. **Phase A2** — пишем quantity на каждый stock.move:
   - Pack lines (uom_id=31): `quantity = expected_qty` (stems), `x_studio_received_packs = product_qty` (paq).
   - Stem lines: `quantity = expected_qty || product_qty`.
   - Все writes под `tracking_disable=True, mail_create_nolog=True, mail_notrack=True`.
   - **Pre-flight invariant:** agent **обязан** залить `x_studio_expected_qty > 0` на pack lines (см. §G hard gates).
3. **Final gate by color** (§D3).
4. `picking.with_context(skip_backorder=True, NO_TRACK).button_validate()` → `state=done`.

### §D3 Gate logic (по color, не по text)
```python
PASS_COLORS = (10, 8, 3, 2)   # green, dark-blue, yellow, orange
BLOCK_COLORS = (1,)            # red

color = move.x_studio_review_color or 0
if color in PASS_COLORS: continue
elif color in BLOCK_COLORS: flag stop
else (color == 0): fallback по qty delta vs MINOR_THRESHOLD
```

### §D4 What action 1217 does NOT do (agent must do post-trigger)
- ❌ Summary message — agent через `mcp__odoo__create_record('mail.message', {...})` (HTML correct рендер).
- ❌ Activity create — agent через `mcp__odoo__create_record('mail.activity', {...})` с `res_model_id=819`.

### §D5 Constraints внутри action 1217 (safe_eval)
- ❌ `obj.field = value` (use `write({...})`)
- ❌ `type(e).__name__`, `hasattr(...)` (use `'field' in record._fields`)
- ❌ `import` statements
- ✅ `env['model'].create/search/browse`
- ✅ `with_context(...)`, `record.write(...)`

---

## §E — RETRY / IDEMPOTENCY

### §E1 Skip правила
**Skip pedido целиком** если:
- `state='cancel'`
- `state='purchase'` AND все picking_ids в `done`

**Не skip** если:
- `state='draft'`
- `state='purchase'` AND picking в любом не-done/не-cancel (RETRY case)

**Wait (не trogai)** если:
- `x_studio_claude_finalize=True` уже стоит (action 1217 в работе)

**Skip line** если:
- `item_comment` содержит `✅ Verified by Claude AI`

### §E2 Re-run на draft / RETRY pedido
Продолжаем с места где остановился. Применяем новые правила если algorithm refined после прошлого pass. На pass2 (см. §H) — применяем owner_resolution_text.

---

## §F — EDGE CASES + ДЕТЕКТОРЫ ОШИБОК БУХГАЛТЕРА

### §F1 Стандартные edge cases

| Case | Detection | Action |
|---|---|---|
| Empty paper / corrupted PDF | pdftotext output не содержит keywords {Cant, Concepto, Total} | Try `-raw` без `-layout`. Если всё равно нет — BLOCKER C |
| Multi-paper split (12439827-B/G/P) | Несколько pedidos с одинаковым ref + B/G/P суффиксом | Supervisor manual (не subagent) |
| Bookkeeper edit after first reconcile | item_comment `✅ Verified` но qty/price не совпадают | 🟡 manual_edit_detected, не trogai |
| Concepto на каталанском | Fuzzy match не находит | BLOCKER C сразу + activity. Transliteration out of scope |
| Multi-IVA на одной MIX | paper N строк с разным IVA на одну Odoo MIX | Split на N Odoo lines с тем же продуктом, разные tax_ids |
| Holded import даёт `tax_ids=[]` | Empty tax | Записать explicitly по paper IVA |

### §F2 Детекторы ошибок бухгалтера (4 типа)

Все 4 типа = **оранж** (бот сам справляется), **если бот уверен**. Если не уверен → красный (HR7).

| # | Тип | Detection | Action | Color |
|---|---|---|---|---|
| 1 | **Digit-loss** (потерял разряд) | `paper.qty > 10 * Odoo.qty` AND identity match strong (`paper.qty / Odoo.qty ≈ 10`) | paper-truth: `product_qty=paper.qty`. Activity «🟡 поправил X→Y, бухгалтер потерял разряд». **Yellow silent**, gate проходит | 🟡 yellow |
| 2 | **Lost line** (потерял строку) | После positional match есть unmatched paper line + identity ясен (по supplierinfo / fuzzy concepto) | Создать новую `purchase.order.line` на найденную card. Activity «🟠 добавил строку которую бухгалтер потерял» | 🟠 orange |
| 3 | **Extra line** (нарисовал лишнее) | Odoo line не имеет paper-аналога AND нет evidence что это reasonable дубль | Set qty=0 на лишней Odoo-строке. Activity «🟠 обнулил лишнюю строку» | 🟠 orange |
| 4 | **Substitution by coincidence** (подмена по случайному совпадению) | Identity gate fails, но qty/name совпадают подозрительно близко (например бухгалтер положил OZOTHAMNUS, бумага F Arroz Pink) | Reassign product_id на бумажный (если бот **уверен** что нашёл правильную карту в каталоге). Activity «🟠 поправил подмену X→Y» | 🟠 orange |

**Если бот не уверен в identity для Тип 2 (на какую карту положить потерянную) или Тип 4 (правильная карта существует?) → НЕ ИЗОБРЕТАТЬ, BLOCKER C 🔴 (HR7).**

**Sub-cases:**
- **SKU typo Levenshtein 1-2** (бухгалтер ошибся 1-2 символами в codigo) — `Levenshtein(paper.ref, learned.codigo) ∈ {1,2}` AND identity match по concepto strong → reassign на правильный codigo + 🟠 orange + activity «коррекция SKU typo X→Y»
- **Phantom dup** (Odoo 2 одинаковые, paper 1) — same product_id, same qty → обнулить вторую (qty=0) + comment, как Extra line

---

## §G — HARD GATES ФИНАЛИЗАЦИИ (consolidated)

Если хоть один gate не прошёл — **НЕ trigger 1217**, легальный blocker, activity, pass2 queue.

| # | Gate | Условие pass | Если fail |
|---|---|---|---|
| G1 | Все lines имеют `x_studio_supplier_sku` | непустое значение на 100% lines | BLOCKER C |
| G2 | Pack lines имеют `expected_qty > 0` | uom_id=31 → expected_qty заполнено | BLOCKER C, activity «нет recount на pack» |
| G3 | Нет красных строк | все `review_color != 1` | BLOCKER C на каждой red |
| G4 | **Сумма pedido ≈ paper.Total** | `abs(amount_total - paper.Total) ≤ 0.05€` | BLOCKER C, activity «не сошлась сумма с бумагой на N€, проверь построчно» |
| G5 | Σ subtotal check | `abs(Σ(line.qty × line.price) - paper.Subtotal) ≤ 0.05€` | BLOCKER C, activity «не сошлась subtotal — сигнал что одна из строк не правильная» |
| G6 | Адрес mismatch (§A1) | warehouse адрес матчит | **НЕ блокер**, activity и финализацию ждём pass2 |

---

## §H — PASS2 MODE ADDENDUM

**Activated** когда на входе есть `owner_resolution_text` (string, простой язык). Supervisor уже разобрал ответы owner из чатеров/активити pedido и сформулировал инструкции для агента в свободной форме — фиксированной схемы нет.

**Pass2 pipeline** (вместо §3 Step 1-11):
1. Read pedido state — red lines (`review_color=1`), open activities, owner messages в чатере (`user_id=2` после bot's activity).
2. Apply `owner_resolution_text` к каждой red line. Поддерживаемые cases (supervisor разбирает на них):
   - `reassign` — переложить product_id на указанную карту: «для строки 7 переложи на PHAL Eleg Cascade»
   - `create` — создать новую карту в карантине (§A5 + §A3): «создай новую под ROSA Premium SEL, типа FLORES CORTADAS»
   - `confirm` — подтвердить spornoe («confirm warehouse Plaza, продолжай»)
   - `keep` — оставить как у бухгалтера несмотря на blocker («для substitution оставь, не трогай»)
3. Re-evaluate color — red → orange (substantial fix с одобрения) или green (просто confirm). **Учим supplierinfo на финальной карте** (§A3) — не теряем data.
4. Run hard gates (§G) → trigger 1217 если passed.
5. Post 3-layer summary (§C2) с пометкой `[pass2]` в opening.
6. Если после pass2 всё равно red — escalate owner ad-hoc (третий проход не алгоритмизирован).

---

## §I — SUPERVISOR-LEVEL WORKFLOW

Этот блок — для supervisor session, не для agent.

### §I1 Pass1 batch
1. Setup (один раз): pedidos re-imported, supplierinfo wiped, action 1146 + 1217 prod, paper PDFs синкнуты + прицеплены через `09_reception_INSTR_attach_pdf.md`, native attributes setup в Studio (§A6) когда готово.
2. Pilot pass — supervisor сам обрабатывает 5-10 первых pedidos, refines algorithm decisions с owner.
3. Algorithm freeze — fix v20, commit.
4. Batch — subagents per 10 pedidos, owner checkpoints после каждой партии.
5. Closed-clean → готово. Closed-with-orange → owner ревью через активити. Red blockers → pass2 queue.

### §I2 Pass2 dispatch
1. Owner отвечает на красные blockers в чатере/активити конкретных pedidos простым языком.
2. Supervisor собирает ответы (читает чатеры pedidos где есть unresolved red).
3. Для каждого красного pedido — формирует `pedido_id + owner_resolution_text`, запускает agent в **pass2 mode**.
4. Agent применяет resolution, перепрогоняет красные, финализирует.
5. Если после pass2 всё равно red — escalate owner ad-hoc (третий проход не алгоритмизирован, supervisor + owner решают вручную).

### §I3 Special cases
- **6 не-numeric pedidos** (12439827-B/G/P, correction-*) — manual через supervisor (multi-warehouse split / merge / cancel).
- **Out-of-scope Verdnatura**: Serviflor (без codigo — adjusted algorithm), holded.factura split — отдельные workflow.

---

## §J — RUNTIME CHECKLIST (для agent перед каждым pedido)

- [ ] paper PDF доступен на `pedido.files/reception_paper/verdnatura_<docNum>.pdf`
- [ ] mode определён (pass1 / pass2)
- [ ] partner=42 (Verdnatura, **не 23**)
- [ ] §0 hard rules + §G hard gates прочитаны

---

## §K — STOP SIGNAL PROTOCOL

Subagent работает автономно — не разговаривает с owner мидл-pedido (только через `mail.message` summary + `mail.activity` после verify). Но **если** в любой точке pipeline возникает прямое owner-input в чате (`СТОП` / `постой` / много восклицательных знаков / «отмени»):
- **Немедленно** прерывает текущий pedido — никаких «ещё одно действие и остановлюсь»
- Постит chatter с фактом остановки + текущим прогрессом
- Сбрасывает `x_studio_claude_finalize=False` если был выставлен
- Возвращает control supervisor

Не продавливать через. Остановка важнее завершения.

---

## §L — OPEN ITEMS (для supervisor, не для agent)

- **MCP user attribution** — MCP authenticate'ится как Andriy → line writes идут от его имени. Bot res.users + отдельный API key (требует licensing review).
- **Action 1217 cleanup** — добавить `x_studio_expected_qty: False` в ROLLBACK clear-set. Auto-cancel orphan backorder через штатный `picking.action_cancel()`.
- **§A6 native attributes setup** — список атрибутов и Studio create — отдельная задача до запуска.
