<!-- v: 21.10 | updated: 2026-05-03T20:30Z -->
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

**§3 Step 2.1 Multi-albarán PDF (v20.2)**: paper PDF может содержать несколько albaranes (factura format с N albaranes на одну invoice — например factura A12610404 содержит 12297344 / 12277169 / 12281779 / 12287826 / 12294902 / ...).

Detection:
- В text есть **multiple** `Albarán <docNum>` headers (regex `Albarán\s+\d{8}`) → multi-albarán mode
- ИЛИ paper PDF имеет word `Factura A\d+` в header (вместо `ALBARÁN`)

Workflow в multi-albarán mode:
1. Найти target docNum через `re.search(r'Albarán\s+' + target_docnum + r'.*?(?=Albarán\s+\d{8}|Subtotal|$)', text, re.DOTALL)`
2. Парсить только ЭТУ секцию (lines + subtotal + IVA)
3. Если target docNum НЕ найден в PDF → BLOCKER C «paper PDF не содержит target albarán».

Supervisor может **починить paper PDF** (extract pages, replace attachment) — см. handover (TBD: future doc) для recipe. Алгоритм agent просто работает с тем что прицеплено, и legalно блокирует если не находит.

### Step 3 — Warehouse address check (§A1)
Сравни paper «Dirección de entrega» с `purchase.order.picking_type_id.warehouse_id`.
- **Match** → продолжаем нормально.
- **Mismatch** → **НЕ блокер разбора**. Создаём activity «🟠 адрес бумаги X, pedido висит на Y — какой склад правильный?». Финализацию **дожидаемся owner** (через pass2).

### Step 4 — Bulk preload pattern (v21.0 REWORK)

**Цель:** на старте pedido загрузить в memory **всё** что понадобится для решений per line — чтобы decisions phase делалась **БЕЗ дополнительных MCP search calls**. Уменьшает API calls с ~50-95 до ~25 per pedido.

**4.1 Read all PO lines** (1 call):
```python
lines = mcp__odoo__search_records('purchase.order.line',
    domain=[['order_id','=',pedido_id]],
    fields=['id','product_id','product_qty','price_unit','name','uom_id','tax_ids',
            'x_studio_supplier_sku','x_studio_expected_qty',
            'x_studio_supplier_product_name','x_studio_item_comment',
            'x_studio_operator_hit'],
    order='id asc')
```

**4.2 Extract unique template/product IDs** (in memory):
```python
product_ids = list(set(l['product_id'][0] for l in lines))
# product_id → product_tmpl_id mapping needed (variant→template)
products = mcp__odoo__search_records('product.product',
    domain=[['id','in',product_ids]],
    fields=['id','product_tmpl_id','default_code','product_template_attribute_value_ids'])
template_ids = list(set(p['product_tmpl_id'][0] for p in products))
```

**4.3 Bulk read templates** (1 call):
```python
templates = mcp__odoo__search_records('product.template',
    domain=[['id','in',template_ids]],
    fields=['id','name','default_code','barcode','categ_id','sale_ok',
            'list_price','standard_price','uom_id','type','is_storable',
            'description_purchase','x_studio_codigo_fabrica','active',
            'product_variant_count','attribute_line_ids'])
# image_1920 НЕ грузим — просто заметить empty/non-empty через отдельный thin search:
templates_with_image = mcp__odoo__search_records('product.template',
    domain=[['id','in',template_ids],['image_1920','!=',False]],
    fields=['id'])
templates_without_image_set = set(template_ids) - {t['id'] for t in templates_with_image}
```

**4.4 Bulk read attribute_lines на preloaded templates** (1 call):
```python
attribute_lines = mcp__odoo__search_records('product.template.attribute.line',
    domain=[['product_tmpl_id','in',template_ids]],
    fields=['id','product_tmpl_id','attribute_id','value_ids'])
```

**4.5 Bulk read supplierinfo Verdnatura для preloaded templates** (1 call):
```python
supplierinfo = mcp__odoo__search_records('product.supplierinfo',
    domain=[['partner_id','=',42],['product_tmpl_id','in',template_ids]],
    fields=['id','product_tmpl_id','product_id','product_code','price','uom_id',
            'min_qty','date_start','product_name'])
```

**4.6 Lazy load attribute_values — только для used attributes этого pedido** (1 call):

Перед этим вызовом — **parse paper PDF** (Step 2 уже сделан) и **extract** какие attribute tags реально встречаются в paper sub-lines. ATTR_MAP в §A6 дает 17 attribute_ids общего списка, но на одном pedido обычно используется **5-7** (Color, Altura, UD Venta, Nº Tallos, Peso — типичный набор).

```python
# Из паршеных paper.lines extract used tags
used_attr_ids = set()
for paper_line in paper.lines:
    for tag in paper_line.attributes:  # already parsed sub-line
        attr_id = ATTR_MAP.get(normalize(tag))
        if attr_id:
            used_attr_ids.add(attr_id)

# Load values ТОЛЬКО для used (обычно 5-7 attribute_ids, не 17)
attribute_values = mcp__odoo__search_records('product.attribute.value',
    domain=[['attribute_id','in', list(used_attr_ids)]],
    fields=['id','name','attribute_id'])
# Index: {(attr_id, name_normalized): value_id} for fast lookup
```

**Speedup:** ~3× faster чем preload всех 17 (load ~30-50 values вместо ~150-300).

**Total Step 4: 5-6 search calls для **полной** preloaded картины этого pedido.**

**Step 5+ (decisions) делается через memory dict lookups, не MCP**:
- Identity match — lookup `templates[tmpl_id]['name']` / `codigo_fabrica` / `default_code`
- Codigo learn — lookup `supplierinfo` filtered by `product_tmpl_id`
- Attribute upsert — lookup `attribute_lines` для template + `attribute_values` для re-use
- §B1c search before create — `templates` dict содержит все candidate cards уже

Если **fuzzy semantic search across all catalog** нужен (новая card, нет identity на preloaded templates) — fallback к single MCP search. Это редкий path (~5% lines).

**⚠️ ANTI-PATTERN (v21.3): mid-process MCP re-reads запрещены**

После любого write (line / template / supplierinfo / attribute_line) **НЕ** делай дополнительный MCP read для confirm result. **Trust write success** — MCP вернул `success:True` достаточно. Update local `ctx` dict с новыми value (чтобы downstream Step 5+ видели свежий state из memory).

**Запрещено:**
- Per-line `get_record` после `update_record` line
- Per-template `get_record` после `attribute_line.create`
- Per-supplierinfo verify после `create`
- Re-read templates после batch update

**Разрешено (один раз каждое):**
- Step 4 initial bulk preload (~5 calls)
- Step 9 batch §A6.2 variant_count verify (1 call, batch all touched templates)
- Step 10 после trigger 1217 — final verify pedido state + picking + stock.moves (3 calls)
- Step 11 ничего read не нужно (write summary + activity)

**Pilot 11 incident (2026-05-03):** subagent делал per-template variant_count read = 5 extra calls. Total ~36 vs target 25-30. Net +5 calls бесплатно потеряно. Spec теперь explicit: batch verify = 1 call.

**§3.A Memory data structures (v21.0):**

```python
ctx = {
    'pedido_id': int,
    'lines_by_id': {line_id: line_dict},
    'lines_ordered': [line_dict, ...],  # by id asc
    'templates_by_id': {tmpl_id: tmpl_dict},
    'products_by_id': {product_id: product_dict},  # variant → template lookup
    'attribute_lines_by_tmpl': {tmpl_id: [attr_line_dict, ...]},
    'supplierinfo_by_tmpl': {tmpl_id: [supplierinfo_dict, ...]},
    'attribute_values_by_attr': {(attr_id, name): value_id},
    'templates_without_image': set(),
    'paper': {'docNum', 'lines': [...], 'subtotal', 'iva_breakdown', 'total', 'address', 'fecha'},
}
# All Step 5-9 decisions read/write `ctx` (in memory).
# Step 10 (writes) накапливает changes в `ctx['pending_writes']`, затем flushes.
```

