<!-- v: 19 | updated: 2026-05-01T02:15Z -->
# Verdnatura Reception — Agent Specification

**Audience:** autonomous reconciliation agent (subagent) или supervisor session, обрабатывающий Verdnatura albaranes 2026 в Espafloria SL.

**Goal:** закрыть один pedido end-to-end (state=purchase + picking done + chatter summary + activity для owner) на основании paper PDF от Verdnatura.

**Lineage:** этот документ — **единственный self-contained источник** для агента-приёмщика. Не требует чтения memory/ или других md-файлов. Базируется на Make.com bot prompt v3.5 (модуль 149), интегрирует SESSION_HANDOVER_2026-04-29.md, накопленные decisions из supervisor pilot 2026-04-30, и audit findings 2026-04-30.

---

## 0. EXECUTIVE SUMMARY (read this first)

Каждый pedido = диалог трёх источников:
- **Paper PDF от Verdnatura** = единственная истина по бумаге (refs, qty, price, IVA, address).
- **Holded import в Odoo** = бухгалтерский ввод. Полезен ровно в двух местах: **(a) выбор product_id** (на какую карту-полку положили), **(b) physical recount qty** (сколько штук бухгалтер физически насчитал — поле `x_studio_expected_qty`). Всё остальное (price, line.name, supplier_sku) — игнор.
- **Algorithm decisions** (этот документ) = бот переписывает что нужно, оставляет что верно.

