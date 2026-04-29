<!-- v: 2 | updated: 2026-04-29T23:50Z -->
# Verdnatura reception algorithm — Espafloria 2026

Жёсткий алгоритм приёмки albaranes Verdnatura для свежей сессии Claude. Subagents следуют без отклонений. Supervisor (Claude в свежей сессии) калибрует на pilot и обновляет с owner approve.

Baseline + alignment: Make.com bot module 149 (`prompt_reconciliation_v3.5.txt`).

---

## 1. Paper-truth hierarchy

### 1.1 Источники
1. **PDF от Verdnatura** = единственная истина (ошибки крайне редки).
2. **Odoo lines после Holded import** содержат ДВА мнения:
   - Мнение бухгалтера (на какую карту положил товар).
   - Мнение флориста (сколько штук физически приехало после раскрытия паков).
3. Оба мнения могут ошибаться независимо.

### 1.2 Без PDF не закрываем pedido — никогда.

### 1.3 Иерархия paper-truth по детальности
| Уровень | Источник | Детальность |
|---|---|---|
| 1 | Individual albaran PDF в Holded Archivos | Ref + Cant + Concepto + Productor + COLOR/ALTURA/MACETA/UD VENTA + PVP + IVA + Importe |
| 2 | Вырезанная страница из monthly factura | Ref + Cant + Concepto + PVP + IVA + Importe |
| 3 | Monthly factura целиком (cross-reference) | то же что L2 |
| 4 | Ничего | НЕ закрываем, флаг для owner |

### 1.4 Где paper лежит физически
- `master-context/pedido.paper/verdnatura_<docNum>.pdf` — 166 individual + split-pages
- `master-context/pedido.paper/verdnatura_factura_<period>_<facNum>.pdf` — 4 monthly facturas (декабрь 2025, январь/февраль/март 2026)

---

## 2. Paper parsing

### 2.1 Извлечение текста
```bash
pdftotext -layout /path/to/verdnatura_<docNum>.pdf -
```

### 2.2 Структура строки товара (фиксированные колонки Verdnatura)
```
<Ref>  <Cant>  <Concepto>  <Productor>  <PVP>€  <IVA>  <Importe>€
```

### 2.3 Атрибуты под основной строкой
Подстрока с UD VENTA / COLOR / ALTURA / MACETA / PESO/TALLO / Nº FLORES / TAMAÑO BOTON / DIÁMETRO / LONGITUD BROTE.

**UD VENTA Paquete** — критический сигнал что строка в паках.

### 2.4 IVA коды
- **G** = General 21%
- **R** = Reduced 10% (растения, срезка)

### 2.5 Sanity check
- Sum (Cant × PVP) каждой строки = Importe
- Sum всех Importe = Subtotal
- Subtotal × IVA_rate + Subtotal = Total

### 2.6 Edge case — пустой paper
Возможные причины:
1. Бухгалтер забыл приложить PDF в Holded → искать в monthly factura.
2. Один paper разрезан на N albaran (split по магазинам, mnemonic суффиксы B/G/P) → supervisor + owner.
3. PDF в Holded был, но не доскачался → перепроверить Holded UI.
4. Ошибка нумерации albaran → проверить соседние docNum.
5. Cancel pedido — крайний случай, только через owner approve.

---

## 3. Matching paper ↔ Odoo lines

### 3.1 Принципы (из v3.5 prompt — Make.com bot module 149)
- LLM делает identity matching, Python делает арифметику.
- Safety > Coverage: wrong match хуже unmatched.
- 5 независимых решений per строка: candidate / quantity / pack-vs-unit / tax / price action.

### 3.2 Иерархия доказательств identity match
1. **Обученный codigo** (`product.supplierinfo.product_code` = paper.ref).
2. **Operator hit** (`x_studio_operator_hit` на Odoo line).
3. **Existing plausible assignment** (бухгалтер на разумную карту).
4. **Fabrication code** (`x_studio_codigo_fabrica`).
5. **Default code** карточки.
6. **Semantic similarity** (только tie-breaker).

### 3.3 Strict identity gate
Допустимо: rose ↔ rose, chrysanthemum ↔ chrysanthemum, EUC cinerea ↔ EUC cinerea.
НЕ допустимо: rose ↔ general flower, EUC cinerea ↔ EUC parvifolia.