### Step 5 — Identity match per Odoo line (§A2) — **memory-based (v21)**
Для каждой Odoo line найти соответствующую paper line. **Все evidence lookups через preloaded `ctx` dicts** (templates_by_id / supplierinfo_by_tmpl / attribute_lines_by_tmpl / products_by_id). НЕ делать дополнительные MCP search calls на каждой строке.

Strict identity gate + flexibility — см. §A2.

**Fuzzy fallback (rare ~5%):** если paper line не находит identity на preloaded templates (новая card, нет в этом pedido) → **тогда** разрешён 1 MCP search для broader catalog fuzzy match. Если и так не найден → BLOCKER C 🔴 (или create new per §B1A).

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
Для каждой не-blocker строки:
- Upsert supplierinfo (paper.ref + price + uom_id + date_start) — §A3
- Enrich template (description_purchase, x_studio_codigo_fabrica) — §A3.3
- **Upsert native attributes** на template из paper sub-line (COLOR / ALTURA / MACETA / UD VENTA / etc.) — см. §A6 pipeline. ATTR_MAP константа.
- Mandatory chatter на template с **причиной создания** (если new card) — §C5

### Step 9 — Pre-flight + hard gates (§G)
Проверить hard gates. Если хоть один не прошёл — **НЕ trigger 1217**, легальный blocker, activity.

### Step 10 — Trigger action 1217
```python
update_record('purchase.order', pedido_id, {'x_studio_claude_finalize': True})
sleep 10
```
Verify: `state='purchase'` AND `picking.state='done'` → SUCCESS. Иначе FAIL → §E retry.

**Action 1217 v8.0 (2026-05-03)** автоматически устанавливает retroactive delivery date:
- `paper_fecha = pedido.date_order` (= paper.FECHA из Holded import)
- Если `paper_fecha < (now - 7 days)` → `delivery_date = paper_fecha + 1 day` (старый pedido — typical supplier +1 day delivery)
- Иначе → `delivery_date = now()` (свежий pedido)
- Updates: `picking.date_done`, `stock.move.date`, `purchase.order.date_approve`
- Stock-side only (`purchase_method='receive'` для цветов — bills отдельным flow)
- Subagent **не должен** вручную писать эти даты — action 1217 делает.

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

**Latin↔Spanish common names — valid identity flexibility (v20.2):**
- OZOTHAMNUS diosmifolius ↔ Flor de Arroz / F Arroz Pink (rice flower) — paper «F Arroz Pink», Odoo card `🚫 OZOTHAMNUS - flor` с `codigo_fabrica` «ARROS, FLOR DE ARROZ, ARR» — identity OK, не reassign.
- Когда `codigo_fabrica` содержит aliases / synonyms / botanical+common names — это explicit **trained identity flexibility**, использовать как evidence #4 (fabrication code) per §A2.4.

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

#### §A2.7 Preserve existing card — scaled price gate + flag suspicious (v21.6)

**Default = keep bookkeeper's product_id assignment** даже если paper concepto на нескольких lines выглядит «похоже». Reject default ТОЛЬКО при выполнении ВСЕХ:

1. **Hard species conflict** существует (rose↔tulip, eucalyptus cinerea↔parvifolia — разные species)
2. ИЛИ **явно лучший candidate** найден на сильнейшем evidence (learned codigo / operator hit)
3. **Scaled price gate passes** (см. §A2.7.1)

#### §A2.7.1 Scaled price gate (v21.6 — заменяет flat 1.5)

Старый flat `ratio <= 1.5` равно работал для роз 0.5€ и для бонсая 15€. Это **некорректно**: для дешёвых товаров normal price spread выше (varieties rose 1.0↔1.8 = same MIX), для дорогих spread меньше (бонсай 9↔17 = разные products).

```python
def is_same_product(price_a, price_b):
    """v21.6 scaled threshold — учитывает absolute + relative."""
    avg = (price_a + price_b) / 2
    ratio = max(price_a, price_b) / min(price_a, price_b)
    abs_diff = abs(price_a - price_b)
    
    if avg < 3:        # very cheap (роза, gypso, аспарагус, paniculata stem)
        return ratio <= 2.5 and abs_diff <= 1.5
    elif avg < 8:      # mid (lilium, peonia, tulipan, plantas T12-T17)
        return ratio <= 1.7 and abs_diff <= 3.0
    elif avg < 20:     # expensive (cymbidium short, premium roses, BONS Ginseng)
        return ratio <= 1.4 and abs_diff <= 5.0
    else:              # very expensive (vases, decoración premium, multi-set boxes)
        return ratio <= 1.25 and abs_diff <= 10.0
```

**Применение в reassign decision:** перед `write({'product_id': X})` если X != original — compute gate против existing supplierinfo на candidate template. **Pass → reassign OK. Fail → preserve bookkeeper.**

#### §A2.7.2 Flag suspicious price spread (v21.6 NEW — catch bookkeeper errors)

После Step 8 supplierinfo upsert на template — verify **gate против всех pairwise supplierinfo prices** на этой template (партнёр Verdnatura). Если хоть одна пара **fails gate** → bookkeeper потенциально put 2 разных products на одну card.

```python
suppliers_v = supplierinfo_by_tmpl[tmpl_id].filter(partner_id=42)
prices = [si.price for si in suppliers_v if si.price > 0]
if len(prices) >= 2:
    # Pairwise check
    for i in range(len(prices)):
        for j in range(i+1, len(prices)):
            if not is_same_product(prices[i], prices[j]):
                # SUSPICIOUS — create activity на template
                create_activity_on_template(tmpl_id, 
                    summary=f'⚠️ Price spread suspicious: {min(prices)}€..{max(prices)}€',
                    note=f'Card hosts {len(suppliers_v)} Verdnatura refs '
                         f'with prices {sorted(prices)}. Possibly different products. '
                         f'Visit shelf to verify identity.')
                # break — one activity per template, не spam
                break
```

**Pilot 11 incident retro (2026-05-03 после re-evaluation):** card 7126 (FICUS BONSAI - planta/25) держал refs 165850 (9.26€) и 199106 (16.75€). Pairwise: avg 13.0€ (expensive band), ratio 1.81 > 1.4, abs 7.49 > 5.0 — **fail gate**. Должна быть activity для review. После owner verify: 199106 reassigned на 7083 (FICUS BONSAI GINSENG con maceta cerámica) — корректное место. Это **именно тот тип ошибки** который scaled gate должен ловить.

**§B1a MIX consolidate criteria** наследуют тот же scaled gate — алгоритм consolidate vs preserve unified.

#### §A2.7.3 Stem-line qty gate via margin cross-check (v21.8 NEW — catch bookkeeper import bugs)

**Проблема (bulk batch 1, pedido 12186266):** ref 57603 CL Solomio Edo SEL — paper 40 stems, бухгалтер записал в Holded `1` штуку (broken import — Holded иногда выгружает default `1` вместо реального qty при сбое API). Бот доверчиво поставил expected_qty=1, на склад ушёл 1 stem вместо 40, активность создана но color только 🟡 yellow silent.

**Принцип решения:** для STEM lines (uom=Tallo), bookkeeper recount **не верим** если он даёт **absurd margin** относительно paper. Margin × как cross-check на qty integrity.