**Hard rules** (нарушение = bug):
1. Без paper PDF не закрываем — никогда.
2. Никогда не сравниваем Holded цену с paper. Paper price пишется silent на каждой строке.
3. Никаких half-actions. Каждое решение — decisive: **A (change)** / **B (silent accept)** / **C (blocker)**.
4. `author_id=56` на ВСЕХ chatter messages. Через `mcp__odoo__create_record('mail.message', {...})`, **не** `message_post` (та escape'ит HTML).
5. `tracking_disable=True, mail_create_nolog=True, mail_notrack=True` на ВСЕХ writes/buttons под bot.
6. **Wrong match worse than unmatched.** Лучше оставить строку без матча и поднять blocker, чем притянуть неправильный товар. Безопасность идентификации > покрытие.

---

## 1. INPUT / OUTPUT CONTRACT

### 1.1 Inputs
- `pedido_id` (int) — `purchase.order.id` в Odoo
- `paper_pdf_path` — `/Users/andriy/Documents/master-context/master-context/pedido.paper/verdnatura_<docNum>.pdf` (доступен через `mcp__workspace__bash` `pdftotext`)
- `paper_pdf_url` (для attach) — `https://raw.githubusercontent.com/sugestr/Espafloria/main/master-context/pedido.paper/verdnatura_<docNum>.pdf`

### 1.2 Output (success)
- `purchase.order.state` = `'purchase'`
- Все `picking_ids[].state` = `'done'`
- `amount_total` ≈ `paper.Total` (±1€)
- 1× `mail.message` (author=56, через direct create) — summary
- 1× `mail.activity` (если есть `🟠`/`🟡`/`🔴` строки) — review queue
- Все `stock.move.x_studio_review_color` ∈ {2 orange, 3 yellow, 8 dark-blue, 10 green}, либо 0 если qty delta within MINOR_THRESHOLD; **не** 1 red, **не** 4 blue-legacy

### 1.3 Output (blocker)
- `purchase.order.state` = `'draft'` OR picking ещё не done
- `mail.activity` создан с описанием блокера и **NO trigger** action 1217

---

## 2. CONSTANTS (reference IDs)

| Параметр | Value |
|---|---|
| Verdnatura `partner_id` | **42** (внимание: `23` — посторонняя запись, **НЕ использовать**) |
| Claude AI Reconciliation `partner_id` (author) | **56** |
| Andriy `user_id` (activity owner) | **2** |
| `res_model_id` для `purchase.order` (mail.activity) | **819** (verified 2026-04-30, recheck если ломается на новом env) |
| `activity_type_id` (To-Do) | **4** |
| Tax IDs: 10% R goods | **68** |
| Tax IDs: 10% R service | 70 |
| Tax IDs: 21% G goods | 7 |
| Tax IDs: 21% G service | 8 |
| UoM Tallo/Units | **1** |
| UoM Paquete | **31** |
| Carantine category root | **207** (см. §A4) |
| Action server 1217 (`x_studio_claude_finalize` trigger) | **1217** |
| Next free SKU | формула: `MAX(product.template.default_code regex '^84001\d{3}$') + 1` (НЕ hardcode) |
| review_color palette | 1=red, 2=orange, 3=yellow, 4=blue-legacy, 5-7,9=reserved/unused, 8=dark-blue, 10=green |
| MINOR_THRESHOLD (soft-gate stems) | **5** |

---

## 3. CORE PIPELINE

### Step 1 — Parse paper PDF
```bash
pdftotext -layout <paper_pdf_path> -
```
Extract:
- **Dirección de entrega** (адрес доставки — для §A1 warehouse match). Не путать с **Datos fiscales** (всегда «MUNTANER 260» — это регистрация ESPAFLORIA SL, не shipping).
- Per-line: `Ref`, `Cant`, `Concepto`, `Productor`, `PVP`, `IVA` (R/G), `Importe`, плюс под-строка с атрибутами (`COLOR`, `ALTURA`, `MACETA`, **`UD VENTA`** — критический для pack/stem detection, `PESO`, `Nº FLORES` etc.)
- `Subtotal` + IVA cuota + `Total`.

**Validity check**: если pdftotext output не содержит ни одного hit на keywords {`Cant`, `Concepto`, `Total`} → BLOCKER C (битый PDF). Char-count threshold не используем — он ненадёжен.

Sanity на paper: `Σ(Cant × PVP) ≈ Subtotal`; `Subtotal × (1 + IVA) ≈ Total`.

### Step 2 — Warehouse address check (см. §A1)
Сравни paper «Dirección de entrega» с `purchase.order.picking_type_id.warehouse_id`.
- **Match** → продолжаем.
- **Mismatch** → **BLOCKER C**: создаём activity для owner с paper-address и proposed warehouse, **не trigger** 1217. Owner меняет `picking_type_id` либо confirms (тогда retry).

### Step 3 — Attach paper PDF (idempotent)
Search `ir.attachment(res_model='purchase.order', res_id=pedido_id, name='verdnatura_<docNum>.pdf')`. Если 0 → `create_record` метаданных + `set_binary_field(field='datas', source=paper_pdf_url)`.

### Step 4 — Pull Odoo lines
```python
mcp__odoo__search_records('purchase.order.line',
  domain=[['order_id','=',pedido_id]], order='id asc')
```

### Step 5 — Identity match per Odoo line (§A2)
Для каждой Odoo line найти соответствующую paper line. **Strict identity gate** — см. §A2.1: NARROW species/type match (`rose↔rose` OK; `rose↔tulip`, `EUC cinerea↔EUC parvifolia` — НЕ OK). Identity flexibility внутри narrow block — см. §A2.3 (variety/cultivar/color/producer OK).

### Step 6 — Per-line decisions
Для каждой строки **6 решений** (см. §B):
1. **Card** (§B1) — keep / reassign / blocker
2. **Quantity** (§B2) — paper-truth с tolerance
3. **Pack vs stem** (§B3)
4. **Tax** — paper IVA wins
5. **Price** — paper PVP wins **silently** (no markers, no comparison)
6. **Name** — sync `[paper.ref] paper.concepto (paper.productor)`

Write в `purchase.order.line`:
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
    'x_studio_expected_qty': florist_count, # для pack: stems от Holded recount
    'x_studio_item_comment': formatted_comment,  # см. §C3
})
```

### Step 7 — Learn supplierinfo (§A3)
Для каждого `paper.ref` без существующей supplierinfo на этой template — create. **Никогда не учим supplierinfo на placeholder card** (`⛔НОВЫЙ ТОВАР` / FLOR EXOTICA / SANSIVIERIA generic) — закрепление ошибки.

### Step 8 — Pre-flight verification
**Hard checks (failure → blocker, не trigger):**
- Все lines имеют `x_studio_supplier_sku`
- **Все pack lines (uom_id=31) имеют `x_studio_expected_qty > 0`** (иначе action 1217 fallback на `paq_count` = баг, см. §D2)
- Нет 🔴 markers в item_comments
- Нет address mismatch (Step 2)

**Diagnostic warnings (failure → activity для owner, НЕ blocker — totals ≠ source of truth, see L12 v3.5):**
- `amount_total ≈ paper.Total ±1€`
- `Σ(line.product_qty × line.price_unit) ≈ paper.Subtotal ±0.50€` — line-level subtotal check (catches tax mismatch скрывающее line drift, из v1 §6.1)

Если warning — bot всё равно triggers 1217, но активити «ревью totals» для owner.

### Step 9 — Trigger action 1217 (§D contract)
```python
update_record('purchase.order', pedido_id, {'x_studio_claude_finalize': True})
sleep 10
```

### Step 10 — Verify
```python
get_record('purchase.order', pedido_id, ['state', 'picking_ids', 'amount_total', 'x_studio_claude_finalize'])
```
- `state='purchase'` AND `picking.state='done'` → SUCCESS
- `state='draft'` или picking ещё не done → FAIL (см. §E retry / blocker)

### Step 11 — Post summary message (§C1 format)
**Direct create** (НЕ `message_post`) чтобы HTML не escape'нулся:
```python
mcp__odoo__create_record('mail.message', {
    'model': 'purchase.order',
    'res_id': pedido_id,
    'subject': f'AI Reconciliation — {paper.docNum}',
    'author_id': 56,
    'subtype_id': 1,
    'message_type': 'comment',
    'body': html_summary,  # формат §C1
})
```

### Step 12 — Post activity (если есть 🟠/🟡/🔴 строки)
```python
mcp__odoo__create_record('mail.activity', {
    'res_model_id': 819,
    'res_id': pedido_id,
    'activity_type_id': 4,
    'user_id': 2,
    'summary': f'🟠 Pedido {paper.docNum}: K крупных правок на ревью',
    'date_deadline': today_str,
    'note': html_note,  # формат §C2
})
```

---

## §A — REFERENCE TABLES

### §A1 Warehouse mapping (Espafloria 3 active магазина + 1 archived)
| Paper «Dirección de entrega» содержит | Warehouse | picking_type_id |
|---|---|---|
| **Olimpic** / **Castelldefels** | Blau (id 4) | 28 (`BLA/IN/`) |
| **Augusta** / **Augusta 109 (bis)** | Plaza (id 2) | 10 (`PLA/IN/`) |
| **Diagonal** / **Macinista** / **Sant Martí** | Gloria (id 3) | 19 (`GLO/IN/`) |
| **Muntaner 260** | Temporal (id 5) **+ scrap planned** | 37 (`TMP/IN/`) — закрытый магазин, на склад принимаем, потом списываем что не продалось |
| Прочее / пусто | flag → owner | — |

Mismatch на Step 2 → BLOCKER C, не trigger.

### §A2 Identity match — strict gate + flexibility

**Core principle:** **wrong match worse than unmatched** (см. §0 hard rule #6). Никогда не притягивай матч ради покрытия. Лучше unmatched paper line + activity для ревью, чем wrong-product substitution.

#### §A2.1 Strict identity gate
Match только когда **specific narrow species/type** plausibly the same.

**Допустимо** (примеры):
- rose ↔ rose
- chrysanthemum ↔ chrysanthemum
- freesia ↔ freesia
- eucalyptus cinerea ↔ eucalyptus cinerea
- bamboo ↔ bamboo
- photinia ↔ photinia
- bouquet ↔ bouquet **только** при strong direct evidence для конкретной строки

**Отклоняем** (примеры):
- rose ↔ tulip (разные species)
- photinia ↔ madroño (разные species)
- eucalyptus cinerea ↔ eucalyptus parvifolia (разные species, одна семья — НЕ match, НЕ MIX)
- цветок ↔ растение горшечное
- ваза стеклянная ↔ роза (категория ≠ предмет)

#### §A2.2 Broad tokens — НЕ identity
Generic tokens сами по себе **не establish identity**:
`bouquet`, `bqt`, `mix`, `tropical`, `assorted`, `decorative`, `floral`, `greenery`

Если у двух line только эти токены общие — **не match**, идти в unmatched. Не использовать blocker C как dump bucket для таких пар.

#### §A2.3 Identity flexibility (внутри narrow block)
Когда specific identity passes gate, эти различия **НЕ ломают** match:
- variety / cultivar / sort
- color / shade
- size / height / maceta
- producer
- style wording (legacy / awkward Odoo naming)

**Примеры допустимой flexibility:**
- freesia soleil ↔ freesia rosario
- rose Mondial ↔ rose Pretty Pillow
- bamboo прямой ↔ bamboo крученный
- photinia red robin (paper) ↔ generic «PHOTINIA» в Odoo (если supplierinfo подтверждает)

#### §A2.4 Evidence priority (от сильного к слабому)
1. **Learned codigo** — `supplierinfo(partner=42, product_code=paper.ref)` указывает на template совпадающий с Odoo line.product_id. Сильнейшее.
2. **Operator hit** — `x_studio_operator_hit == paper.ref`. Сильное direct указание для текущего pedido.
3. **Existing assignment** — бухгалтер's `product_id` если identity match. TRUST если species OK.
4. **Fabrication code** — `paper.ref` substring в `product.template.x_studio_codigo_fabrica`.
5. **Default code** — `product.template.default_code == paper.ref`.
6. **Semantic similarity** — Levenshtein / fuzzy на concepto. Last resort tie-breaker.

#### §A2.5 Match-method discipline
`match_method` label = всегда **сильнейшее actual evidence**, не default `semantic`. Precedence:
- `supplierinfo_code` — ТОЛЬКО если paper.ref exact match с `supplierinfo.product_code`
- `fabrication_code` — ТОЛЬКО если paper.ref substring в `x_studio_codigo_fabrica`
- `default_code` — ТОЛЬКО если paper.ref == `default_code`
- `semantic` — ТОЛЬКО когда нет ни одного code hit + match по species/concepto

Никогда не label `semantic` если есть code hit. Сначала просканируй все code-поля.

#### §A2.6 Confidence bands
- **0.92-0.98** — direct learned vendor code, no hard contradiction
- **0.88-0.95** — direct operator command, no hard contradiction
- **0.84-0.91** — fabrication / default code hit или very strong specific identity. **HIGH threshold** (используется в §B1).
- **0.74-0.83** — clean specific identity match без direct code
- **0.62-0.73** — plausible weaker assigned-card / semantic
- **<0.62** — обычно unmatched, иначе blocker C

`HIGH` в §B1 = ≥0.84. **Не downgrade** learned vendor code или operator hit потому что Odoo card name ugly/legacy/awkward.

#### §A2.7 Learned vendor code rule
Exact match paper.ref ↔ `supplierinfo.product_code`:
- **Прибавляет** уверенность, не уменьшает
- НЕ downgrade если внутреннее имя Odoo broad / legacy / awkward
- Override **только** при hard species contradiction

Если `data[]` (supplierinfo list для template) пуст — это «not learned yet», НЕ «invalid» / «no candidate». Учим через §A3.

#### §A2.8 Operator command rule
`x_studio_operator_hit == paper.ref` — direct manual instruction для текущего pedido.
- Слабее learned vendor code, **сильнее** generic semantic / line order / vague resemblance
- НЕ downgrade на ugly internal naming
- Override только при hard contradiction или сильнейший learned-code на другом кандидате

#### §A2.9 Preserve existing product cards
pedido уже содержит product-card работу бухгалтера. Сохраняем assignment когда:
- specific identity plausibly the same
- нет clearly stronger competing candidate

Reject existing card **только** когда:
- identity hard-different (species conflict)
- другой candidate явно лучше на сильнейшем evidence

НЕ reject existing card **только** потому что:
- qty differs / pack-vs-unit / tax differs / price differs / wording imperfect / internal name broad

**Quantitative threshold для wrong-card preservation** (из v1 §4.1):
- Если existing card имеет **≥1 supplierinfo с близкой ценой** (`±50%` от paper.PVP) → keep card (consolidate OK, бухгалтер положил на разумную полку даже если concepto немного отличается).
- Если price diff **>×1.5** (50% deviation в любую сторону) И identity не подтверждён сильным evidence → **Variant A split** (создать distinct card).

#### §A2.10 Blocker C — НЕ dump bucket
Blocker C ставим **только** когда есть конкретный residual identity risk. Не использовать как «куда деть всё что непонятно». Для чистых unmatched paper line — unmatched + activity для ревью.

#### §A2.11 Matching algorithms (HOW-to)
Когда identity gate (§A2.1) пройден, выбор kandidate paper↔Odoo line идёт по этим алгоритмам в порядке убывания надёжности:

1. **Positional 1:1** — paper line[i] ↔ Odoo line[i], если N=M (количество строк совпадает) и порядок не нарушен. Самый дешёвый и обычно правильный для свежих Holded import'ов.
2. **Match по qty (N=M, порядок сбит)** — если N=M но positional не работает (например бухгалтер пересортировал), переставь Odoo строки чтобы paper.cant матчила line.product_qty. Tie-breaker — concepto similarity.
3. **Match по концепту fuzzy** — если N≠M: substring / first-word / Levenshtein на `concepto` ↔ `product.template.name OR default_code`. Только если identity gate проходит.
4. **Multi-paper → 1 Odoo MIX consolidate** — если несколько paper строк (одного species, например 4× CL разных сортов) матчат одну Odoo MIX-карту: суммируй `Σ paper.cant` и сверяй с `line.product_qty`. Если совпадает или close — match подтверждён, MIX-карта корректна (см. §B1a).

Если ни один алгоритм не даёт надёжный match для paper line → unmatched + activity (НЕ blocker C, см. §A2.10).

### §A3 supplierinfo create + product.template enrichment

**Цель:** карточка товара после reconcile pedido = обученная для будущих pedidos. Codigo + цена + бумажная дата + имя как у поставщика + атрибуты в описании.

#### §A3.1 Когда учим — по blocker-статусу, НЕ по card type

**Простое правило:** учим **все non-blocker строки**. Не учим **blocker C** строки.

- ✅ **Учим** если строка обработана decisively (KEEP / Variant A reassign / new card created / accept paper-truth) — то есть identity clearly resolved. **Не важно** какая это card — 🚫 quarantine / placeholder / normal — учим всё. Логика: paper.ref ↔ template связку накапливаем для всех successfully-обработанных строк, не теряем data.
- ❌ **НЕ учим** если строка = **blocker C** (бот не уверен в идентификации, или предложил создать новую но не уверен, или не решился заменить card). Это потенциально wrong assignment — закрепить = ошибка.
- ✅ **Второй проход** — после того как owner резолвит blocker (apply его решение через UI или MCP), бот **учит supplierinfo** на финальной карточке (та что owner подтвердил). Это происходит при retrigger 1217 или manual sweep.

Это значит на pilot 12421571 (где было 2 blocker red) — учим **16 из 18** non-blocker lines прямо сейчас. Оставшиеся 2 (F Arroz Pink + F Cera Eden) — учим после ответа owner.

#### §A3.2 supplierinfo upsert (создаём ИЛИ обновляем existing empty)

**До create — search:** `product.supplierinfo([['partner_id','=',42],['product_tmpl_id','=',tmpl_id],['product_code','in',[False, '']]])`. Если найдена пустая default — **обновляем её** вместо создания дубликата. Иначе — create new.

| Field | Value |
|---|---|
| `partner_id` | 42 |
| `product_tmpl_id` | template-id of card бот выбрал |
| `product_code` | paper.ref (**главное!** без этого карточка не обучена) |
| `product_name` | `<concepto> (<productor>) <key_attributes>` — например `Acacia (Mimosa Bola) >500 gr` |
| `price` | paper.PVP (per uom_id supplierinfo'а) |
| `min_qty` | 1 |
| `date_start` | paper.FECHA (дата бумаги) |
| **`uom_id`** | **31 (Paquete) для pack товаров (line.uom_id=31), 1 (Tallo) для stem.** Без этого поля Odoo дефолт берёт template.uom_id и цена интерпретируется неправильно. |

#### §A3.3 product.template enrichment (одновременно с supplierinfo)
Записываем на `product.template`:
| Field | Когда писать | Value |
|---|---|---|
| `description_purchase` | Всегда если empty | `Auto-enriched from paper {ref} {date}: {concepto} ({productor}). Атрибуты: {ALTURA/COLOR/MACETA/PESO/Nº FLORES — те что есть в paper sub-line}` |
| `x_studio_codigo_fabrica` | Если empty — записать `paper.ref`. Если non-empty — append через `;` если ref не уже там | sequence Verdnatura refs обслуженных этой картой |

**Chatter log на template (mandatory):** при ЛЮБОМ изменении полей template (description_purchase, codigo_fabrica, name, supplierinfo create/update — любое не учебное действие на карточке) — постим chatter message на template:
```python
mcp__odoo__create_record('mail.message', {
    'model': 'product.template',
    'res_id': tmpl_id,
    'author_id': 56,
    'subtype_id': 1,
    'message_type': 'comment',
    'body': f'<p>🤖 Robot edit (pedido {docNum}): {что изменено}</p><p>From paper {ref} {date}: {concepto}</p>',
})
```
Это нужно для audit trail — owner должен видеть все автоматические правки в карточке.

#### §A3.4 Card rename (опционально, через activity)
Если card name явно generic (например `🚫 RSR ROSA RAMI - MIX` — слово MIX без конкретики):
- НЕ переименовывать автоматически
- Добавить **🟠 activity для owner** с предложением: «Переименовать `[название_сейчас]` → `[предложение based on paper attributes]`? Например `🚫 ROSA Mondial+Pretty Pillow MIX`»
- Owner approves → manual rename через UI

#### §A3.5 Multi-ref на одну card (MIX consolidate)
Если N paper.ref'ов матчат одну Odoo MIX-card (per §B1a) — создаём **N supplierinfo записей** на тот же `product_tmpl_id` с разными `product_code`. Это нормально и желательно — карточка становится обучена N codigo одновременно.

### §A4 Carantine categories (для new card placement)
- 207 — root «⛔ Карантин Holded»
- 210 — EMBALAJE (упаковка)
- 211 — ENTREGA
- 212 — FLORES CORTADAS (срезка)
- 213 — PLANTAS EN MACETAS (горшечные)
- 214-279 — спец. подразделы (см. live `product.category` на espafloriasl.odoo.com при необходимости)
- 280 — DECORACION (вазы, декор)
- 281 — PRODUCTO DESCONOCIDO

### §A5 Card create (§B1A Variant A когда нужна new card)
| Field | Value |
|---|---|
| `name` | `🚧🟠 <paper.concepto>` |
| `default_code` | next_sku по формуле §2 (sequential 84001NNN, строго после max existing) |
| `barcode` | `default_code` если `categ_id ∈ {212 FLORES CORTADAS}`; manufacturer barcode допустим если `categ_id ∈ {213 PLANTAS EN MACETAS, 280 DECORACION, 210 EMBALAJE}` |
| `categ_id` | по типу товара (§A4) |
| `type` | `'product'` |
| `list_price` | 0 |
| `standard_price` | paper.PVP |
| `uom_id` | 1 (Tallo) или 31 (Paquete) по UD VENTA |
| `uom_po_id` | то же |
| `purchase_method` | `'receive'` |
| `description_purchase` | `Auto-created by Claude AI <date> from paper {ref} {concepto} {productor}` |
| `image_1920` | `set_binary_field(source='https://cdn.verdnatura.es/image/catalog/1600x900/<paper.ref>')`, 404 → leave empty |

---

## §B — DECISION TREES

**Decisive rule (везде в §B):** A (change) / B (silent accept) / C (blocker) — никаких половинных решений. Если бот не уверен — blocker C, не «orange и продолжим».

### §B1 Card decision (per line)
```
match = identity_match_result(paper, odoo_line)