### 3.4 Алгоритмы матчинга (по убыванию надёжности)
1. **Positional 1:1** — N=M, qty в одинаковом порядке.
2. **Match по qty** — N=M но позиции сбиты, переставляю Odoo строки.
3. **Match по концепту** — substring / first-word / Levenshtein on default_code.
4. **Multi-paper → 1 Odoo MIX** (consolidate) — sum paper qty = Odoo qty, paper concepto одного семейства.

### 3.5 Edge cases
1. **Paper > Odoo** (бухгалтер пропустил): искать карту по concepto fuzzy → создать line; иначе создать новую card в карантине + line.
2. **Odoo > Paper**: phantom (qty=0+price=0) — delete; иначе set qty=0 + comment.
3. **Wrong card**:
   - Цена близка (±50%) к codigo на этой карте → keep.
   - Цена сильно отличается (×1.5+) → split: создать distinct card + reassign.
4. **Lazy match** (на MIX вместо специфичной существующей): найти specific card → reassign.
5. **Дубликат строки** (Odoo две одинаковых, paper одна): обнулить вторую + comment.
6. **Глупая опечатка SKU** (Levenshtein 1-2): high prob опечатка → reassign.
7. **Глупая опечатка qty** (paper 19, Odoo 9): suspect digit-loss → flag.
8. **Bookkeeper edit after first reconcile** (4.1 audit edge): `item_comment` уже содержит `✅ Verified by Claude AI <date>` но `product_qty` или `price_unit` не совпадают с paper (owner / bookkeeper руками поправил после моего pass). → не перетереть, флаг 🟡 «manual edit detected, owner-confirmed».
9. **Битый pdftotext** (4.2 audit edge): pdftotext выдал empty или очень короткий текст (<100 chars) → попытаться `pdftotext -raw` или `pdftotext` без `-layout`; если всё ещё битый → flag pedido red «PDF corrupted».
10. **Concepto на каталанском или нестандарте** (4.3 audit edge): fuzzy match не находит карту по испанскому. → попробовать transliterate (catalan→spanish substring), Levenshtein расширить порог 5+; если nothing → flag для owner с paper concepto and proposed candidates.
11. **Multi-line одна Odoo карта но разные IVA** (4.4 audit edge): paper имеет N строк с разным IVA (R 10% и G 21%) на одну Odoo MIX card. → split на 2 Odoo lines (одна 10%, другая 21%) с тем же продуктом, или flag если непонятно.

---

## 4. Per-line decision tree (5 решений)

### 4.1 Карточка
- Matched через обученный codigo → confident.
- Bookkeeper assigned reasonable card → keep.
- Bookkeeper wrong card с близкой ценой → keep (consolidate OK).
- Wrong card с разной ценой (×1.5+) → reassign / split (substantial fix → 🟠).
- Карта-placeholder (`⛔НОВЫЙ ТОВАР`) → search existing → reassign or create new.

### 4.2 Количество (с учётом pack/stem)

#### Pack/stem detection signals (детектирую перед quantity decision)
1. UD VENTA Paquete в paper → **pack**
2. Розы любого сорта (10/12/25 шт., редко 6) → **pack** (default)
3. Известные pack-товары: Mimosa, Skimmia, EUC, Lentisco, Acacia, Ranunculus pequeño, и т.д. (список дообучается)
4. Уже learned pack товар (supplierinfo с unit Paquete) → **pack**
5. Сильное несовпадение paper qty vs Odoo qty (×3+) → **pack suspect**
6. Иначе → **stem**

#### Pack case
| Поле | Значение |
|---|---|
| `product_qty` | paper paq count |
| `product_uom_id` | 31 (Paquete) |
| `price_unit` | paper PVP per paq |
| `x_studio_expected_qty` | florist physical stems count |
| amount line | paper paq × PVP/paq = paper Subtotal | 
| stock.move.quantity (Phase A2) | `expected_qty` (florist stems) |
| stock.move.x_studio_received_packs (Phase A2) | paper paq count |

#### Stem case
| Поле | Значение |
|---|---|
| `product_qty` | paper qty (stems) |
| `product_uom_id` | Tallo / Unidades default |
| `price_unit` | paper PVP per stem |
| `x_studio_expected_qty` | florist physical count |
| stock.move.quantity (Phase A2) | `expected_qty` (florist) — почти всегда |

#### Decision rule по qty (карточка ОК) — **direction-aware**
По handover §2.4 owner verbatim: «положительная дельта (Odoo > paper) = щедрость поставщика → auto-OK; отрицательная (paper > Odoo) = подозрение → flag».