```python
def stem_qty_gate(line, paper_cant, expected_qty, list_price, price_unit):
    """v21.8 — catch bookkeeper qty import bugs via margin cross-check.
    
    Применяется ТОЛЬКО к stem lines (uom=Tallo, не pack).
    Применяется ТОЛЬКО когда expected_qty != paper_cant (есть divergence).
    """
    # Skip if no significant divergence or tiny line
    if expected_qty == paper_cant or paper_cant < 5:
        return ('keep', None)
    
    # Compute margin both ways
    if not list_price or not price_unit:
        return ('keep', None)  # nothing to cross-check against
    
    # Margin if we trust paper as physical truth (price_unit per stem, 1:1)
    margin_via_paper = list_price / price_unit
    
    # Margin if we trust bookkeeper recount (cost spread over fewer/more stems)
    cost_per_stem_recount = (price_unit * paper_cant) / expected_qty if expected_qty else float('inf')
    margin_via_recount = list_price / cost_per_stem_recount if cost_per_stem_recount else 0
    
    # Decision matrix:
    # - margin_via_recount < 1.0 (loss territory) AND margin_via_paper >= 1.0 (sane)
    #   → bookkeeper data broken, override expected_qty = paper.cant + orange + activity
    # - both sane (>= 1.0) → keep recount as physical (legit small loss/damage scenario)
    # - both loss → both broken? rare, kepp as-is + red blocker
    
    if margin_via_recount < 1.0 and margin_via_paper >= 1.0:
        return ('override_to_paper', f'Bookkeeper recount={expected_qty} → margin ×{margin_via_recount:.2f} (loss). Paper={paper_cant} → margin ×{margin_via_paper:.2f} (sane). Override.')
    
    if margin_via_recount < 1.0 and margin_via_paper < 1.0:
        return ('blocker_c', f'Both margins loss-territory. Identity или price может быть кривое. Owner-resolve.')
    
    if margin_via_recount >= 10.0:
        return ('high_soft_flag', f'Margin ×{margin_via_recount:.1f} необычно высоко. Возможно устарел list_price на карточке, или вендорский бонус (recount > paper). Не override, но проверь.')
    
    # v21.9 NEW: large divergence on stem without margin signal — no auto-decision
    rel_diff = abs(paper_cant - expected_qty) / max(paper_cant, expected_qty)
    if rel_diff > 0.30:
        return ('large_divergence_no_override',
                f'Stem-line: paper={paper_cant}, bookkeeper={expected_qty} (divergence {rel_diff*100:.0f}%). '
                f'Margin sane в обоих сценариях (×{margin_via_paper:.1f} vs ×{margin_via_recount:.1f}), '
                f'не уверен кто прав. Не override — owner physical verify.')
    
    return ('keep', None)
```

**Action на `override_to_paper`:**
- `x_studio_expected_qty = paper.cant`
- `product_qty = paper.cant` (already paper-truth)
- Phase A2 picking → `quantity = paper.cant` (full paper qty)
- color = 🟠 orange (substantial autofix)
- activity на pedido: «Строка X: detected import bug (paper N stems, Holded recount K). Override на N. Физически проверь сколько реально пришло.»

**Action на `blocker_c`:** красный + activity + НЕ trigger 1217.

**Action на `high_soft_flag` (v21.8):**
- `expected_qty` НЕ override — recount скорее всего верный, проблема в list_price freshness или это legit бонус.
- color = 🟠 orange (требует ревью).
- activity на pedido: «Строка X: margin ×{m:.1f} необычно высоко. Проверь list_price на карточке (может устарел) ИЛИ это вендорский бонус (recount > paper — норма). Сделай решение.»

**Action на `large_divergence_no_override` (v21.9 NEW):**
- `expected_qty` НЕ trogaem (keep bookkeeper input as default — что бухгалтер записал).
- `product_qty` = paper.cant (paper-truth для bill).
- color = 🟠 orange.
- activity на pedido: «Stem-line N: paper={X}, bookkeeper={Y} (divergence {pct}%). Margin sane в обоих сценариях — бот не уверен кто прав. Физически проверь сколько реально пришло.»

**Когда срабатывает (vs другие gates):**
- Расхождение >30% на stem-линии при paper.cant ≥ 5
- Margin **в обоих сценариях** sane (между 1.0 и 10.0) — иначе сработали бы LOSS / HIGH gates
- Pack lines не applies (для них divergence = ожидаемое поведение detector pack-conv)

**Принцип:** **«не уверен → не решай»**. Бот не должен молча принимать сторону, которая может быть случайно правильной. Расхождение ×2 (как ALLIUM 20↔40 или ASPIDISTRA 10↔5) — слишком много чтобы пройти мимо.

**Pilot retro 12210647 (2026-05-03):** обе линии (ALLIUM и ASPIDISTRA) были закрыты yellow silent. Должны были orange + activity. Retro-fixed: stock.move color 3→2, activity создана на каждую. См. activities 323, 324 на pedido 47828.

**Когда НЕ срабатывает (legit cases):**
- Pack lines (uom=Paquete): не applies, для pack divergence — это ожидаемое поведение (paper packs ≠ recount stems).
- Stem с малым delta (paper 40, recount 39): не trigger т.к. margin via recount ~×1.83, sane — нормальная фактическая проверка.
- Stem с большим delta но обоими margin sane (1.5–10): keep (например paper 40, recount 30 — physical loss 10 шт, margin via recount всё ещё ×1.55 = норма).

**Mnemonic для owner ревью (живой контроль через Margin × колонку в Studio):**

Studio decoration на `Margin ×` синхронизирован со spec gate:

| Margin × | Visual | Семантика | Бот действие |
|---|---|---|---|
| < 1.5 | 🔴 red | убыток / cost ≥ price | gate `override_to_paper` (если loss) или `blocker_c` (если оба broken) — auto-override + activity |
| 1.5 — 2.5 | 🟡 yellow | тонко, ниже target | normal flow, без флага |
| 2.5 — 10 | 🟢 green | норма (target ×3) | normal flow |
| ≥ 10 | 🔵 blue | подозрительно высоко | gate `high_soft_flag` — activity, без override |

**Принцип:** **оба** края (×<1.5 и ×≥10) подозрительны для бота, оба триггерят activity на pedido. Разница в действии: low → override qty, high → не трогаем qty, флагуем list_price.

**Дополнительно (v21.9):** даже если margin в обоих сценариях sane, **расхождение qty paper vs bookkeeper >30% на stem-линии** = orange + activity (gate `large_divergence_no_override`). Бот не молча выбирает чью сторону держать — owner verify обязателен. Это закрывает класс ошибок типа ALLIUM (paper 20 / bookkeeper 40 = vendor-bonus или import-bug) и ASPIDISTRA (paper 10 / bookkeeper 5 = loss или recount-error) которые margin gate не ловит.

**Pilot retro:** этот gate retroactively применён к ref 57603 на pedido 47812 — `expected_qty 1→40`, +39 stems в BLA/Stock, color 🟡→🟠, activity создана. См. chatter 19111.

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

**Idempotent rule (v21.1):** для каждого `paper.ref` на pedido — supplierinfo на template должна существовать с `product_code = paper.ref`. Перед create:

```python
existing = ctx['supplierinfo_by_tmpl'][tmpl_id]
already = next((si for si in existing if si.product_code == paper.ref), None)
if already:
    # уже создана — update price если изменилась, иначе skip
    if already.price != paper.PVP:
        update_record('product.supplierinfo', already.id, {'price': paper.PVP})
    continue  # NEXT REF, не create дубликат

# Search empty default (одно из существующих без code)
empty_default = next((si for si in existing if not si.product_code), None)
if empty_default:
    # обновляем empty default с current ref/price/name
    update_record('product.supplierinfo', empty_default.id, vals)
else:
    # create new с full vals
    create_record('product.supplierinfo', vals)
```

**Sanity check (v21.1):** после create verify `record.product_code != False` AND `record.price != False`. Если any field empty — **delete record + retry create** с правильными vals. **Никогда не оставлять supplierinfo без `product_code`** (это «dummy» — мусор каталога, см. pilot 8 incident 2026-05-03).

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
| `image_1920` (v20.2) | На existing template если **`image_1920=False` AND есть paper.ref** | `set_binary_field(source='https://cdn.verdnatura.es/image/catalog/1600x900/<paper.ref>')`, 404 → leave empty. Дёшево, free improvement каталога — фотка появляется при первом upsert на existing card. |

**Mandatory chatter log на template** при ЛЮБОМ изменении (description/codigo/name/supplierinfo) — см. §C5. **Особенно** при создании новой карточки — обязательно ПРИЧИНА (см. §C5).

#### §A3.4 Card rename (опционально через activity)
Если name явно generic (`🚫 RSR ROSA RAMI - MIX`) — **не переименовывать автоматически**, добавить 🟠 activity «Переименовать X → Y? Например `🚫 ROSA Mondial+Pretty Pillow MIX`».