if match.confidence ≥ HIGH (≥0.84) and match.product_id == odoo_line.product_id:
    → KEEP product_id silent. No marker.

elif match.confidence ≥ HIGH and alternative_card exists in Odoo:
    → VARIANT A: reassign product_id to match. 🟠 orange.
    Item_comment: "🟠 Бухгалтер положил на X, в бумаге Y. Перенёс на Y."
    [Лог] old_card=X new_card=Y reason=identity_mismatch

elif match.confidence < HIGH (placeholder card, no clear alternative):
    → VARIANT C BLOCKER. 🔴 red.
    Не trigger 1217. Activity для owner: "Хочу заменить placeholder X, но
    не нашёл подходящую card. Owner: создать new или confirm placeholder OK".

else if MIX preferred (§B1a):
    → KEEP MIX silent. No marker. (бухгалтер сделал правильно)

else if Premium/distinct (§B1b):
    → VARIANT A: split off distinct card. 🟠 orange.
```

#### §B1a MIX-card PREFERRED (group decisively)
MIX OK silent (без оранжа) когда **все три** условия:
- **Same species, varying cultivar/variety/color/producer** — все товары один species (CL разных сортов = Dianthus caryophyllus разных cultivar; PAN разных цветов = один Pandanus species разных colors; PHAL разных variants — Phalaenopsis cultivars). **НЕ** разные species (EUC cinerea ≠ EUC parvifolia — НЕ MIX).
- **Price ratio** ≤ 1.5: `max(prices_on_card) / min(prices_on_card)`.
- **Sales usage** — продаются клиенту как один SKU (флорист берёт любой из карты под композицию).

Если все три — **silent green**, MIX-карту можно/нужно переименовать на инклюзивное имя (например `BAMBU прямой и крученный`, `Salix tinted family`). **Не используй слово «MIX»** в name если есть конкретное описание форм.

На MIX-карту учим N разных Verdnatura ref через supplierinfo (§A3) — каждый ref отдельной supplierinfo записью на тот же template.

#### §B1b Distinct cards (split — Variant A)
Distinct card обязательна когда **хотя бы одно**:
- Premium variety (цена ×1.5+ от средней по семье) с visible identity diff (Monstera Variegata Thai vs Adansonii).
- Продаются как separate SKU (клиент выбирает по сорту/цвету).
- Business-критично для аналитики маржи.

Action: `Variant A` — найти existing distinct card OR create new (§A5) + reassign + 🟠 orange.

#### §B1c Search before create (mandatory)
Перед `create new card`:
1. Search существующие robo-cards (icons `🤖🚧` / `🚧🟠` / `🚧` / `🤖`, ranges 84001152+, 84009*).
2. Search чистая зона: исключающее `🚫` префикс, по `name ilike paper.concepto`.
3. Если найдена точная identity match → reassign (Variant A с existing).
4. Только если нет нигде → create new (§A5).

### §B2 Quantity decision (per line)

#### Detect pack/stem
```python
is_pack = (
    'UD VENTA Paquete' in paper.attributes
    OR known_pack_product(concepto)  # Mimosa, Skimmia, EUC, Lentisco, Acacia, Ranunculus pequeño, etc.
    OR (existing supplierinfo for this ref имеет uom Paquete)
    OR (paper.qty vs Odoo.qty имеют ratio ≥3 без явных stem signals)
)
```

#### Tolerance & MAJOR_THRESHOLD
```python
if is_pack:
    tolerance = min(max(15, int(paper.qty * 0.30)), paper.qty)  # cap by paper qty