| Случай | stock.move.quantity | review_color | reason |
|---|---|---|---|
| Pack (UD VENTA Paquete) | florist stems (expected_qty) | оранжевый 🟠 (2) | substantial pack-conversion |
| Stem direct (paper == florist) | paper (= florist) | зелёный ✅ (10) | clean match |
| Stem small delta любого знака (\|delta\| ≤ 5) | florist | жёлтый 🟡 (3) | физическая порча / extra |
| Stem **positive** delta > 5 (Odoo > paper) при правильной карточке | florist | жёлтый 🟡 (3) | accept Holded recount — Verdnatura переотгрузил («щедрость») |
| Stem **negative** delta > 5 (paper > Odoo) при правильной карточке | flag | красный ❌ (1) | бухгалтер недосчитал ИЛИ массивная порча — owner decode |
| ×N positive >2 без pack signals | flag | красный ❌ (1) | suspect pack/stem confusion — owner verify pack или real over-delivery |
| **×2 ровно** ratio | flag | красный ❌ (1) | suspect bookkeeper double-scan (handover §5.7 — 5/7 accept-Holded имели ≈×2) — owner подтверди |

### 4.3 Pack-vs-unit
Уже принято в 4.2. Документируется в `x_studio_item_comment` с иконкой 📦.

### 4.4 Налог
- Paper IVA = R 10% → tax_id = 10% (см. § 12 для конкретных IDs).
- Paper IVA = G 21% → tax_id = 21%.
- Если Odoo line имеет другой tax → переписать.

### 4.5 Цена
- `price_unit` = paper PVP per uom.
- Если совпадает (≤0.01€ delta) → no action.
- Иначе → update + лог.

---

## 5. Card creation

### 5.1 Когда создавать новую карточку
**Только** при серьёзном обосновании:
1. Не нашёл существующую (ни Levenshtein на SKU, ни fuzzy concepto, ни learned codigo на других картах).
2. Wrong card с большой разницей в цене (×1.5+) — split MIX на distinct.

**Default**: использовать существующую карту (даже MIX) если разумно. Не плодить.

### 5.2 Местоположение — карантин (default)
Категория id=207 «⛔ Карантин Holded» с подкатегориями:
- 210 EMBALAJE — упаковка
- 280 DECORACION — вазы, декор
- 281 PRODUCTO DESCONOCIDO
- 211 ENTREGA
- 212 FLORES CORTADAS — срезка
- 213 PLANTAS EN MACETAS — горшечные
- 214+ — спец. подразделы

Чистая зона — редко, только при сильной уверенности.

### 5.3 Поля при create
| Поле | Значение |
|---|---|
| name | `🚧🟠 <paper concepto>` |
| default_code | next sequential 84001NNN (или 84010NNN для embalaje) |
| categ_id | по типу товара (см. 5.2) |
| type | `'product'` |
| list_price | 0 |
| standard_price | paper PVP |
| uom_id | 1 (Tallo) или 31 (Paquete) по UD VENTA |
| uom_po_id | то же |
| description_purchase | `Auto-created by Claude AI <date> from paper {ref} {concepto} {productor}` |
| image_1920 | `set_binary_field` с `https://cdn.verdnatura.es/image/catalog/1600x900/<paper.ref>`. **404 fallback**: try-catch вокруг set_binary_field, если 404 → leave empty (no error raise), записать в `description_purchase` строку «no image: Verdnatura CDN 404» |
| purchase_method | `'receive'` |

### 5.4 SKU sequential
```
search product.template default_code =ilike '84001%' order desc limit 1
→ extract NNN, +1
```

### 5.5 supplierinfo (Vendor Price)
| Поле | Значение |
|---|---|
| partner_id | 42 |
| product_tmpl_id | new tmpl |
| product_code | paper.ref |
| product_name | `<concepto> (<productor>)` |
| price | paper PVP |
| min_qty | 1 |
| date_start | paper FECHA |

### 5.6 Reassign Odoo line
```
search product.product domain=[['product_tmpl_id','=',new_tmpl_id]] limit=1
→ variant_id
update purchase.order.line product_id=variant_id, name=f'[{84001NNN}] 🚧🟠 {concepto}'
```

---

## 6. Trigger action 1217 + verify