#### §A3.5 Multi-ref на одну card (MIX consolidate)
Если N paper.ref'ов матчат одну Odoo MIX-card — создаём **N supplierinfo записей** на тот же template с разными product_code. Это **feature, не bug** — карточка обучается N codigo одновременно. MIX между поставщиками (Verdnatura + Serviflor + Rillo с разными codigo на одну template) тоже OK — не разрушать чужие supplierinfo.

**КРИТИЧНО (v22.0, 2026-05-04 owner directive):** MIX consolidate работает ТОЛЬКО на supplierinfo level. На purchase.order.line **N paper-строк = N pedido-lines**, ВСЕГДА. Никогда не сливать 2+ paper-строк в одну pedido-line, даже если они на одну MIX-карту.

- ❌ НЕТ: line `[171788+171791] RANUN Hanoi+Marleene MIX` qty=40 price=1.65 (avg)
- ✅ ДА: 2 lines на одну card 8400530:
  - line 1: `[171788] RANUN Hanoi (Del Golfo)` qty=20 price=1.74 sku=171788
  - line 2: `[171791] RANUN Marleene (Del Golfo)` qty=20 price=1.56 sku=171791

**Why:** owner смотрит pedido lines как mirror бумаги — 6 строк бумаги должны быть 6 строк pedido. Иначе сложно сверить, теряются индивидуальные цены/qty, искажается analytics («какая роза была дороже»).

**Stock side:** на каждую line — отдельный stock.move на picking. На существующую MIX-карту это даст N stock.move'ов на одну product_id — это ОК, Odoo это поддерживает.

#### §A3.6 Supplierinfo на color/size variants (v20.2 NEW)

Когда card имеет variants (Color / Size / Color×Size combinations) и codigo per variant unique — supplierinfo должна **pin product_id** (variant), а не только product_tmpl_id.

**Правило:**
- Если paper даёт **один codigo** на template (без разделения по variant) → `product_id=False`, `product_tmpl_id=<id>` — applies to all variants
- Если paper даёт **разные codigos на разные variants** (как Caja Symphony Negro 68103 vs Rojo 67808) → `product_id=<variant_id>`, `product_tmpl_id=<id>` — pin к specific variant

**Пример (pilot 3 → retro-fix Caja Symphony 6 SKU):**
- 6 variants на template 7856 (Color × Size: 2 colors × 3 sizes)
- Paper.ref 68103 (Negro) → 3 supplierinfo на 3 size variants Negro: pin product_id=8335 (Negro+Grande), 8336 (Negro+Mediano), 8337 (Negro+Pequeño)
- Paper.ref 67808 (Rojo) → 3 supplierinfo на 3 size variants Rojo: pin product_id=8338, 8339, 8340

Иначе supplierinfo template-level applies to ALL 6 variants — collision при purchase planning.

### §A4 Carantine categories

```
207 ⛔ Карантин Holded (root)
├── 208 Consumibles (расходники)              ← oasis, бумага, бечевик
├── 209 DECORACION Y ADORNOS (parent)         ← multi-use декор
│   └── 216-246 (ACCESORIOS DECORATIVOS, ADORNOS DE PAPEL, NAVIDEÑOS, ...)
├── 210 EMBALAJE (упаковка) (parent)          ← одноразовая упаковка
│   └── 247 BOLSAS / 248 CINTAS / 249 EMBALAJE / 250 OASIS / 251 TARJETAS / 252 VBOX(CAJAS)
├── 211 ENTREGA (parent)
│   └── 253-258 (BCN-EXPRES, OTRAS, TAXI-GLOVO, ZONA 1/2/3)
├── 212 FLORES CORTADAS (parent)              ← товар-срезка
│   └── 259 BAMBU / 260 BAYAS / 261 CONIFERAS / 262 CORONAS / 263 FLORES VARIADAS /
│       264 SECAS / 265 FRUTAS,VERDURAS / 266 RAMAS,FOLLAJE / 267 ROSA RAMIFICADA / 268 ROSA UNIFLORA
├── 213 PLANTAS EN MACETAS (parent)           ← товар-горшечная
│   └── 269 CACTUS / 270 AÉREAS / 271 AROMÁTICAS / 272 BULBOSAS / 273 COLGANTES /
│       274 CON FLORES / 275 FOLLAJE / 276 FRUTALES / 277 NAVIDEÑAS / 278 TERRAZA / 279 SUCULENTAS
├── 214 PRODUCTOS ESPECIALES (parent)
│   └── 280 DECORACION / 281 PRODUCTO DESCONOCIDO / 282 PRODUCTO POR ENCARGO /
│       283 RAMO DESCONOCIDO / 284 REDONDEO / 285 SERVICIO DE FLORISTA
└── 293 EQUIPAMIENTO (оборудование) ← v20.2 (после pilot 2 retro-fix Tijeras)
                                       ← многоразовые инструменты, не товар, не расходник
```

#### §A4.1 Decision matrix categ_id для card create (v20.2)

| concepto pattern (case-insensitive) | categ_id | examples |
|---|---|---|
| flores срезка: rama / hoja / herbacea / flor / ramo / bouquet | **212** или подкатегории 259-268 | Rosas, Clavel, Eucalipto, Bambu, Photinia, Astilbe |
| plantas en macetas: planta / planta T## / planta/cm | **213** или подкатегории 269-279 | Phalaenopsis, Ficus Ginseng, Sedum, Succulentus |
| упаковка одноразовая: Bolsa / Bolso / Caja paper / VBOX / Cesta single-use / Tarjeta / Cinta | **210** или 247-252 | Bolsa Nature, VBOX paper round, Caja Symphony |
| расходники: Oasis / spray / gel / pegamento / Algodón / Esponja / бумага floristica | **208** или 250 (OASIS) / 251 (TARJETAS) | Oasis, Mini-bag |
| **многоразовое оборудование: Tijera / Cuchillo / Pinza / Cubos / Soporte / Caballete / Secador / Maceta multi-use** | **293** | Tijera Ippon, Tijera Podar, Cubos Expositor |
| декор многоразовый: Florero / Vase / Jarrón / Candelabra / Cesta multi-use | **209** или 280 | Cesta Piel, Jarrón Diábolo |
| entrega/доставка | **211** или 253-258 | — |
| неопознанное (нет identity match): generic «producto» / нет concepto | **281** или 283 | — |

**Heuristic порядок**: пройти по строкам сверху вниз, первое совпадение wins. «Многоразовое оборудование» (293) проверять до «декор» (280) — Tijera уйдёт в правильную, не в декор.

### §A5 Card create (§B1A когда нужна new card)

**Полный checklist полей** — карантинная карта = **прото-боевая**, заполняем как для чистого каталога:

| Field | Value |
|---|---|
| `name` | `🚧🟠 <paper.concepto>` |
| `default_code` | `MAX(default_code regex '^84001\d{3}$') + 1` |
| `barcode` | **NON-EQUIPAMIENTO**: `default_code`. **EQUIPAMIENTO (categ 293)**: `False` (v22.0, 2026-05-04 owner directive: оборудование не продаётся → barcode не нужен). При collision (existing product с тем же barcode) — leave `False` + activity «duplicate barcode». |
| `categ_id` | по §A4.1 decision matrix |
| `type` | `'consu'` (Odoo 19 — НЕ `'product'`, устарело) |
| `is_storable` | `True` (Odoo 19 для tracking inventory) |
| **`sale_ok`** | **`False`** (v20.2 — карантин не продаётся в живом POS до promotion в clean) |
| `purchase_ok` | `True` |
| `list_price` | **NON-EQUIPAMIENTO**: `round(standard_price * 3, 2)` ex IVA (×3 от закупки, owner правило). **EQUIPAMIENTO (categ 293)**: `0` (v22.0 — не на продажу, цена не нужна). Owner делает review цен после, но fall-back baseline = cost×3. Если paper.PVP отсутствует и cost=0 → fall-back `round(paper.PVP * 3 / 1.21, 2)` (PVP customer-facing × 3 / 1.21). |
| `standard_price` | **paper.PVP per uom (ex-VAT)** — обязательно ставим, не оставляем 0. Odoo подхватит supplierinfo при первом receive, но baseline нужен сразу для list_price расчёта. |
| **`supplier_taxes_id`** | **`[68]` ("10% G" purchase, локальный испанский налог)**. **НИКОГДА `[20]` ("10% EU G")** — это для покупок из других стран ЕС, а Verdnatura — испанский поставщик. Аналогично 21% продукты — `[7]` ("21% G" purchase), не EU-вариант (v22.0, 2026-05-04 hotfix). |
| `taxes_id` | `[82]` ("10% G" sale) или `[5]` ("21% G" sale) по категории |
| `uom_id` | 1 (Tallo) или 31 (Paquete) по UD VENTA. **Поле `uom_po_id` НЕ существует на product.template в Odoo 19** — оно только на `product.supplierinfo`. |
| `purchase_method` | `'receive'` |
| `description_purchase` | `Auto-created by Claude AI <date> from paper {ref} {concepto} {productor}. Атрибуты: {paper sub-line attrs}` |
| **`description`** (INTERNAL NOTES) | **MANDATORY (v22.0)** — структурированный HTML-блок, документирующий ПРИЧИНУ и АВТОРА создания (правило CLAUDE.md: каждая карточка должна иметь описание ЗАЧЕМ и кем создана). Формат: см. §A5.4 ниже. |
| `x_studio_codigo_fabrica` | paper.ref |
| **`image_1920`** | `set_binary_field(source='https://cdn.verdnatura.es/image/catalog/1600x900/<paper.ref>')`, 404 → leave empty + note в description |

После create — **mandatory chatter с ПРИЧИНОЙ** (см. §C5) + supplierinfo upsert (§A3) + **activity на pedido** (см. §A5.3 «New card → physical price tag reprint»).

#### §A5.4 INTERNAL NOTES (description) шаблон — MANDATORY (v22.0, 2026-05-04)

**Owner правило (CLAUDE.md):** «каждая карточка должна иметь описание ЗАЧЕМ и кем она была создана». Применимо как к ботом-созданным, так и manual картам. Бот заполняет автоматом, manual create — owner вручную.

**HTML-шаблон для бот-карты:**

```html
<p>🤖 Карта создана ботом Claude (auto-reception v{spec_version}) {YYYY-MM-DD}<br/>
Из pedido: {pedido_id} (Holded {ac_ref} / Vendor ref {paper_vref})<br/>
Verdnatura SKU: {paper_ref} {paper_concepto} ({paper_productor})<br/>
Cost (paper PVP/u, ex-VAT): {standard_price} €<br/>
Sales price: {list_price} € (×3 от закупки, ex-VAT) | или «— (категория EQUIPAMIENTO, не на продажу)»<br/>
Photo: https://cdn.verdnatura.es/image/catalog/1600x900/{paper_ref} | + (404 — нет фото на CDN, ручно добавить) если 404<br/>
Цель: новый продукт обнаружен в paper PDF Verdnatura, не было в каталоге → ботом auto-created для приёмки.<br/>
Проверить: фото, описание, цена, налог (см. CLAUDE.md правило новой карты).</p>
```

**Обязательные элементы:**
1. **Кем создана** (🤖 Claude vs manual user) + версия spec
2. **Из какого pedido** (id + Holded AC ref + Vendor ref)
3. **Verdnatura SKU** + concepto + productor
4. **Cost / Sales price** (с пометкой ×3 или «не на продажу»)
5. **Photo URL** (с пометкой 404 если CDN не вернул)
6. **Цель** (зачем создавали — обнаружено в paper, не было в каталоге)
7. **Что проверить** owner'у

#### §A5.3 New card → physical price tag reprint activity (v21.7 NEW)

**Каждая** новая карточка, создаваемая ботом во время приёмки, означает: в магазине физически уже лежит этот товар (бухгалтер его прокатил по бумаге, picking сделан, quant создан), но **со старым ценником** или **без ценника вообще**. Owner должен найти его и переклеить.

Поэтому: **на каждую новую quarantine-карту бот создаёт activity на pedido** с конкретными данными для переклейки.

```python
mcp__odoo__create_record('mail.activity', {
    'res_model_id': 819,           # purchase.order
    'res_id': pedido_id,
    'activity_type_id': 4,         # To-Do
    'user_id': 2,                  # Andriy
    'date_deadline': (date.today() + timedelta(days=7)).isoformat(),
    'summary': f"🛍️ Новая карточка {tmpl_id} — найти {short_name} в магазине + переклеить ценник",
    'note': html_template_below,   # см. ниже
})
```

**HTML шаблон note:**
```html
<p><b>Причина:</b> в этом albaran пришло <code>{paper.ref} {paper.concepto}</code> — товар, для которого в каталоге не было подходящей карточки. Создал новую quarantine-карту {tmpl_id}, прицепил к строке pedido.</p>

<p><b>Что сделать в магазине:</b></p>
<ul>
  <li>Найти физически {short_name} (склад: {warehouse_name}).</li>
  <li>Напечатать новый ценник:<br/>
    — SKU: <code>{default_code}</code><br/>
    — Barcode: <code>{barcode}</code><br/>
    — Цена: <b>{round(list_price * 1.21, 2)}€</b> con IVA ({list_price}€ ex IVA × 1.21)</li>
  <li>Переклеить ценник (снять старый если был на этом экземпляре).</li>
  <li>В Odoo: открыть карточку, проверить — нужно ли поднять/снизить розничную цену под наш фактический рынок (бот ставит ×3 от закупки как стартовый baseline, не как утверждённую розницу).</li>
</ul>

<p><b>Связь:</b> template <a href="/odoo/products/{tmpl_id}">{tmpl_id}</a>, supplierinfo {paper.ref} (vendor_code), pedido {pedido_id}.</p>
```

**Где взять `warehouse_name`:** `pedido.picking_type_id.warehouse_id.name` (e.g. "Augusta 109", "Salamanca").

**Idempotency:** если на pedido уже висит activity с таким же `summary` (новая карточка для того же tmpl_id) — **не дублировать**. Один pedido может породить несколько таких activity (одна на каждую новую карту).

**Семантика для owner:** **«новая карточка = повод физически найти товар в магазине и переклеить ценник на новый SKU/barcode/цену»**. Это закрывает gap между бот-приёмкой (которая создала карту в Odoo) и физической реальностью (где товар лежит со старой/чужой бирочкой).

#### §A5.1 Odoo 19 quirks (pilot 1+2 confirmed)

- **Field rename**: `'type': 'product'` устарело → используй `type='consu', is_storable=True`. Подтверждено образцом existing card 8212 в каталоге.
- **`uom_po_id` нет на template**: ставь uom только через `uom_id`. Для per-supplier uom — на `product.supplierinfo.uom_id`.
- **`product_template_id` нет на purchase.order.line**: используй `product_id.product_tmpl_id` для template lookup из line.

#### §A5.2 UoM field naming в Odoo 19 — захардкожено (НЕ verify-grep'ом)

Поле UoM на каждой модели — **факт** (не runtime variable). НЕ делать grep на spec / search в Odoo чтобы verify:

| Model | Field name | Использование |
|---|---|---|
| `product.template` | `uom_id` | базовая единица |
| `product.product` (variant) | inherits from template — отдельного поля нет |
| `product.supplierinfo` | `uom_id` | per-supplier uom (может отличаться от template) |
| `purchase.order.line` | `uom_id` | UoM на line (для price interpretation) |
| `stock.move` | **`uom_id`** в Odoo 19 (было `product_uom` в Odoo 17/18 — переименовано) |
| `stock.move.line` | `product_uom_id` | да, тут другое имя — но subagent редко trogает stock.move.line |

UoM IDs (constants, см. §2): **1 = Tallo/Units, 31 = Paquete (Усреднённый)**.

### §A6 Native Odoo product.attribute mapping

**Status:** ACTIVE. Setup сделан, attributes созданы, initial values заполнены. Бот линкует на template (variants для dynamic attributes Odoo генерирует сам).

**Attribute IDs (Odoo):**