else:  # stem
    tolerance = max(4, int(paper.qty * 0.05))  # progressive

# Big-delta cutoff (для решения yellow vs blocker red)
MAJOR_THRESHOLD = max(15, int(paper.qty * 0.30))  # 15 stems OR 30% paper
```

#### Decision matrix (stem товары)
| Сравнение | Action | review_color |
|---|---|---|
| paper.qty == Odoo.qty (или Δ ≤ tolerance) | accept paper qty | ✅ green (10) |
| Odoo > paper, Δ ≤ MINOR_THRESHOLD (≤5) | accept Odoo silent (Verdnatura прислал чуть больше — щедрость) | ✅ green |
| Odoo > paper, MINOR < Δ ≤ MAJOR_THRESHOLD | **paper-truth override** + activity «бухгалтер пересчитал вверх, поправлено по бумаге» | 🟠 orange (2) |
| Odoo > paper, Δ > MAJOR_THRESHOLD | **BLOCKER C** — extreme over-recount, расследовать | 🔴 red (1) |
| Odoo < paper, Δ ≤ tolerance | accept Odoo silent (бухгалтер мелко недосчитал) | ✅ green |
| Odoo < paper, tolerance < Δ ≤ MAJOR_THRESHOLD | **paper-truth override** + activity «бумага говорит +N, физически проверь — возможна недопоставка Verdnatura, scrap if needed» | 🟡 yellow (3) |
| Odoo < paper, Δ > MAJOR_THRESHOLD | **BLOCKER C** — extreme недостача, recourse Verdnatura или опечатка ввода | 🔴 red (1) |
| ratio ≈ ×2 (любая сторона) | **paper-truth override** + activity «×2 наблюдение, известный баг двойного импорта Holded→Odoo» | 🟡 yellow (3) |

#### Decision matrix (pack товары)
| Сравнение | Action | review_color |
|---|---|---|
| Pack pure paper-match (paper.cant == Odoo.paq) + UoM=Paquete + expected_qty filled | accept | ✅ green + 📦 |
| Pack with Δ ≤ tolerance (paq qty match within 30%) | accept | ✅ green + 📦 |
| **Pack-conversion alone** — бухгалтер импорт сделал в stems-формате, бот переводит в paq + UoM=31 + expected_qty=stems, без Δ qty | **silent green + 📦 — НЕ orange** | ✅ green |
| Pack with Δ > tolerance на pack qty (paper 5 paq, Odoo 8 paq — substantial mismatch) | paper-truth override + activity | 🟠 orange (2) |

**Pack-conversion alone — НЕ orange.** 📦 marker в item_comment, color остаётся green по qty.

### §B3 Pack treatment (когда `is_pack=True`)

**Источник штук на склад — только `expected_qty` (Holded recount от бухгалтера).** Бот сам **не пересчитывает** через формулу «paq × stems_per_paq» — нет такого хранилища. Если бухгалтер не насчитал — blocker.

| Field | Value |
|---|---|
| `product_qty` | paper.cant (количество **пачек**) |
| `uom_id` | 31 (Paquete) |
| `price_unit` | paper.PVP per paq |
| `x_studio_expected_qty` | florist physical stems (Holded recount) |
| Phase A2 (action 1217) пишет: | `stock.move.quantity = expected_qty` (точные штуки), `stock.move.x_studio_received_packs = paper.cant` |

**Fallback chain для `stock.move.quantity` на pack line:**
1. **Primary** — `x_studio_expected_qty` (Holded recount). Всегда первое.
2. **Blocker C** — если `expected_qty` пустое OR явно неадекватно (например 1 stem на 5 паков мимозы). Не закрываем pedido. Activity для owner: «нет recount от бухгалтера, нужен ручной пересчёт».

📦 icon в `item_comment` line 1: `✅ Пачки <name>. N пачек × ~M stems = total шт на склад.`

**Zero-backorder gate (v17 механизм):**
Корневая проблема: Odoo жёстко считает `move.product_uom_qty * uom.factor = expected stems`. Если `uom_id=31 (Paquete, factor=10)`, и `product_uom_qty=4 paq`, то Odoo ожидает 40 stems. Если Phase A2 пишет `quantity=18` (реальные штуки), Odoo видит «получено 18 < ожидалось 40» → создаёт backorder.

**Fix:** Phase A2 для pack lines пишет **ОБА значения синхронно**:
```python
move.write({
    'quantity': expected_qty,                      # точные штуки на склад
    'product_uom_qty': expected_qty / uom.factor,  # дробные паки чтобы Odoo не считал по 1:10
    'x_studio_received_packs': paper.cant,
})
```
Тогда Odoo видит «ожидалось paq×factor=stems = принято stems → 0 backorder» ✅.

**Альтернатива** (если дробные паки ломают что-то другое): переключить `move.product_uom_id = 1 (Tallo)` + `move.product_uom_qty = expected_qty` (move в штуках, pedido line остаётся в паках). Тестируется на pilot — фиксируется работающий вариант в action 1217 v7.8.

**Если backorder всё-таки возник** (gate failure):
- ❌ **НЕ закрывать direct state-write** на picking — это violation invariant G8 (state machines через штатный action).
- ✅ **Оставить backorder + 🟠 activity для owner**: «backorder #X создался despite zero-backorder gate — нужен manual cancel или ручной разбор. v7.8 backlog: auto-cancel через `picking.action_cancel()`».

### §B4 Tax decision
- paper IVA = R 10% → `tax_ids = [[6, 0, [68]]]` (goods) или 70 (service)
- paper IVA = G 21% → `tax_ids = [[6, 0, [7]]]` (goods) или 8 (service)
- Если Odoo line имеет другой / пустой tax → переписать.

### §B5 Price decision — **silent paper-truth override**
Всегда: `price_unit = paper.PVP`. **Никаких markers** в item_comment, **никаких сравнений** с Holded.
- Holded цена не имеет смысла (часто 0 / средняя случайная).
- Округление до 5 центов = подгонка, silent overwrite.
- Если paper.PVP = 0 (очень редкий случай) → flag для owner, **не write** 0.

### §B6 Name sync
`name = f'[{paper.ref}] {paper.concepto} ({paper.productor})'`. Всегда переписываем если:
- ref в текущем name `[xxx]` ≠ paper.ref
- name пустой / generic placeholder
- card был reassigned

Sync — НЕ отдельный orange trigger. Считается частью пакета изменений по строке.

### §B7 Color assignment matrix (по итогу 6 решений per line)

Бот выставляет `stock.move.x_studio_review_color` явно после всех решений. Семантика:

| Цвет | ID | Когда |
|---|---|---|
| 🟢 green | **10** | Perfect OK: paper.qty матчит Odoo.qty (точно или within MINOR, в т.ч. accept-Holded ≤MINOR positive delta), identity confirmed, Phase A была корректна заранее. Включая pack-conversion within tolerance (📦). |
| 🤖 dark blue | **8** | **Robot clean fill** — бот заполнил пустую/generic Phase A (line пришла из Holded import без supplier_sku или без expected_qty), positional match + learned codigo подтвердил identity, без content-changing правок. Бот сделал работу, бухгалтер — нет. |
| 🟡 yellow | **3** | Diagnostic flag: Δ>tolerance с paper-truth override на stem, или ×2 ratio paper-truth observation (двойной импорт). Gate проходит, owner информирован активити. |
| 🟠 orange | **2** | **Substantial auto-fix**: reassign card / split MIX / create new card / pack-conversion **с** Δ>tolerance на pack qty. Gate проходит, активити для ревью. |
| 🔵 blue legacy | **4** | «Нужен ввод бухгалтера/флориста» — бот не имеет данных для решения (например `expected_qty` пустое на pack line, identity confidence <HIGH). Gate **блокирует** (см. BLOCK_COLORS §D3). |
| 🔴 red | **1** | Hard species conflict / расхождение с бухгалтером по qty (paper > Odoo с Δ>MINOR negative) / blocker C. Gate **блокирует**. Owner decode required. |

**Decision logic (псевдокод для агента — first match wins, проверяем сверху вниз):**
```python
# 1. Hard blockers
if identity hard-conflict OR (paper > Odoo with Δ>MINOR negative) OR explicit blocker C:
    color = 1  # red