### 6.1 Pre-flight (before trigger) — только data fields
**Бейджи (review_color/review_status) computed action 1146 ПОСЛЕ Confirm**, до триггера их нет — поэтому pre-flight проверяет только мои данные:
- `sum(line.product_qty × line.price_unit)` ≈ paper Subtotal (±0.50€).
- amount_total ≈ paper Total ±1€.
- Все строки имеют supplier_sku, expected_qty (florist), supplier_product_name, item_comment, корректный product_uom_id (1 или 31), price_unit.
- Я **предсказываю** какой цвет получится из data на каждой line (синий/зелёный/жёлтый/оранжевый) — фиксирую в item_comment как `[Лог] predicted_color=...`.
- Ни одна предсказанная **красная** — иначе НЕ триггерю.

Проверка реального color — внутри action 1217 v5 на step 4 «Final gate» (см. 6.3) — после Confirm + Phase A2 + action 1146 пересчитал.

### 6.2 Trigger
```python
update_record('purchase.order', pedido_id, {'x_studio_claude_finalize': True})
```

### 6.3 Что делает action 1217 v5
**DRAFT branch** (state='draft', amount>0, supplier_sku есть на всех):
1. button_confirm() → state=purchase
2. **Phase A2** (расширенный):
   - Для каждой stock.move: `quantity = purchase_line.x_studio_expected_qty` (florist count)
   - Для pack lines: `x_studio_received_packs = purchase_line.product_qty` (paper paq)
   - **НЕ используем uom factor** для конвертации (variable count)
3. action 1146 пересчитывает `review_status` / `review_color` на каждом stock.move
4. **Final gate**: если все review_status начинаются с OK-prefix (синий / зелёный / жёлтый / оранжевый icons) → pass; красный — gate stops
5. button_validate(`skip_backorder=True`) → picking done

**RETRY branch** (state='purchase', picking assigned): soft-gate + validate.

**ROLLBACK branch** (note содержит `ROLLBACK_HOLDED_API`): reverse picking + button_draft + clear Phase A.

### 6.4 Verify через polling (НЕ fixed sleep)
Action 1217 + automation 1146 — async, время может занять >5s на больших pedidos. Использую **polling до stable state**:
```python
for attempt in range(6):  # max 30s total
    sleep(5)
    rec = get_record('purchase.order', pedido_id, ['state','picking_ids','x_studio_claude_finalize'])
    if rec.state == 'purchase' and rec.x_studio_claude_finalize == False:
        # automation отработала, проверяем picking
        pick = get_record('stock.picking', rec.picking_ids[0], ['state'])
        if pick.state in ('done', 'assigned'):
            break
    if rec.state == 'draft' and rec.x_studio_claude_finalize == False:
        # automation отработала, gate stop, остался в draft
        break
# Verify final
- state == 'purchase' AND picking.state == 'done' → ✅ closed
- state == 'draft' → 🟠 gate stopped (см. 6.5)
- amount_total ≈ paper Total ±1€
```

### 6.5 Если gate stop
Picking в state='assigned'. Pedido в 'draft'. Chatter post: `🟠 gate stopped on line X — review_status='<reason>'`.

### 6.6 Backorder
`skip_backorder=True` — никогда не создаём backorder.

---

## 7. Acceptance criteria (когда pedido «качественно» закрыт)

1. **Бумага = pedido**: каждая строка = paper (codigo, concepto, qty в paper-units, цена, IVA). amount_total ≈ paper Total ±1€.
2. **Физика на склад = florist**: `stock.move.quantity = x_studio_expected_qty`.
3. **Карточки обучены**: supplierinfo создан/обновлён для каждой пары paper.ref ↔ Odoo card.
4. **Все ошибки матчинга разрулены**: wrong card / lazy match / missing line / extra line.
5. **Все строки** на бейджах синий 🤖 / зелёный ✅ / жёлтый 🟡 / оранжевый 🟠 (НЕ красный ❌).
6. `state='purchase'`, picking `state='done'`.

---

## 8. Iconography + author + tone

### 8.1 Иконки + цвета (реальные prod IDs)
| Иконка | Цвет (review_color) | Smysl |
|---|---|---|
| 🔵 / 🤖 | **4** (blue) | Робот заполнил clean (no fixes needed) |
| ✅ | **10** (green) | Paper match perfect (OK) |
| 🟡 | **3** (yellow) | Minor auto-fix (qty ±5, price update, positive accept-Holded) |
| 🟠 | **2** (orange) | Substantial auto-fix (created card, split MIX, reassign, pack-conversion) |
| ❌ | **1** (red) | Блокер для owner (unresolved) |
| 🚧 | — | Quarantine card prefix |
| 📦 | — | Pack/stem case |
| ⛔ | — | Placeholder / unknown |
| ➕N / ➖N | — | Qty delta |