| paper sub-line tag | attribute_id | name | create_variant |
|---|---|---|---|
| `COLOR` | **11** | Color | dynamic |
| `ALTURA` | **13** | Altura | dynamic |
| `UD VENTA` / `FORMATO` | **14** | UD Venta | no_variant |
| `MACETA` | **15** | Maceta | dynamic |
| `Nº FLORES` | **16** | Nº Flores | dynamic |
| `Nº TALLOS` | **17** | Nº Tallos | no_variant |
| `TAMAÑO BOTON` / `TAMAÑO BOTÓN` | **18** | Tamaño Botón | no_variant |
| `BOTON MINIMO` / `BOTÓN MÍNIMO` | **19** | Botón Mínimo | no_variant |
| `BOTÓN` (Si/No) | **20** | Botón | no_variant |
| `DIAMETRO` / `DIÁMETRO` | **21** | Diámetro | dynamic |
| `PESO/TALLO` | **22** | Peso/Tallo | no_variant |
| `TAMAÑO FLOR` | **23** | Tamaño Flor | dynamic |
| `LONGITUD BROTE` | **24** | Longitud Brote | no_variant |
| `ANCHO SUPERIOR` | **25** | Ancho Superior | no_variant |
| `ANCHO INFERIOR` | **26** | Ancho Inferior | no_variant |
| `GROSOR` | **27** | Grosor | no_variant |
| `PESO` (без TALLO) | **28** | Peso | no_variant |

**Synonyms** (нормализуй при парсинге paper sub-line):
- `UD VENTA` ≡ `FORMATO` → attribute Ud Venta (id=14)
- `TAMAÑO BOTON` ≡ `TAMAÑO BOTÓN` → attribute Tamaño Botón (id=18)
- `BOTON MINIMO` ≡ `BOTÓN MÍNIMO` → attribute Botón Mínimo (id=19)
- `DIAMETRO` ≡ `DIÁMETRO` → attribute Diámetro (id=21)

**Pipeline (per paper line, в Step 8):**

```python
# 1. парсим sub-line
parsed = parse_paper_subline(line)  # {"COLOR": "Verde", "ALTURA": "70 cm", "Nº FLORES": "5"}

# 2. для каждого attribute:
for tag, raw_value in parsed.items():
    attr_id = ATTR_MAP.get(normalize(tag))  # из таблицы выше
    if not attr_id: continue  # неизвестный тег — log + skip
    
    # 3. найти/создать value (для dynamic — на лету; для no_variant — тоже)
    val = search_or_create('product.attribute.value',
        domain=[['attribute_id','=',attr_id], ['name','=',raw_value]],
        defaults={'attribute_id': attr_id, 'name': raw_value})
    
    # 4. убедиться что у template есть attribute_line с этим val
    line_rec = search('product.template.attribute.line',
        [['product_tmpl_id','=',tmpl_id], ['attribute_id','=',attr_id]], limit=1)
    if not line_rec:
        create('product.template.attribute.line', {
            'product_tmpl_id': tmpl_id,
            'attribute_id': attr_id,
            'value_ids': [(4, val.id)]
        })
    elif val.id not in line_rec.value_ids.ids:
        line_rec.write({'value_ids': [(4, val.id)]})
    # variants для dynamic attributes Odoo пересчитает сам
```

ATTR_MAP — константа в коде агента из таблицы выше.

#### §A6.1 Skip dynamic attributes на MIX-templates — но НЕ no_variant (v20.2 + clarification v20.3)

**Не добавлять** dynamic attribute_lines (Color id=11, Altura id=13, Maceta id=15, Nº Flores id=16, Tamaño Flor id=23, Diámetro id=21) на template если выполнено **любое** условие:

1. **Name detector** — `template.name` содержит `MIX`, `- MIX -`, `mixed`, `РСР `, `RSR `, `varied` (case-insensitive)
2. **Distribution detector** — N paper lines на этом template распределены с **N разными** values одного dynamic attribute (например: 4 paper CL refs с разными Color: Verde/Salmón/Rosa/Mixto на одной CLAVEL MIX template — distinct combination каждой невозможен)
3. **Multi-species detector (v20.2)** — `codigo_fabrica` содержит >2 разных species/common-name aliases (например MARFULL = Madroño + Arbutus + Photinia на одной card — это de-facto multi-species template)

**Что делать вместо** для **dynamic** attrs: записать значения только в `description_purchase` text + `x_studio_supplier_product_name` line + `x_studio_codigo_fabrica` (refs list). NO `attribute_line.create` для **dynamic**.

**Почему**: добавление dynamic attribute_line на template без single combination → Odoo автоматически архивирует default variant → existing PO lines / stock на default variant остаются на archived → bookkeeper UI confused (ARCHIVED banner). См. pilot 2 incident: CLAVEL MIX (template 7293) — variant default архивирован, retro-fix unarchive потребовался.

#### §A6.1.bis ⚠️ КРИТИЧНО (v20.3 после pilot 4 incident): `no_variant` атрибуты ВСЕГДА apply

**`no_variant` атрибуты variants НЕ создают, archive default НЕ происходит** — поэтому их нужно apply **на ВСЕХ templates без исключения**, включая MIX/multi-species. Список `no_variant` attributes:

- **UD Venta** (id=14) — критично для **pack товаров**: указывает что товар продаётся в paquetes
- **Nº Tallos** (id=17) — stems_per_paq для pack товаров (расчёт ratio: stems_count / paquetes)
- **Tamaño Botón** (id=18) — для роз
- **Botón Mínimo** (id=19) — для роз
- **Botón** (id=20) — для роз
- **Peso/Tallo** (id=22) — вес одного стебля (для pack: paper sub-line «PESO 150 g», «PESO 200 gr»)
- **Longitud Brote** (id=24)
- **Ancho Superior** (id=25), **Ancho Inferior** (id=26) — для коробок (paper sub-line «ANCHO SUPERIOR 24,5×24,5 cm»)
- **Grosor** (id=27)
- **Peso** (id=28) — общий вес упаковки

**Pilot 4 incident (2026-05-03)**: subagent skipped ALL attributes на MIX-templates (MARFULL, GENISTA-MIX, SKIMMIA), включая `no_variant`. Owner: «карточки пачковые не получили атрибуты — необучены». Должен был добавить `UD Venta=Paquete + Nº Tallos=N + Peso info` на каждой pack-card, even MIX. Эти атрибуты НЕ создают variants, безопасны.

**Алгоритм для template upsert (v20.3 patch):**

```python
for tag, raw_value in parsed_attrs.items():
    attr_id = ATTR_MAP.get(normalize(tag))
    if not attr_id: continue
    
    # Caveat A — runtime verify create_variant
    attr_meta = env['product.attribute'].browse(attr_id)
    create_variant = attr_meta.create_variant  # 'dynamic' | 'always' | 'no_variant'
    
    # MIX-skip применяется ТОЛЬКО к dynamic
    if create_variant == 'dynamic' and is_mix_template(tmpl):
        # skip + log в description_purchase
        continue
    
    # no_variant + always — apply unconditionally на любых templates
    upsert_attribute_line(tmpl, attr_id, raw_value)


def upsert_attribute_line(tmpl, attr_id, raw_value):
    # find/create attribute_value (existing если уже есть в системе)
    val = env['product.attribute.value'].search([
        ('attribute_id','=',attr_id), ('name','=',raw_value)
    ], limit=1) or env['product.attribute.value'].create({
        'attribute_id': attr_id, 'name': raw_value
    })
    
    line = env['product.template.attribute.line'].search([
        ('product_tmpl_id','=',tmpl.id), ('attribute_id','=',attr_id)
    ], limit=1)
    
    if not line:
        # Caveat C: первое появление — create
        env['product.template.attribute.line'].create({
            'product_tmpl_id': tmpl.id,
            'attribute_id': attr_id,
            'value_ids': [(4, val.id)]
        })
    elif val.id not in line.value_ids.ids:
        # Caveat B+C: append multi-value (preserve existing values, не overwrite)
        line.write({'value_ids': [(4, val.id)]})
    # else: value уже привязан, ничего не делаем
```