elif line needs florist input (pack без expected_qty, identity confidence <HIGH):
    color = 4  # blue legacy

# 2. Substantial structural fixes
elif (card reassigned) OR (new card created) OR (split MIX) OR (pack-conversion with Δ>tolerance on pack qty):
    color = 2  # orange

# 3. Diagnostic flags (gate passes, owner informed)
elif (Δ>tolerance с paper-truth override на stem) OR (×2 ratio paper-truth applied):
    color = 3  # yellow

# 4. Clean cases — distinguish robot-fill vs paper-match-preserved
elif (Phase A on Odoo line was empty/generic before bot's write — нет supplier_sku OR нет expected_qty originally — AND bot confirmed identity via supplierinfo):
    color = 8  # dark blue (robot clean fill)

# 5. Default green — paper-match preserved
else:
    color = 10  # green (включая accept-Holded ≤MINOR positive delta, pack-conversion within tolerance)
```

**Important:** silent paper-truth `price_unit = paper.PVP` write (per §B5) **не считается** «правкой» для color logic — это no-op (cosmetic alignment). Только content-changing правки (identity reassign, qty override beyond tolerance, new card creation) триггерят non-green color.

Полная prod-логика action 1146 (`review_status_automation`) — в `master-context/review_status_automation.py` (contract mirror, см. §H runtime checklist). Agent сам пишет color на `stock.move.x_studio_review_color`; action 1146 переключает текстовый `review_status` по триггерам.

---

## §C — TEXT FORMAT (всегда plain language first)

**Принцип:** owner на мобильном должен понять суть за 5 секунд из первой строки. Детали и техника — внизу для тех кто хочет дойти до уровня. **Никаких ref/tmpl_id/uom_id в первой строке.**

### §C1 Summary message (mail.message body, HTML)

**Принцип первой секции:** рассказать **историю** простым языком, без технических терминов. Owner должен понять «что случилось» за 5 секунд. Цифры и detail — ниже, не в opening.

**Шаблон opening (естественный язык):**
```
Verdnatura прислала <N> строк товара на <X>€ для магазина <name> (например Olimpic, Plaza, Gloria).
Бухгалтер импортировал <M> строк в Odoo (<diff комментарий: «правильно» / «на K больше» / «K строк потерял»).
Бот: <1-2 предложения о главных правках простым языком — например «4 пакетных товара обработал по правилу пачки/штуки, 3 лишних обнулил, на 1 строке исправил недосчёт по бумаге, 1 товар добавил вручную»>.
```

**Что НЕ писать в opening:**
- ❌ `pack-stress-test`, `Phase A2`, `UoM=31`, `tax_ids`, `picking BLA/IN/00064`
- ❌ Цифры через дефис типа `recount=stems×factor`
- ❌ Английские термины кроме общеупотребительных (бумага, бухгалтер, склад, recount)

**Что писать:**
- ✅ Имена магазинов (Olimpic, Plaza, Gloria, Augusta, Diagonal)
- ✅ Простые формулировки («пакетный товар», «лишних обнулил», «потерял строку», «недосчитал»)
- ✅ Сумма в €, имя поставщика, дата если важна

```html
<p><b>🤖 Что случилось в принципе:</b></p>
<p><Шаблон выше — 2-3 предложения простым языком, без жаргона.></p>

<p><b>Что в результате:</b></p>
<ul>
  <li>K крупных правок — описание паттерна</li>
  <li>L pack-only — clean (зелёные с 📦)</li>
  <li>M clean — без правок</li>
  <li>Сумма pedido X€ ↔ бумага X€ ✅</li>
  <li>Picking <code> done на warehouse Y ✅</li>
  <li>N supplierinfo обучены</li>
</ul>

<p><b>🟠 K крупных (нужен ревью):</b></p>
<ol>
  <li><b>[Ref] Concepto</b> — что было / что стало plain language</li>
  ...
</ol>

<p><b>✅ Чистых N:</b></p>
<ul>
  <li>📦 Ref Concepto (если pack)</li>
  <li>Ref Concepto (если stem)</li>
  ...
</ul>

<p>[Лог] session=&lt;short_id&gt; algo=&lt;version_from_§J&gt; closed=&lt;UTC ISO8601&gt;</p>
```

### §C2 Activity note (mail.activity note, HTML)
```html
<p><b>Pedido <docNum> — простыми словами:</b></p>
<p>1-2 предложения почему оранжевые есть.</p>
<ol>
  <li><b>[Ref] Concepto</b> — что было / что стало.</li>
  ...
</ol>
<p>Зелёных N — clean paper-match, ревью не требуется.</p>
```

### §C3 Item_comment (per line, plain text)

**📦 emoji prefix mandatory для pack lines** (любого статуса — clean / orange / red). Owner должен сразу видеть в pedido list что строка пакетная даже если статус не оранжевый.

```
Line 1: ОБЗОР simple language. Один из:
  - "✅ Paper match: <concepto> <qty>×<price>€"  (stem clean)
  - "✅📦 Пачки <name>. <paq>×~<stems_per_paq>=<total> шт на склад."  (pack clean)
  - "🟠 Бухгалтер X, бумага Y. Поправил."  (stem substantial fix)
  - "🟠📦 Бухгалтер X пачек, бумага Y пачек. Поправил."  (pack with Δ>tolerance)
  - "🟡 Paper-truth +N stems. Owner: физически проверь."  (paper>Odoo moderate)
  - "🟡 ×2 наблюдение, paper-truth применён. Возможный баг двойного импорта."
  - "🔴 BLOCKER: <причина>. Owner: <вопрос>."  (red)
  - "🔴📦 BLOCKER: <причина>. Pack товар."  (pack red)

Line 2: Бумага factual.
  "Бумага: <qty> <pак|шт> × <price>€ = <importe>€ (Verdnatura ref X, IVA Y%, ALTURA Z)."

Line 3: [Лог] machine-readable.
  "[Лог] supplier_sku=X expected_qty=N price=Y paper_match=<reason> [card=...] [old_card=...]"
```

---

## §D — ACTION 1217 v7.7 CONTRACT (server-side)

Mirrored в `master-context/reconcile_finalize_action.py`. Триггер: write `x_studio_claude_finalize=True` на `purchase.order`.

### §D1 Branches (selected by current state)
| Branch | Trigger condition | Что делает |
|---|---|---|
| **ROLLBACK** | `note` substring `ROLLBACK_HOLDED_API` | reverse done picking → button_draft → clear Phase A на лайнах: `price_unit=0`, `x_studio_supplier_sku=False`, `x_studio_supplier_product_name=False`, `x_studio_item_comment=False` (4 поля; `x_studio_expected_qty` пока **НЕ** чистится — gap для v7.8 backlog) |
| **RETRY** | `state='purchase'` AND есть picking в любом state кроме `done`/`cancel` (т.е. `draft`/`waiting`/`confirmed`/`assigned`) | soft-gate (≤MINOR_THRESHOLD=5) → button_validate(skip_backorder=True) |
| **DRAFT** | `state='draft'` | pre-flight (amount>0, all lines have supplier_sku) → button_confirm → Phase A2 → soft-gate → button_validate |

### §D2 DRAFT branch detail
1. `pedido.with_context(NO_TRACK).button_confirm()` → `state=purchase`, picking создан.
2. **Phase A2** — пишем quantity на каждый stock.move:
   - Pack lines (uom_id=31): `quantity = expected_qty` (stems), `x_studio_received_packs = product_qty` (paq).
   - Stem lines: `quantity = expected_qty || product_qty`.
   - Все writes под `tracking_disable=True, mail_create_nolog=True, mail_notrack=True`.

   **⚠ Pre-flight invariant для pack lines:** agent **обязан** залить `x_studio_expected_qty > 0` до trigger 1217. Иначе код v7.7:122 fallback'ит на `paq_count` (число пачек, НЕ стеблей) — это баг. Проверка в Step 8 pre-flight.

3. **Final gate by color** (§D3 logic).
4. `picking.with_context(skip_backorder=True, NO_TRACK).button_validate()` → `state=done`.

### §D3 Gate logic (по color, не по text)
```python
PASS_COLORS = (10, 8, 3, 2)   # green, dark-blue, yellow, orange
BLOCK_COLORS = (1, 4)          # red, blue legacy «нужен ввод»

color = move.x_studio_review_color or 0
if color in PASS_COLORS: continue
elif color in BLOCK_COLORS: flag stop
else (color == 0): fallback по qty delta vs MINOR_THRESHOLD
```
Status текст пишется только при delta > 0 (без `-0` bug v5/v6).

### §D4 What action 1217 does NOT do (agent must do post-trigger)
- ❌ Summary message — agent создаёт через `mcp__odoo__create_record('mail.message', {...})` (HTML correct рендер).
- ❌ Activity create — agent делает через `mcp__odoo__create_record('mail.activity', {...})` с `res_model_id=819`.

### §D5 Constraints внутри action 1217 (safe_eval)
- ❌ `obj.field = value` (use `write({...})`)
- ❌ `type(e).__name__`, `hasattr(...)` (use `'field' in record._fields`)
- ❌ `import` statements
- ✅ `env['model'].create/search/browse`
- ✅ `with_context(...)`, `record.write(...)`

---

## §E — RETRY / IDEMPOTENCY

### §E1 Skip правила (для re-run)
**Skip pedido целиком** если:
- `state='cancel'` (отменён)
- `state='purchase'` AND все picking_ids в `done`

**Не skip** если:
- `state='draft'` (продолжаем работу)
- `state='purchase'` AND picking в любом не-done/не-cancel (RETRY case — action 1217 RETRY branch)

**Skip pedido (mid-flight)** если:
- `x_studio_claude_finalize=True` уже стоит (action 1217 в работе) — wait

**Skip line** если:
- `item_comment` содержит `✅ Verified by Claude AI` (уже сверена)

### §E2 Re-run на draft / RETRY pedido
Продолжаем с места где остановился. Если algorithm refined после прошлого pass — пытаемся разрешить старые красные с новыми правилами (Variant A reassign / Variant B accept / Variant C blocker).

---

## §F — KNOWN OPEN WORK (current gaps)

### §F1 Pedido-level visual status (decision 2026-04-30)

**Owner verbatim:** «мне очень важно сразу легко понимать глядя на pedido или список pedido — закрыто всё зелёное / закрытое есть жёлтое-оранжевое / не закрыто (на склад не ушло, надо решать какие-то проблемы лично)».

#### §F1.1 Три уровня pedido-level status
| Бейдж | Условие | Что значит |
|---|---|---|
| 🟢 **Closed clean** | `state='purchase'` AND все `picking.state == 'done'` AND все `stock.move.x_studio_review_color in (10, 8)` (green/dark blue) | Закрыт, всё чисто, owner может игнорировать |
| 🟡 **Closed needs review** | `state='purchase'` AND все `picking.state == 'done'` AND **хотя бы один** `stock.move.x_studio_review_color in (3, 2)` (yellow/orange), но **нет красных/legacy-blue** | Закрыт, но есть substantial fixes — ревью в activity |
| 🔴 **Not closed** | `state != 'purchase'` OR любой `picking.state != 'done'` OR любой `stock.move.x_studio_review_color in (1, 4)` (red/blue legacy «нужен ввод») | Не закрыт, физика на склад не ушла (или частично), нужно решать лично |

#### §F1.2 Implementation design (open work)
**Поле:** `purchase.order.x_studio_pedido_status` (selection: `green` / `yellow` / `red`) — computed через server action или Studio compute.

**Compute logic (псевдокод):**
```python
def compute_pedido_status(pedido):
    if pedido.state != 'purchase':
        return 'red'
    pickings = pedido.picking_ids
    if any(p.state != 'done' for p in pickings):
        return 'red'
    moves = pedido.picking_ids.move_ids
    if any(m.x_studio_review_color in (1, 4) for m in moves):
        return 'red'
    if any(m.x_studio_review_color in (3, 2) for m in moves):
        return 'yellow'
    return 'green'
```

**Trigger:** server action / base.automation на изменение `stock.move.x_studio_review_color` и `stock.picking.state` — recompute parent pedido status.

**Visual:** kanban view конфиг — color-by `x_studio_pedido_status`. Или badge widget в list view.

#### §F1.3 Implementation status
🔴 **Не реализовано** — design note. Implementation требует:
1. Studio: создать selection field `x_studio_pedido_status` на `purchase.order`.
2. Server action компьютирующая статус (base.automation на изменение related stock.move.x_studio_review_color).
3. List view конфиг — colored badge / decoration по статусу.

Делать **после batch reception** (пока 166 pedidos closed по алгоритму, status не критичен — owner идёт по activity queue).

#### §F1.4 Workaround до implementation
Owner использует существующие Odoo фильтры:
- **Closed all clean (🟢):** filter `state='purchase'` + `activity_ids = []` (нет activity). Activities не создаются для зелёных-чистых pedidos (по §3 Step 12).
- **Closed needs review (🟡):** filter `state='purchase'` + `activity_ids != []` (есть activity).
- **Not closed (🔴):** filter `state='draft'` OR `state='purchase'` AND `any(p.state != 'done' for p in picking_ids)` OR `any(m.x_studio_review_color in (1,4) for m in picking_ids.move_ids)`.

### §F2 MCP user attribution (long-term)
MCP authenticate'ится как Andriy → auto-tracking messages от его имени для прямых writes на line (price/name). Workaround сейчас — accept spam от Andriy на line-level. Long-term — bot res.users + отдельный API key (требует licensing review owner).

### §F3 Action 1217 v7.8 backlog (low priority)
- Добавить `x_studio_expected_qty: False` в ROLLBACK clear-set (текущий v7.7 не чистит).
- Auto-cancel orphan backorder picking через штатный `picking.action_cancel()` — на случай если zero-backorder gate всё-таки даст осечку. **НЕ direct state-write** (G8 violation).

### §F4 Algorithm-level deferred (next iteration)
- **L7 duplicates tie-breaking** — когда два candidate'а внутри narrow identity block, добавить explicit tie-breaker в §A2: `strongest code → operator hit → exact qty → closest qty → semantic specificity → line order weak`.
- **L8 3-fold mismatch таксономия** — формализовать в §A2: «missing line vs wrong card vs diagnostic mismatch» как три самостоятельных категории (сейчас покрыты через §G + §B, но не классифицированы единообразно).
- **§A4 carantine 214-279 inline list** — заменить deferral на live `product.category` явным списком категорий.
- **§F1.4 workaround edge case** — не покрывает «post-gate red на done picking» (теоретически недостижимо, но бы защитить).
- **n2/n3/n4** — глоссарий RU/EN терминов, version log v1-10 expand, hard rule #3 контекст.
- **m9** — verification note для остальных hardcoded IDs (`activity_type_id=4`, partner IDs).

---

## §G — EDGE CASES (consolidated)

| Case | Detection | Action |
|---|---|---|
| Empty paper / corrupted PDF | pdftotext output не содержит keywords {Cant, Concepto, Total} | Try `-raw` без `-layout`. Если всё равно нет keywords → BLOCKER C |
| Multi-paper split (12439827-B/G/P) | Несколько pedidos с одинаковым ref + B/G/P суффиксом, разные dirección | Supervisor manual (не subagent), 3 albaranes на 3 разных warehouse |
| Bookkeeper edit after first reconcile | item_comment содержит `✅ Verified` но qty/price не совпадают с paper | 🟡 manual_edit_detected, не trogai |
| Concepto на каталанском | Fuzzy match не находит карту | BLOCKER C сразу + activity для owner. Transliteration / extended fuzzy out of scope subagent |
| Multi-IVA на одной MIX | paper N строк с разным IVA на одну Odoo MIX | Split на N Odoo lines с тем же продуктом, разные tax_ids |
| Phantom dup в Odoo (Odoo 2 одинаковые, paper 1) | Same product_id, same qty | Обнулить вторую (qty=0) + comment |
| Missing line (paper N+1, Odoo N) | После positional match есть unmatched paper | Создать новую order_line на найденную card OR Variant C BLOCKER если card неясна |
| **Bookkeeper merge с дропом** (paper 4 строки → Odoo 3 линии, одна потеряна — кейс 12421571 §5.6) | `Σ matched paper qty < Σ paper.cant` И `Σ stems на Odoo line ≠ Σ matched paper qty` | Создать недостающую order_line на найденную card OR BLOCKER C если потерянная строка не определяется. Activity «бухгалтер потерял paper строку при импорте» |
| **Wrong-product substitution by coincidence** (бухгалтер взял случайно похожий товар, qty/price совпали — кейс 12421571 §5.6 F Arroz Pink↔OZOTHAMNUS) | Identity gate fails, но qty/price совпадают подозрительно близко | BLOCKER C — activity «бухгалтер положил X (paper Y), идентификация не подтверждается, проверь физически» |
| ×N inflation paper vs Odoo (×3+) без UD VENTA Paquete | Подозрение pack/stem confusion | Проверить known pack товар. Если EUC/Mimosa/Skimmia/etc — pack treatment. Иначе flag |
| Holded import даёт `tax_ids=[]` | Empty tax | Записать explicitly по paper IVA |
| **SKU typo Levenshtein 1-2** (бухгалтер ошибся 1-2 символами в codigo, например 196920 вместо 165920) | Levenshtein(paper.ref, learned.codigo) ∈ {1,2} И identity match по concepto strong | High prob опечатка → reassign на правильный codigo + 🟠 orange + activity «коррекция SKU typo X→Y» |
| **Qty digit-loss** (paper 19, Odoo 9; paper 30, Odoo 3 — потерянный первый знак) | `paper.cant > 10 * Odoo.qty` или `Odoo.qty * 10 ≈ paper.cant` ± MINOR | Suspect digit-loss → 🟠 orange + activity «бухгалтер потерял разряд: paper N, Odoo N/10. Подтвердить paper.qty?» Применять paper.qty с warning, **не** auto-blocker |

---

## §H — RUNTIME CHECKLIST (для agent перед стартом каждого pedido)

- [ ] У меня есть доступ к: (a) этот файл (`reception_algorithm.md`), (b) `reconcile_finalize_action.py` (mirror action 1217 в проде, v7.7 contract), (c) `review_status_automation.py` (mirror action 1146 в проде, color/review_status logic — referenced from §B7)
- [ ] paper PDF доступен локально на `master-context/pedido.paper/verdnatura_<docNum>.pdf`
- [ ] Знаю `pedido_id`, `partner_ref` (=paper docNum), `partner_id=42` (Verdnatura, **не 23**)
- [ ] Понял §0 hard rules (особенно #6 wrong-match-worse-than-unmatched)
- [ ] Понял §A2 strict identity gate + flexibility + evidence priority + match-method discipline + confidence bands
- [ ] Понял §B decision trees (decisive A/B/C, никаких половинных)
- [ ] Понял §C text format (plain language first для owner на мобильном)
- [ ] Понял §D action 1217 contract (что код делает / что **не** делает)
- [ ] Понял §K stop-signal protocol (если owner пишет СТОП — abort)

---

## §I — SUPERVISOR-LEVEL WORKFLOW (вне scope agent)

Этот блок — для supervisor session, не для agent.

1. **Setup** (один раз): pedidos re-imported, supplierinfo wiped, action 1146 + 1217 prod, `pedido.paper/` synced + GitHub public.
2. **PDF re-attach** на 166 numeric pedidos через subagent (mass batch, idempotent).
3. **Pilot pass** — supervisor сам обрабатывает 5-10 первых pedidos, refines algorithm decisions с owner.
4. **Algorithm freeze** — fix этого документа, commit + push.
5. **Batch** — subagents per 10 pedidos, owner checkpoints after каждой партии.
6. **Owner review** — пройти activity queue, отметить done или дать решение per pedido.
7. **Special cases** — 6 особых через supervisor (B/G/P split, correction-*).
8. **Out-of-scope Verdnatura**: Serviflor (без codigo), holded.factura split — отдельные workflow.

---

## §K — STOP SIGNAL PROTOCOL

Subagent работает автономно — не разговаривает с owner мидл-pedido (только через `mail.message` summary + `mail.activity` activity queue после verify). Но **если** в любой точке pipeline возникает прямое owner-input в чате (`СТОП` / `постой` / много восклицательных знаков / «отмени»):
- **Немедленно** прерывает текущий pedido — никаких «ещё одно действие и остановлюсь»
- Постит chatter с фактом остановки + текущим прогрессом (что успел изменить)
- Сбрасывает `x_studio_claude_finalize=False` если был выставлен
- Возвращает control supervisor

Не продавливать через. Остановка важнее завершения.

---

## §J — VERSION

- **v: 19 — 2026-05-01** — fixes from pilot 12491307 owner feedback (82.48-82.53). **§A3.2 supplierinfo upsert** — добавлен `uom_id` field (=31 для pack товаров, =1 для stem) — без него цена интерпретировалась per Tallo даже на pack. Plus rule «search empty default supplierinfo first, update вместо create new» — устраняем дубликаты от Holded import. **§A3.3 mandatory chatter log** на product.template при любом изменении (description_purchase/codigo_fabrica/name/supplierinfo) — audit trail для owner. **§B3 + action 1217 v7.8 zero-backorder** — Phase A2 для pack lines пишет `move.product_uom=1 (Tallo) + product_uom_qty=stems` — Odoo не пересчитывает по 1:10. После button_validate v7.8 cleanup loop — orphan backorder pickings (state≠done, backorder_id≠False) → action_cancel() + unlink(). Owner override prior G8 rule 82.51: cancel+delete bot-side. **§C3 📦 emoji mandatory** на pack item_comment всех статусов — owner видит pack в pedido list immediately. Action 1217 v7.8 запушен в prod (id=1217 ir.actions.server.code обновлён через MCP). Manual cleanup от pilot 12491307: 4 pack supplierinfo поправлены (uom_id=31), 13 пустых default supplierinfo удалены, 2 orphan backorder pickings (304, 306) cancelled + unlinked.
- **v: 18 — 2026-05-01** — §A3.1 rule simplified per owner clarification 82.45: «учим все non-blocker строки, не учим blocker C, второй проход после owner resolution». Card type (placeholder/quarantine/normal) больше НЕ критерий. Не теряем data на любую decisively-обработанную строку.
- **v: 17 — 2026-05-01** — fixes from pilot 12421571 + 12267946 owner feedback. **§A3 expanded supplierinfo** + product.template enrichment (codigo + price + date_start + product_name with attributes + description_purchase + x_studio_codigo_fabrica + optional rename via activity); placeholder vs quarantine clarification (🚫 quarantine = LEARN, ⛔НОВЫЙ ТОВАР / FLOR EXOTICA = NO LEARN — pending owner final decision per chat 82.44). **§B2 row 4 reformulation**: Odoo<paper Δ>tolerance — paper-truth + 🟡 yellow (раньше был red blocker) для moderate Δ ≤ MAJOR_THRESHOLD (=max(15, 30%)); only extreme Δ>MAJOR → 🔴 red. **§B2 pack matrix**: pack-conversion alone = silent green (НЕ orange) — explicit anti-pattern after subagent misclassified 4 pack rows as orange. **§B3 zero-backorder mechanism v17**: Phase A2 для pack lines пишет ОБА (`quantity` + `product_uom_qty = expected_qty / paq.factor`) — корневой fix на UoM 1:10 Odoo баг. Subagent rule: НИКОГДА direct state-write на picking (G8 violation, audit B3); если backorder возник — оставить + 🟠 activity. **§C1 opening шаблон**: естественный язык-история без жаргона (pack-stress-test, Phase A2, BLA/IN/...) — owner's mobile readability requirement.
- **v: 16 — 2026-05-01** — restored 4 concrete operational guidances из v1 потерянных в condensation: §A2.11 Matching algorithms (positional 1:1 / qty-match / concept fuzzy / multi-paper→1 MIX consolidate); §A2.9 quantitative threshold ±50% price-similarity для consolidate-OK vs Variant A split; §3 Step 8 split на Hard checks (blocker) vs Diagnostic warnings (activity не blocker — totals/subtotal через L12 v3.5 политику); §G два паттерна — SKU Levenshtein 1-2 typo и Qty digit-loss (paper 19 Odoo 9). Идеальная агрегация v1 mechanics + v3.5 policy + HANDOVER hard rules + pilot 2026-04-30 decisions + audit fixes.
- **v: 15 — 2026-05-01** — fix re-audit findings on v14: NB1 §B7 pseudocode regression (silent paper-truth price write was triggering yellow on every line — теперь explicit no-op для color logic); NM1 dark-blue=8 был unreachable из-за порядка проверок — переписан pseudocode с first-match-wins иерархией; NM2 conflict §B7 vs §B2:412 на accept-Holded ≤MINOR — green wins (historical precedence); NM3 pack-conversion within tolerance = green per §B2:419, только pack-with-Δ>tolerance = orange; NM4 D9 — `review_status_automation.py` добавлен в §H runtime checklist как contract mirror. Минор: «логист»→«бухгалтер/флорист», `picking_ids[0]`→`any(p)`, «Skip line»→«Skip pedido (mid-flight)». Backlog (§F4) для L7/L8/L12 + carantine + workaround edge case.
- **v: 14 — 2026-04-30** — restored from v11 (lost during v12 condensation): §B7 color assignment matrix (когда ставить какой цвет, особенно dark-blue=8 «robot clean fill» case), §F1 pedido-level visual status full content (3-tier definition + workaround filters + implementation design pseudocode). Owner workflow + agent decision logic preserved.
- **v: 13 — 2026-04-30** — integrated audit findings (5 BLOCKER + 11 MAJOR из independent audit). Restored from v3.5: identity gate с примерами, identity flexibility, broad tokens-not-identity, match-method discipline, confidence bands, learned vendor code rule, operator command rule, preserve existing card rule, blocker-C-not-dump-bucket. Restored from HANDOVER: partner_id=23 warning, stop-signal protocol §K, bookkeeper merge-with-drop / substitute patterns. Production drift fixed: §D1 ROLLBACK enum, §D1 RETRY filter correct, §D2 expected_qty pre-flight invariant. Removed: §F1 uom_id (gap closed), §F2 backorder cleanup (non-issue per owner — backorder = bug, not feature). Decisive paper-truth on Δ>5 в плюс (v12 row 3 confirmed correct). ×2 ratio: paper-truth + 🟡 yellow «двойной импорт» (v12 row 5 reformulated). Self-containment enforced: убран read MEMORY.md из §H.
- v: 12 — 2026-04-30 — full restructure as agent specification
- v: 11 — 2026-04-30 — accumulated decisions during pilot session 2026-04-30 (decisive A/B/C, MIX-card preferred, pack-conversion silent, address-based blocker, search-before-create)
- v: 1-10 — see git log (initial Make.com module 149 prompt v3.5 baseline → first Odoo agent specs)

Изменения трекаем через git. Для изменений алгоритма — bump v + commit + push.