### 8.2 Author
Все `mail.message` create — `author_id=56` (🤖 Claude AI Reconciliation).

### 8.3 Tone — структура коммента (3 слоя)
```
[1 строка] Что произошло понятно (для owner на mobile)
[2 строка] Детали: codigo, qty, цена, IVA
[3 строка] [Лог] machine-readable structured (опц.)
```

Простой язык, минимум Odoo-жаргона. Owner читает на мобильном.

### 8.4 Activity для owner (review queue)
Создаю `mail.activity` на pedido для всех уровней **кроме** синий/зелёный:
- 🟡 жёлтый: «проверь — minor auto-fix» (валидация без правок)
- 🟠 оранжевый: «проверь — substantial auto-fix» (валидация)
- ❌ красный: «нужно решение» (owner даёт ответ → закрываю)

**Closure правило** (минор 3.3): когда owner отвечает в чате pedido либо отмечает activity как done — supervisor mark activity `state='done'`, чтобы review queue не накапливался мусором. Pedido может получить новую activity при последующей правке.

---

## 9. Idempotency = re-run safe

### 9.1 Skip правила
**Skip pedido если:**
- `state == 'cancel'` → отменён, не trogai.
- `state == 'purchase'` AND **все** picking_ids в state `done` → закрыт end-to-end, не trogai.

**НЕ skip если:**
- `state == 'draft'` — продолжаем работу (re-run on draft).
- `state == 'purchase'` AND есть picking в state `assigned` — это **RETRY case** (handover §3.2: base.automation 15 filter `state in ['draft','purchase']` именно для этого).

**Skip line если:**
- `x_studio_claude_finalize=True` уже стоит (action 1217 в работе) — wait, не trogai одновременно.
- На line `item_comment` содержит «✅ Verified by Claude AI <дата>» → skip line (уже сверена).

### 9.2 Re-run на draft / RETRY pedido
**Продолжает** работу с места где остановился. Если supervisor доработал алгоритм после прошлого pass — пытается разрешить красные с новыми правилами.

Для RETRY (state=purchase + picking assigned): применяет soft-gate retry через action 1217 RETRY branch без re-Phase-A (Phase A уже была сделана при первом проходе).

---

## 10. Iteration order

### 10.1 Список из Odoo
```python
mcp__odoo__search_records('purchase.order',
  domain=[['partner_id','=',42],['date_order','>=','2026-01-01'],['date_order','<','2027-01-01']],
  fields=['id','partner_ref','state','amount_total','order_line'],
  limit=200, order='partner_ref asc')
```

### 10.2 Filter numeric 8-digit
- `partner_ref` matches `^\d{8}$` → 166 numeric pedidos.
- Не-numeric → отдельный supervisor pass (не subagent).

### 10.3 Партии по ~10 numeric
Subagent processes 10 pedidos за партию, 2-5 минут per pedido (max 5).
Если subagent zalipает >5 минут на одном — pomeчает красным и идёт дальше.

### 10.4 После каждой партии
Subagent → отчёт: closed / flagged counts + per-flag причины.
Supervisor добавляет в общий лог + берёт следующую партию.

---

## 11. Workflow в общем

### 11.1 Подготовка (один раз ДО запуска)
**Owner делает:**
- 172 pedidos удалены + re-imported из Holded
- ~432 supplierinfo Verdnatura wiped
- Cards оставить (~19 моих + старше migrated)
- Мусорные поля удалены: `x_studio_claude_finalize_1`, `x_studio_char_field_3j4_1jl7fjno2` (Studio)
- Action 1146 расширен под синий (5) и оранжевый (2) уровни (Studio script)
- Repo `master-context` public для batch attach