**Три caveats объясняю:**
- **A (runtime verify):** ATTR_MAP может ошибиться или Odoo config поменяется — перед apply проверяем `attr.create_variant` actual.
- **B (multi-value preserve):** Если N paper lines на одном template дают **разные** values одного `no_variant` attribute (GENISTA-MIX: Retama Rojo Nº Tallos≈7, Retama Blanco ≈9) — `append` оба value в `value_ids`, не один поверх другого. `no_variant` хранит multi-value без variant explosion.
- **C (no overwrite existing):** Если на template уже привязан `UD Venta=Tallo` (legacy), а текущий paper говорит `UD Venta=Paquete` — append Paquete рядом. Bookkeeper потом manually cleanup'нет если нужно. Алгоритм НЕ удаляет историю.

#### §A6.3 ⚠️ Final attribute completeness check (v21.2 NEW)

**После всех writes на template** (Step 8 finished) — per template которые получили supplierinfo upsert на этом pedido, **сделать final pass**:

```python
for tmpl_id, suppliers in ctx['supplierinfo_by_tmpl'].items():
    if tmpl_id not in touched_templates: continue  # обрабатывали этот pedido

    # 1. Parse все no_variant attrs из всех supplierinfo.product_name на этом template
    expected_values_by_attr = defaultdict(set)  # {attr_id: {value_name, ...}}
    for si in suppliers:
        if si.partner_id != 42 or not si.product_name: continue
        # parse «Concepto | COLOR X | ALTURA Y | UD VENTA Z | PESO/TALLO W» style
        for tag, raw_value in parse_pipe_separated(si.product_name):
            attr_id = ATTR_MAP.get(normalize(tag))
            if not attr_id: continue
            attr_meta = env['product.attribute'].browse(attr_id)
            if attr_meta.create_variant != 'no_variant': continue  # only no_variant
            expected_values_by_attr[attr_id].add(normalize(raw_value))

    # 2. Compare vs current attribute_lines
    for attr_id, expected_values in expected_values_by_attr.items():
        existing_line = next((al for al in ctx['attribute_lines_by_tmpl'][tmpl_id] 
                              if al.attribute_id.id == attr_id), None)
        existing_values = set()
        if existing_line:
            for val_id in existing_line.value_ids:
                existing_values.add(normalize(val_id.name))
        
        # 3. Find missing values
        missing = expected_values - existing_values
        if not missing: continue  # all covered
        
        # 4. Add missing values (create attribute.value if not exists)
        for value_name in missing:
            value = find_or_create_attribute_value(attr_id, value_name)
            if existing_line:
                update_record('product.template.attribute.line', existing_line.id, 
                              {'value_ids': [(4, value.id)]})
            else:
                create_record('product.template.attribute.line', {
                    'product_tmpl_id': tmpl_id,
                    'attribute_id': attr_id,
                    'value_ids': [(6, 0, [value.id])]
                })
```

**Зачем:** subagent во время line processing мог пропустить attribute_line write по любой причине (ошибка, edge case, retry). Final pass **гарантирует** что **все** no_variant atrs из supplierinfo.product_name applied на template. Multi-value preserve.

**Pilot 8 incident (2026-05-03):** TULIPAN-MIX имел 4 supplierinfo с разными Peso/Tallo (34/35/40/30 gr), но attribute_line содержал только 3 values (30 gr missing). Subagent пропустил append на one paper.ref. STATICE имел 0 attribute_lines хотя 2 supplierinfo с Peso/Tallo=30 gr. HEDERA, PANICUM, RANUNCULUS-MIX, CHAMELACIUM, ROSA AQUA, ROSA RAMI sweet gelato Sian, RS ROSA Pink Athena — все missing. **Final pass поймал бы все** автоматически.

**Stop-gap:** этот final pass — defensive, добавляет ~1-2 secs на pedido. Net win стоит.

#### §A6.2 Safety check — unarchive default variant (BATCHED v21.3)

После **всех** attribute_line writes Step 8 done — **один batch verify** для всех touched templates:

```python
# Один read для всех templates сразу (НЕ per-template loop)
touched_tmpl_ids = [...]  # из ctx, accumulated в Step 8
verify = mcp__odoo__search_records('product.template',
    domain=[['id','in', touched_tmpl_ids]],
    fields=['id','product_variant_count'])

zero_variant_tmpls = [t['id'] for t in verify if t['product_variant_count'] == 0]
if not zero_variant_tmpls:
    pass  # all OK
else:
    # Один search для archived default variants на проблемных templates
    archived = mcp__odoo__search_records('product.product',
        domain=[['product_tmpl_id','in', zero_variant_tmpls],
                ['active','=',False],
                ['product_template_attribute_value_ids','=',False]],
        fields=['id'])
    # Bulk unarchive
    for variant in archived:
        update_record('product.product', variant.id, {'active': True})
```

**Total: 1-2 reads + N writes (только если есть archived). НЕ N per-template reads.**

Сценарий: Odoo при добавлении dynamic attribute_line на template archive'ит default variant если новые variants ещё не созданы. Pilot 2 поймал это incident'ом, retro-fix потребовался.

**v21.3 правка:** **Не делай per-template MCP reads** для variant_count check — используй один batch search. Pilot 11 (12536221) делал per-template = 5 calls лишних.

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

**`UD VENTA Paquete` (или `FORMATO Paquete`) на бумаге = STRONGEST signal.** Это явное заявление поставщика «эта строка в пачках». Используется как top-priority gate в обе стороны:
- **Активирует pack treatment** даже если ratio paper.qty vs Odoo.qty всего ×2-×3
- **БЛОКИРУЕТ digit-loss detector** (§F2 Type 1) — если UD VENTA Paquete присутствует, расхождение qty это pack confusion, а не потеря разряда

```python
is_pack = (
    'UD VENTA Paquete' in paper.attributes  # STRONGEST — поставщик явно сказал «пачки»
    OR 'FORMATO Paquete' in paper.attributes  # синоним UD VENTA
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
| Odoo > paper, Δ > tolerance, ≤ MAJOR_THRESHOLD | **`product_qty=paper.cant`** (для G4/G5 sum gate), **`x_studio_expected_qty=Odoo_old`** (physical recount). v20.2: Phase A2 picking handles physical excess через expected_qty. | 🟡 yellow (silent в комментарии, без activity) |
| Odoo < paper, Δ > tolerance | paper-truth override + activity «бумага говорит +N, физически проверь» | 🟡 yellow |
| Δ ekstrем (>50% paper) AND нет signals pack/digit-loss | проверить §F детекторы (digit-loss / lost / extra). Если детектор не сработал → BLOCKER C | 🔴 red |

`MAJOR_THRESHOLD = max(15, int(paper.qty * 0.30))`.

**§B2.1 Yellow path explicit color write (v20.2):** для yellow case (Odoo>paper accept-silent OR paper-truth override) — **обязательно** `move.write({'x_studio_review_color': 3})` ПОСЛЕ `button_confirm()` создал picking. Default value `0` или `10` (green) не подходит для color-аудита и for action 1217 gate logic. Найти соответствующий stock.move через `purchase_line_id == line.id` после picking creation.

#### Decision matrix (pack)
| Сравнение | Action | review_color |
|---|---|---|
| Pack pure paper-match (paper.cant == Odoo.paq) + UoM=Paquete + expected_qty filled | accept | ✅ green + 📦 |
| Pack with Δ ≤ tolerance | accept | ✅ green + 📦 |
| **Pack-conversion alone** — бухгалтер импорт сделал в stems, бот переводит в paq + UoM=31 + expected_qty=stems, без Δ qty | **silent green + 📦 — НЕ orange** | ✅ green + 📦 |
| Pack with Δ > tolerance на pack qty | paper-truth override + activity | 🟠 orange + 📦 |

### §B3 Pack treatment + universal recount preservation

Pack count и stem count = два независимых числа. **НЕ** используем `uom.factor` для конвертации (плавающее число штук в пачке).

#### §B3.0 ⚠️ UNIVERSAL RULE — preserve bookkeeper recount (v21.1, generalized из pack-only v20.3)

**Правило для ВСЕХ lines (pack OR stem):** bookkeeper в Holded ввёл `product_qty` = physical stems он принял на склад (recount). Это **священная информация** — её нужно **сохранить в `x_studio_expected_qty`** перед любой modification, **даже если** pack-conversion не происходит.

```python
# Для КАЖДОЙ line на pedido (stem ИЛИ pack):
old_qty = line.product_qty  # bookkeeper's physical stems count