### 11.2 Свежая Claude session = supervisor
1. Read handover + reception_algorithm.md (этот файл) + memory feedbacks (16 правил)
2. Read prompt_reconciliation_v3.5.txt (Make.com bot baseline)
3. Build numeric pedido list (166) через `mcp__odoo__search_records`
4. **PDF re-attach (первый actual шаг работы)**: re-imported pedidos после reset не имеют PDF в `ir.attachment`. Supervisor проходит по 166 numeric pedidos и через `mcp__odoo__set_binary_field` прицепляет PDF из `master-context/pedido.paper/verdnatura_<docNum>.pdf` (file source URL — GitHub raw на public repo). Two-step: create_record metadata + set_binary_field. **Idempotency check** (минор 3.4): перед create_record делаю `search ir.attachment domain=[['res_model','=','purchase.order'],['res_id','=',pedido_id],['name','=',f'verdnatura_{docNum}.pdf']]` — если total>0 → skip (attachment уже есть, не дублируем).
5. **Pilot pass**: первые 10-15 pedidos обрабатывает supervisor сам (НЕ subagent), внимательно. Validate algorithm на real data
6. Report owner pilot result: алгоритм держится? нужны правки?
7. Owner approve / refine algorithm
8. Batch через subagents (10 pedidos per batch) на остальные ~150

### 11.3 Per партия
Subagent следует строго Sections 1-7. 2-5 min/pedido.
Если pedido не закрывается — красный bage + chatter, идём дальше.

### 11.4 После всех 166 numeric
Activity для owner на каждом pedido где non-зелёный/синий бейдж (жёлтый/оранжевый/красный):
- Owner идёт по списку
- Жёлтые/оранжевые: «OK принял» (валидация)
- Красные: даёт решение per pedido → supervisor применяет → закрывает

### 11.5 6 особых pedidos через супервизора
- **12439827-B/G/P**: один paper разнесён на 3 albaran. Supervisor предлагает: один pedido + multi-warehouse picking, или 3 pedidos + раздельные paper.
- **correction-2026-01-05/-09/-02-02**: попытки бухгалтера исправить без paper. Supervisor приносит owner: cancel/merge/keep.

### 11.6 Финал — не только Verdnatura
- 100% numeric pedidos closed или explained
- 6 особых обработаны
- Затем не-Verdnatura: **Serviflor** (id=39, без codigo — adjusted algorithm), мелкие — ad-hoc
- Затем **holded.facturas с прямым распределением** товара (отдельный workflow, owner пришлёт данные)

---

## 12. Custom fields map

### 12.1 purchase.order
- `x_studio_claude_finalize` (bool) — триггер action 1217 ✓ used
- `note` (html) — для маркера ROLLBACK_HOLDED_API (substring match, не startswith)

### 12.2 purchase.order.line
- `x_studio_supplier_sku` (char) — paper Verdnatura ref ✓
- `x_studio_supplier_product_name` (char) — concepto + productor + атрибуты ✓
- `x_studio_expected_qty` (float) — **florist physical count** ✓
- `x_studio_item_comment` (char) — лог reconciliation ✓
- `x_studio_operator_hit` (char) — ручная подсказка от owner (read-only для бота)

### 12.3 stock.move
- `x_studio_paper_qty` (float, related) — paper qty (= purchase_line.product_qty)
- `x_studio_paper_unit` (m2o, related) — paper uom (= purchase_line.product_uom_id)
- `x_studio_received_packs` (float) — paq count (Phase A2 пишет для pack lines)
- `x_studio_avg_per_pack` (float) — auto computed
- `x_studio_diff_vs_expected` (float) — auto delta vs paper
- `x_studio_expected_qty_info` (float) — Logist re-calc NUM
- `x_studio_expected_qty_info_display` (char) — display
- `x_studio_review_status` (char) — text бейджа (action 1146 пишет)
- `x_studio_review_color` (int) — color ID

### 12.4 stock.picking — нет custom

### 12.5 Не использую
- `x_studio_char_field_3j4_1jl7fjno2` (мусор, удалить)
- `x_studio_claude_finalize_1` (duplicate, удалить)