# 1. Сохрани bookkeeper recount в expected_qty (если ещё не сохранён)
if not line.x_studio_expected_qty or line.x_studio_expected_qty == 0:
    line.write({'x_studio_expected_qty': old_qty})

# 2. Только потом write paper-truth
if is_pack:
    line.write({
        'product_qty': paper.cant,    # paper paquetes
        'uom_id': 31,                  # Paquete
        'price_unit': paper.PVP,
    })
else:
    line.write({
        'product_qty': paper.cant,    # paper stems
        'price_unit': paper.PVP,      # paper price
        # uom остается =1 (Tallo/Units)
    })
```

**Логика:**
- Если `old_qty == paper.cant` (типичный stem case без recount разницы) → `expected_qty == product_qty`, **no harm, no info loss**.
- Если `old_qty != paper.cant` (bookkeeper recounted differently — pack stems vs paquetes ratio, или stem variance) → `expected_qty` хранит recount бухгалтера, `product_qty` хранит paper-truth.
- При finalize action 1217 Phase A2 пишет `stock.move.quantity = expected_qty` (физически на склад).

**Никогда не оставлять `expected_qty = 0` на line с non-zero `product_qty`** — это **потеря информации пересчёта бухгалтера**.

**Pilot 4 incident (2026-05-03)** + **Pilot 9 повтор (2026-05-03)** — subagent оставил expected_qty=0 на multiple stem lines, потеряв bookkeeper recount. Owner: «нельзя терять информацию пересчёта — qty это с бумаги, expected_qty это от бухгалтера, ВСЕГДА переноси». Этого не должно быть.

#### §B3.1 Pack-specific детали (когда `is_pack=True` AND uom_id=1 → 31)

Когда detect `is_pack=True` AND текущий line **uom_id=1 (Tallo)** AND `product_qty > paper.cant` (бухгалтер ввёл stems вместо paquetes — типичная ситуация Holded import):

```python
# 1. ЗАХВАТИ bookkeeper's recount ДО modification
old_qty = line.product_qty  # bookkeeper's physical stems count
old_uom_id = line.uom_id.id  # 1 = Tallo

# 2. Если existing expected_qty уже non-zero — keep, не overwrite
if not line.x_studio_expected_qty or line.x_studio_expected_qty == 0:
    if old_uom_id == 1 and old_qty > paper.cant:
        # Бухгалтер положил stems count, paper.cant=paquetes — переноска
        line.write({'x_studio_expected_qty': old_qty})

# 3. ТОЛЬКО ПОТОМ — pack conversion
line.write({
    'product_qty': paper.cant,    # paper-truth: paquetes
    'uom_id': 31,                  # Paquete
    'price_unit': paper.PVP,       # per paq
    # x_studio_expected_qty уже сохранён в шаге 2
})
```

**Sanity check ratio**:
- `ratio = old_qty / paper.cant` — stems_per_paq
- Realistic ratios: 3-15 stems/paq (например MIMOSA 3.25, MARFULL Madroño 10.6, SKIMMIA 4.8)
- Если `ratio > 50` или `ratio < 1` — **подозрительно**, log в item_comment, leave expected_qty с warning, но НЕ blocker автоматически

**Pilot 4 incident (2026-05-03) объяснение**: subagent **потерял** old `product_qty` (stems count бухгалтера 13/53/20/28/24) при overwrite на `paper.cant` (paquetes 4/5/3/3/5). expected_qty остался 0 → 5 pack BLOCKERs C → pedido не закрылся → owner manual retro-fix. **Этого не должно происходить** — bookkeeper уже сделал recount, его НЕЛЬЗЯ терять.

#### §B3.1 Field write checklist (после §B3.0)

| Field | Value |
|---|---|
| `product_qty` | paper.cant (количество **пачек**) |
| `uom_id` | 31 (Paquete) |
| `price_unit` | paper.PVP per paq |
| `x_studio_expected_qty` | bookkeeper stems count из §B3.0 (НЕ затирать!) |
| Phase A2 (action 1217): | `stock.move.quantity = expected_qty` (точные штуки), `stock.move.x_studio_received_packs = paper.cant` |

Backorder не создаём. Если пришло 17 stems вместо 20 — silent accept.

📦 icon в item_comment line 1: `✅ Пачки <name>. N пачек × ~M stems = total шт на склад.`

**Если `expected_qty` пустое на pack line AND `product_qty == paper.cant` (т.е. recount не было ни в Holded, ни от subagent):** BLOCKER C — без recount нельзя положить точные штуки на склад, activity «нет recount от бухгалтера, нужен ручной пересчёт».

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

**Одна activity на pedido даже при N blockers (v20.2):** не создавать N отдельных activity records (по одной на blocker). Создавать **одну** activity с numbered list внутри note. Owner получает один уведомление с full list to resolve, не N мелких. Если N pack BLOCKERs (как pilot 4: 5 pack без recount) — все 5 в один note с separate `<li>` per blocker.

**При новых cards в pedido — упомянуть в activity note (v20.2):** добавить отдельный bullet «⚠️ Создал N новых cards (84001XXX, 84001YYY) — установи sales price перед promotion в clean catalog» если N > 0.

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

**⚠️ STRICT TEMPLATES (v21.1):** используй точные strings ниже как Слой 1. **НЕ** изобретай альтернативный стиль типа «🤖 ASTER на MIX-карте» или «🤖 Robot edit» — owner видит pilot 8 эти отклонения как style violation. Одинаковый формат на 100% lines bulk → быстрый scan owner'а в pedido list.

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

<p><b>Pricing baseline:</b> закуп 0.55€ → list_price = 1.36€ ex IVA = 1.65€ con IVA (×3 markup ex IVA, формула paper.PVP × 3 / 1.21). `sale_ok=False` пока в карантине. Перед promotion в clean — owner может скорректировать розницу под фактический рынок.</p>

<p><b>Activity:</b> создана на pedido 12491307 — найти товар в магазине + переклеить ценник на новый SKU 84001345 / barcode 84001345 / цена 1.65€ con IVA (см. §A5.3).</p>

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

**Skip line write (only line-level)** если:
- `item_comment` содержит `✅ Verified by Claude AI`
- ИЛИ `x_studio_supplier_sku` уже непустой AND identity на этой line неизменна

**⚠️ КРИТИЧНО — НЕ skip template-side actions** даже если все lines на этом template уже processed:
- supplierinfo upsert per `paper.ref` — **всегда** проверяй и create если нет (идемпотентно по `product_code`)
- attribute_lines (no_variant per §A6.1.bis) — **всегда** проверяй и apply
- description_purchase / codigo_fabrica enrichment — **всегда** проверяй и append если нет

**Restart bug pilot 8 (2026-05-03):** subagent при restart skipped template-side training потому что обнаружил `supplier_sku` на lines (думал «уже processed»). Result: CLEMATIS template оставлен с 1 supplierinfo (208) вместо 3 (208 + 87571 + 45580); LISIANTHUS-MIX без `Nº Flores=5` attribute_line; ASTER-MIX dummy supplierinfo без `product_code`. Carta была **частично** обучена. **Никогда не skip template-side enrichment** — он идемпотентный и обязательный per paper.ref.

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
| 1 | **Digit-loss** (потерял разряд) | `paper.qty > 10 * Odoo.qty` AND identity match strong (`paper.qty / Odoo.qty ≈ 10`) **AND `UD VENTA Paquete` / `FORMATO Paquete` отсутствует** на бумаге (иначе это pack confusion, не digit-loss — §B2) | paper-truth: `product_qty=paper.qty`. Activity «🟡 поправил X→Y, бухгалтер потерял разряд». **Yellow silent**, gate проходит | 🟡 yellow |
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