### 12.6 Read-only для бота
- `x_studio_operator_hit` — owner пишет, я читаю как input для matching (Section 3.2 evidence #2).

---

## 13. Action 1146 расширение (review_status_automation)

### 13.1 Реальная prod палитра (per `03_inventory_pipeline.md §4.1`)
| Level | Цвет | ID | Smysl |
|---|---|---|---|
| 0 | 🟢 green | **10** | OK |
| 1 | 🔵 blue | **4** | Нужен ввод (бот хочет заполнить — «посчитать!», «...и пачки?») |
| 2 | 🟡 yellow | **3** | Расхождение с бумагой / пачками |
| 3 | 🔴 red | **1** | Расхождение с логистом (большое) |

### 13.2 Расширение под orange
Добавляем **новый** ID для substantial robot fix:
| Level | Цвет | ID | Smysl |
|---|---|---|---|
| (new) | 🟠 orange | **2** | Substantial auto-fix роботом (создал карточку / split MIX / reassign / pack-conversion) |

Re-purpose blue (4) семантически — теперь покрывает оба случая:
- Бот заполнил clean (auto-OK, нет проблем) — ✅ **переход** существующего значения
- Бот хочет ввода (legacy semantic, остаётся валидным)

### 13.3 Decision logic (псевдокод после расширения)
```python
if line had wrong-card fix or pack-conversion or new-card-created or split-MIX:
    color = 2  # orange — substantial fix
elif line had minor qty fix (≤5) or price update or accept-Holded positive delta:
    color = 3  # yellow — minor delta vs paper
elif paper.qty == florist.qty and price match and codigo learned:
    color = 10  # green — perfect OK
elif line clean auto by bot (positional + obloecho codigo, no fixes needed):
    color = 4  # blue — robot filled clean
elif paper > Odoo with delta >5 (negative) or ×N suspect or unresolved:
    color = 1  # red — needs owner
else:
    color = 4  # blue (default state — data filled but unverified)
```

### 13.4 Mirror
`master-context/review_status_automation.py` (existing) → расширить с orange (ID 2) branch и semantic переключение blue (ID 4) на «robot clean fill». Owner финализирует через Studio.

---

## 14. Что нужно от supervisor session

### 14.1 Перед стартом
- Прочитать reception_algorithm.md (этот документ) ✓
- Прочитать SESSION_HANDOVER_2026-04-29.md ✓
- Прочитать memory feedbacks (16 файлов в `~/.../memory/`)
- Прочитать prompt_reconciliation_v3.5.txt (Make.com bot baseline)

### 14.2 Pilot pass
Обработать первые 10-15 pedidos из 166 numeric **сам**, не subagent. Ищет:
- Алгоритм держится на real data?
- Какие edge cases не покрыты?
- Какие нюансы зафиксировать?

### 14.3 Algorithm refinement
Предлагает owner правки algorithm (новые секции, новые heuristics).
Owner approves → апдейт reception_algorithm.md → push.

### 14.4 Batch проход
После refined algorithm — subagents per 10 pedidos.

### 14.5 Owner review
После всех 166 — список activities. Owner проходится, валидирует или решает красные.

### 14.6 Fingerprint каждого закрытого pedido
В chatter каждого закрытого pedido — fingerprint (timestamp + algorithm version + supervisor session id) для traceability.

---

## 15. Принципы (memorized)

1. PDF = истина. Holded = глюк (бухгалтер + флорист могут ошибиться).
2. Без PDF — не закрываем.
3. Карта = один продукт = один codigo. Не сливать дорогую и дешёвую под одну карту.
4. На pedido level — деньги по paper. На stock — физика по флористу.
5. Pack vs stem variable count: pack count в paper, stems в stock.move (через Phase A2). НЕ используем uom factor.
6. ×N inflation > 2 БЕЗ pack signals → flag, не paper-truth slепо.
7. Создание карточки — только при серьёзном обосновании. По умолчанию use existing.
8. Карантин default для new cards. Чистая зона — редко.
9. `author_id=56` на ВСЕХ message_post.
10. Простой язык в chatter. Иконки для бейджа.
11. Cancel pedido — крайний случай. Только через owner approve.
12. Re-run safe (idempotency).
13. Subagent следует алгоритму строго. Supervisor может refine с owner approve.
14. ≤10% максимум красных pedidos (целевая планка качества).
15. Финал — не только Verdnatura: 6 особых + Serviflor (без codigo) + holded.factura split — отдельные workflow.

---

## 16. Где смотреть всё в Odoo

После прохода 166 pedidos owner видит:
- **Список pedidos** (фильтр Verdnatura 2026)
- `state` колонка: filter draft / purchase
- `picking_ids[0].state`: assigned / done
- **Color бейдж** (через review_color на stock.move агрегированно): синий/зелёный/жёлтый/оранжевый/красный
- **Activities** (mail.activity todo) на каждом non-зелёном pedido
- **Чат-лента** (mail.message с author_id=56) на каждом pedido — 3-слойный лог

Список activities = пошаговый review queue для owner: идти, отмечать «принято» или давать решение.
