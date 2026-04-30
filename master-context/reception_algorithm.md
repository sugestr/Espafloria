<!-- v: 11 | updated: 2026-04-30T21:00Z -->
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

#### 4.1.1 MIX-карта — PREFERRED grouping (decision 2026-04-30 v2)
**Owner verbatim 2026-04-30 v2 на pilot 12186258:** «есть логика все гвоздики посадить на один MIX, цена похожа и форма почти такая же, слегка цвет гуляет. Возможно остальные товары так же имеет смысл кидать на MIX карточку. Мы решили попробовать упростить и похожий товар группировать в продаже и учёте чтобы было легче флористам и нам. Если группировка оправдана — я бы её сохранял и даже продвигал дальше».

**Принцип: MIX-карта PREFERRED (не просто допустимо)** для семейного товара когда:
- **Форма/тип почти совпадает** (CL разных сортов, CR разных сортов, PAN разных цветов, PHAL разных variants)
- **Цены закупки близкие** — `max(prices) / min(prices) ≤ 1.5`
- **Цвет / сорт / productor варьируется**

**Цель:** упростить учёт + флористам понятнее. Не плодить «карта = 1 codigo = 1 sort» если форма+цена близкие. На MIX-карту учим N разных Verdnatura ref через supplierinfo.

**Эксклюзивные premium variants** (цена ×1.5+ от средней по MIX) → distinct card обязательна (memory `feedback_card_distinct_codigos.md` priority).

**Примеры:**
- PHAL Cascade Rosa 8.22€, PHAL Mini 7.90€, PHAL Eleg 8.09€ → ratio 1.04, **OK на одной MIX-карте**.
- Monstera Adansonii 4.28€, Monstera Variegata Thai 29.10€ → ratio 6.8, **distinct cards обязательно**.
- Plantamix Pastel 8.74€, Plantamix Specialties 9.93€ → ratio 1.14, **OK на одной MIX-карте**.

При reassign на MIX-карту (когда identity match явный, цена близкая) → **🟠 orange** (substantial card change).

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

#### Decision rule по qty (карточка ОК) — **direction-aware** + **прогрессивный tolerance**

**Owner verbatim (decision 2026-04-30 на pilot 12186266):** «я бы сказал ±3 или 4 штуки на штучном товаре — это максимум расхождения. Ну разве что приезжала БОЛЬШАЯ ПАРТИЯ (например 200 штук) — там может быть больше ошибок. Для всяких веток типа мимоза — всегда плавающее число в пачках».

**Tolerance threshold по типу товара:**

```python
if is_pack_product:  # Mimosa, EUC, Skimmia, ветки, известные pack-товары
    tolerance = max(15, int(paper_qty * 0.30))  # 15 stems base, 30% — "в разумных пределах реалистичности"
else:  # Stem (штучный) — розы, гвоздики, лилии, etc.
    tolerance = max(4, int(paper_qty * 0.05))  # 4 stems base, 5% для больших партий
```

**Pack tolerance examples (owner verbatim 2026-04-30: «в разумных пределах реалистичности»):**
- Mimosa 100 stems (4 paq) → tolerance 30 → 70-130 stems OK
- EUC 50 stems (5 paq × 10) → tolerance 15 → 35-65 stems OK
- Rose pack 25 stems (1 paq) → tolerance 15 → 10-40 stems OK
- Pack 500 stems → tolerance 150 (30%)

**Примеры stem tolerance:**
- paper 12 stems → tolerance 4 (12+4=16 max OK)
- paper 50 stems → tolerance 4 (50+4=54 max)
- paper 100 stems → tolerance 5 (5%)
- paper 200 stems → tolerance 10 (5%)
- paper 500 stems → tolerance 25

**Decision matrix:**

| Случай | stock.move.quantity | review_color | reason |
|---|---|---|---|
| Pack (UD VENTA Paquete or known pack товар) | florist stems (expected_qty) | оранжевый 🟠 (2) | substantial pack-conversion |
| Stem direct (paper == Odoo) | paper | зелёный ✅ (10) | clean match |
| Stem **\|delta\| ≤ tolerance** на штучном | florist | жёлтый 🟡 (3) | физическая порча / minor extra |
| Stem **positive** delta > tolerance (Odoo > paper) на штучном | **paper** (override Odoo) + comment | оранжевый 🟠 (2) — orange not yellow | **Подозрение на ошибку пересчёта бухгалтера**. Поставщик не делает +N stems на штучном товаре. Возвращаем к paper. Activity для owner: «paper N, Odoo M (+delta) — возможно pack/stem конфузия или ошибка ввода». Если owner решит overrule → ручной revert. |
| Stem **negative** delta > tolerance (paper > Odoo) на штучном | flag | красный ❌ (1) | бухгалтер недосчитал ИЛИ массивная порча — owner decode |
| ×N positive >2 без pack signals | flag | красный ❌ (1) | suspect pack/stem confusion — owner verify pack или real over-delivery |
| **×2 ровно** ratio | flag | красный ❌ (1) | suspect bookkeeper double-scan (handover §5.7 — 5/7 accept-Holded имели ≈×2) — owner подтверди |

**Изменение по сравнению с v7 алгоритма:** «положительная дельта auto-accept Holded → жёлтый» **БОЛЬШЕ НЕ default**. Теперь positive дельта на штучном товаре с >tolerance → **paper-truth wins + orange + activity**. Для pack-товаров — auto-accept по-прежнему OK.

### 4.3 Pack-vs-unit
Уже принято в 4.2. Документируется в `x_studio_item_comment` с иконкой 📦.

### 4.4 Налог
- Paper IVA = R 10% → tax_id = 10% (см. § 12 для конкретных IDs).
- Paper IVA = G 21% → tax_id = 21%.
- Если Odoo line имеет другой tax → переписать.

### 4.5 Цена — silent paper-truth override
**Paper price ВСЕГДА wins.** При сверке Verdnatura pedidos `purchase.order.line.price_unit` всегда выставляется = paper PVP. **Никаких markers** в item_comment, **никаких сравнений** с Holded/Odoo current price.

**Why (decision 2026-04-30 на pilot 12186258):** owner verbatim: «тебе НЕ важна цена в Holded или pedido — ты её всегда берёшь с PDF, не надо их сравнивать!» Также: «мелкие ошибки округления и подгонка финальной цифры в Holded — если расхождение до 5 центов = явно подгонка, просто пиши норм цену даже не помечай жёлтым».

**How to apply:**
- В Phase A на `purchase.order.line` — всегда `write({'price_unit': paper.PVP})` **silent**, без проверки delta, без markers.
- Не пишем `🟡` или текст «Цена: X → Y» в `x_studio_item_comment` для price-only fixes.
- В item_comment просто `✅` если linе clean. Если есть substantial issue (wrong card / wrong sort / phantom dup) → `🟠`. Цена сама по себе никогда не triggers `🟡`.
- Если paper PVP = 0 (очень редкий случай) → flag для owner, не записывать как-есть.
- Не относится к sale.order — там цена с pricelist.

### 4.6 Line.name синхронизация (decision 2026-04-30)
После Phase A — **всегда** проверить `line.name` на формат `[<paper.ref>] <paper.concepto>`:
- Если ref в скобках в name **НЕ совпадает** с `paper.ref` (бухгалтер использовал старый/чужой Verdnatura ref в name) → переписать на правильный.
- Если name был **пустым** или name = автогенерированный default по карточке (типа `[8400991] 🚫 SANSIVIERIA placeholder`) → переписать на `[paper.ref] paper.concepto`.
- Если карта была reassigned (§4.1 wrong card → reassign / split) → name переписывается обязательно (это уже было в §5.6).
- Если ref OK но concepto в name немного короче / отличается косметически (truncated, minor diff) → оставить (cosmetic, не trogai).

**Это считается substantial fix (🟠 orange)** — бот переписывает структурное текстовое поле бухгалтера. В `item_comment` лог: `🟠 ref/name: [<old>] → [<new>]`.

**Why:** owner на форме pedido видит `[ref] concepto` непосредственно в строке. Если там стейл-ref (например `[196920]` от старой партии когда paper говорит `[165850]`) или wrong concepto — confusion при ручном review. Должен быть один консистентный код везде. Owner verbatim 2026-04-30: «2.3.a да логично и впредь».

---

## 5. Card creation

### 5.1 Когда создавать новую карточку
**Только** при серьёзном обосновании:
1. Не нашёл существующую (ни Levenshtein на SKU, ни fuzzy concepto, ни learned codigo на других картах).
2. Wrong card с большой разницей в цене (×1.5+) — split MIX на distinct.

**Default**: использовать существующую карту (даже MIX) если разумно. Не плодить.

#### 5.1.1 Перед create — проверить existing robo-cards (decision 2026-04-30)
**Обязательный шаг перед create новой карточки:** search existing robo-cards (карточки сделанные ботом / прошлой migration v2.2) — могут уже покрывать identity:
- Префиксы name: `🤖🚧` / `🚧🟠` / `🚧` / `🤖`
- Диапазоны default_code: 84001152-84001170 (мои текущие 19), 84009xxx (migration v2.2 robo-cards), любые новые robo ranges (см. 5.4).
- Категории: 207 «⛔ Карантин Holded» + подкатегории (210/211/212/213/214/280/281).

Если найдена существующая robo-card точно по identity (узкий species match, не широкий family) → **reassign на неё**, не плодить дубль. Это substantial fix → 🟠.

Только если ни в чистой зоне (рукотворные Holded), ни среди existing robo-cards нет — create new.

**Owner verbatim 2026-04-30 (pilot 12187009):** «2.5.a — не надо новых карт» (если existing robo-card покрывает identity). Пример: Monstera Variegata Thai Constellation уже есть как 84009001 от migration v2.2 — reassign, не дублировать.

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

### 5.3.1 Barcode rule (decision 2026-04-30)
**Цветы (FLORES CORTADAS, ROSA UNIFLORA):** `barcode = default_code` строго. SKU и barcode должны совпадать.

**Твёрдые товары (DECORACION, EMBALAJE, JARRONES):** разрешено `barcode = manufacturer barcode` (отличается от default_code) — баркод от производителя на упаковке.

**Горшечные растения (PLANTAS EN MACETAS):** обычно `barcode = default_code`, но **иногда** можно manufacturer barcode (если на горшке/упаковке есть штрих-код).

При **создании** robo-card → всегда заполнять оба поля одновременно. При **rename** SKU → переименовать и barcode тоже (если они были синхронизированы; если barcode был от производителя — оставить).

**Why:** owner verbatim 2026-04-30 на pilot 12187009: «при фиксе робо-карт SKU и barcode должны быть синхронизированы — ты забыл про barcode как минимум в одной карточке». Затем уточнил scope: «все товары которые мы заводим по своим карточкам имеют уникальный SKU и он совпадает с баркодом для цветов — точно. Барcоды твёрдых и иногда горшечки можем использовать производителя».

**Pilot 12187009 fix:** 21 robo-card barcode синхронизирован с default_code (84001147, 84001148, 84001152-84001170, 84001171). 6 collision-templates 84001149/150/151 (по 2 template на каждый SKU от migration v2.2 bug) — отложены, нужен отдельный rename в свободные слоты.

### 5.4 SKU sequential — **continuous через robo + manual без gaps**
**Правило (decision 2026-04-30):** robo-cards идут sequential **сразу после max manual Holded SKU**, без gaps. Не плодить отдельные диапазоны (84009* был outlier, сейчас merged в 84001*).

```
# Find next SKU
max_code = search product.template default_code =like '84001%' order desc limit 1 (только 8-digit, отфильтровать 7-digit)
→ extract NNN, +1
```

**Текущее состояние 2026-04-30:**
- 84001000-84001146 — robo от migration v2.0 (147 cards, 🚫)
- 84001147-84001151 — robo от migration v2.2 (5 cards 🤖🚧, 3 collision-pairs)
- 84001152-84001170 — мои pilot cards (19, 🚧🟠)
- 84001171 — Monstera Variegata Thai (renumbered с 84009001)
- **next free: 84001172**

При create — обязательно: `default_code = next_sku`, `barcode = next_sku` (для цветов и в общем случае).

**Owner verbatim:** «в Holded там нумерация была порядковая и удобрная, чтобы не плодить SKU интервалы странные». Цель — один сплошной поток.

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

### 6.7 Gate-check логика (decision 2026-04-30, для v7)
**Старая (v5/v6) логика:** `if status.startswith('OK'): continue` — баг: emoji-prefix `🟠 OK` от action 1146 ломает startswith → gate перезатирает status на «OK (auto-minor -0)» (бессмысленный текст когда delta=0). Pilot 12187009 показал — на 3 оранжевых строках получили «-0», на 9 зелёных всё ОК.

**Новая (v7) логика — по color, не по тексту:**
```python
color = move.x_studio_review_color or 0
if color in (10, 8, 3, 2):    # green / dark blue / yellow / orange — все pass
    continue
elif color == 1:               # red — block, нужен owner
    flagged.append(...)
elif color == 4:               # blue — нужен ввод флориста
    flagged.append(...)
else:                          # color == 0 (нет computed) — fallback по qty delta
    paper = move.product_uom_qty or 0
    actual = move.quantity or 0
    delta = abs(paper - actual)
    if delta == 0:
        continue                # точное совпадение — let 1146 handle status
    elif delta <= MINOR_THRESHOLD:
        sign = '+' if actual > paper else '-'
        new_status = 'OK (auto ' + sign + str(int(delta)) + ')'
        if move.x_studio_review_status != new_status:
            move.with_context(...).write({'x_studio_review_status': new_status})
    else:
        flagged.append(...)
```

**Status text без `-0`:** delta=0 → не пишем status (1146 уже выставил). delta>0 → текст без silly «-0».

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
| 🤖 | **8** (dark blue) | Робот заполнил clean (no fixes needed) — НОВЫЙ ID, отличается от legacy 4 |
| ✅ | **10** (green) | Paper match perfect (OK) |
| 🟡 | **3** (yellow) | Minor auto-fix (qty ±5, price update, positive accept-Holded) |
| 🟠 | **2** (orange) | Substantial auto-fix (created card, split MIX, reassign, pack-conversion) |
| 🔵 | **4** (light blue) | Legacy «нужен ввод» (бот хочет данных от флориста) — оставлен **без re-purpose** |
| ❌ | **1** (red) | Блокер для owner (unresolved) |
| 🚧 | — | Quarantine card prefix |
| 📦 | — | Pack/stem case |
| ⛔ | — | Placeholder / unknown |
| ➕N / ➖N | — | Qty delta |

### 8.2 Author
Все `mail.message` create — `author_id=56` (🤖 Claude AI Reconciliation).

### 8.3 Tone — структура коммента / explanation (decision 2026-04-30 v3)
**Owner verbatim:** «общий отчёт тяжело читать много спец деталей сразу в лоб без понятного объяснения что случилось в принципе. Будут объяснения мне понятнее».

**Универсальная структура для item_comment + summary message + activity note + ответов в чате:**

```
1. ОБЗОР — что в принципе случилось простыми словами (1-2 предложения)
   └─ Без техники. Без ref/tmpl_id/uom_id/safe_eval. Что бот ПОНЯЛ + что СДЕЛАЛ.
   Пример: «Бухгалтер положил все хризантемы на один сорт (Molly Yellow), а в бумаге другой — Altaj. Поправил».

2. КАК ИСПРАВЛЕНО — короткие группы похожих фиксов
   └─ Если несколько похожих исправлений — группировать по типу.
   Пример: «5 строк гвоздик: бухгалтер положил все на один сорт «Molly Yellow», бот разнёс по правильным сортам с бумаги».

3. ДЕТАЛИ — список конкретных строк (только если нужно review owner'у)
   └─ Per-line bullet с минимумом jargon. Refs в скобках.

4. [Лог] — машинный лог в самом конце для аудита
   └─ Технические fields для re-process / debug. Owner может скипнуть.
```

**Принцип:** owner на мобильном должен ПОНЯТЬ суть за 5 секунд из первой строки. Детали и техника — внизу для тех кто хочет дойти до уровня.

**Per item_comment пример новый:**
```
🟠 Бухгалтер положил все хризантемы на один сорт (Molly Yellow), а в бумаге другой — Altaj Galaxy. Поправил название и код. Карта-полка та же общая для хризантем.
Бумага: 20 шт × 1.24€ = 24.80€ (Verdnatura ref 197433, IVA 10%, ALTURA 70cm).
[Лог] supplier_sku=197433 expected_qty=20 price=1.24 paper_match=positional card=MIX_consolidate
```

**Per summary message пример:**
```
🤖 Что случилось в принципе:
Бумага Verdnatura пришла с N строками на сумму X€ (warehouse, address).
Бухгалтер положил всё на правильные семейные карты, но СПУТАЛ конкретные сорта (для всех CR один «Molly Yellow», для всех TUL — «North Pole»). Бот разнёс по правильным сортам.

Также M строк это пачки (мимоза, евкалипт) — штатная ситуация, бот перевёл uom на «Пачки» 📦.

Что в результате:
• K substantial fixes — бухгалтер put неправильный сорт
• L pack-only — clean (зелёные с 📦)
• N clean — без правок
• Сумма pedido X€ ↔ бумага X€ ✅
• Picking PLA/IN/00XXX done на warehouse Y ✅

🟠 K substantial (нужен ревью):
1. [Ref] Concepto — что было / что стало / коротко.
...

✅ Чистых: список refs с 📦 для pack-only.

[Лог] session=... algo=v11 closed=...
```

Простой язык, минимум Odoo-жаргона. Owner читает на мобильном.

### 8.4 Activity для owner (review queue)
Создаю `mail.activity` на pedido для всех уровней **кроме** синий/зелёный:
- 🟡 жёлтый: «проверь — minor auto-fix» (валидация без правок)
- 🟠 оранжевый: «проверь — substantial auto-fix» (валидация)
- ❌ красный: «нужно решение» (owner даёт ответ → закрываю)

**Поля mail.activity (Odoo 19):**
- `res_model_id` (m2o → ir.model) — НЕ `res_model` (char). Для `purchase.order` нужен ir.model id (текущий = 819).
- `res_id` (int)
- `activity_type_id` — id=4 «To-Do» по умолчанию
- `user_id` — id=2 (Andriy) для owner review

**Closure правило** (минор 3.3): когда owner отвечает в чате pedido либо отмечает activity как done — supervisor mark activity `state='done'`, чтобы review queue не накапливался мусором. Pedido может получить новую activity при последующей правке.

### 8.5 Chatter rules (decision 2026-04-30) — **только на 2 ключевых событиях**
**Pedido chatter (mail.message)** — только сводные структурные сообщения на двух business events:

1. **Pack/stem detection** (после Phase A2, если есть pack lines) — список вида:
```
📦 Phase A2 (pack detection): найдено 3 пачки
• STATICE (ref 12345): 5 паков × 8 стеблей = 40 шт
• EUC (ref 67890): 2 пачки × 10 стеблей = 20 шт
```

2. **Picking validate** (после button_validate) — сводка:
```
✅ BLA/IN/00060 done. 12 строк сверены, paper 636.14€ ↔ Odoo 636.14€.
3 substantial фикса (см. activity).
```

3. **Errors / warnings** — `⛔ Claude finalize stopped (>MINOR): ...`, `❌ ERROR: ...` — условные, только при проблемах.

**НЕ постить в chatter:**
- Per-line price/sku/name updates — это в `purchase.order.line.x_studio_item_comment` (видно на форме строки).
- Auto-tracking «Полученное количество обновлено», «Цена изменена» — отключены через `with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True)` в action 1217 v6+.
- Generic «✅ Claude finalize done.» без деталей — был в v5, удалён в v6.

**Why:** owner verbatim 2026-04-30: «зачем мы пишем в message вот это? мусорим. вся эта инфа есть в pedido.line комменте». Затем: «там в логи разве что имеет смысл отмечать нашли пачки сделали то-то или ожидали 25 штук реально 22 штуки... сводный отчет хорошо. на этапе распознавания пачек и штук сводный итог имеет смысл, и потом сообщение когда пикинг делаем».

Все message_post — `author_id=56` (Claude AI Reconciliation partner).

### 8.6 Auto-tracking suppression (action 1217 v6+)
**Все writes/buttons под bot context должны быть с `tracking_disable=True, mail_create_nolog=True, mail_notrack=True`.**

```python
move.with_context(tracking_disable=True, mail_create_nolog=True, mail_notrack=True).write({...})
picking.with_context(skip_backorder=True, tracking_disable=True, mail_create_nolog=True, mail_notrack=True).button_validate()
```

**Why:** иначе Odoo auto-tracking создаёт mail.message «Полученное количество обновлено» под user'ом который запустил MCP-вызов (Andriy) — нарушение правила «author_id=56 на всех messages». На pilot 12187009 было 5 таких auto-сообщений от Andriy на picking. v6 закрыл это.

**Caveat:** MCP writes напрямую на `purchase.order.line` (не через action 1217) всё ещё могут триггерить auto-tracking под Andriy для tracked-полей (price_unit, name, product_id). Долгосрочный fix — bot res.users + отдельный MCP API key (out of scope). Промежуточный — переносить Phase A на лайны внутрь action 1217 (запланировано).

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
1. Read handover + reception_algorithm.md (этот файл) + memory feedbacks (`master-context/memory/` — 17 правил + MEMORY.md index)
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

### 12.5 Не использую (мусорные поля удалены 2026-04-29)
- `x_studio_char_field_3j4_1jl7fjno2` — удалён
- `x_studio_claude_finalize_1` — удалён

(см. § 11.1 setup checklist для context)

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

### 13.2 Расширение — добавляем 2 НОВЫХ ID
**Не trogai** legacy 4=blue («нужен ввод»). Вместо re-purpose выделяем **новые ID**:

| Level | Цвет | ID | Smysl |
|---|---|---|---|
| (new) | 🟠 orange | **2** | Substantial auto-fix роботом (создал карточку / split MIX / reassign / pack-conversion) |
| (new) | 🤖 dark blue | **8** | Robot clean fill — бот заполнил clean без правок |

Так что после расширения palette:
- 1 = red (legacy, расхождение с логистом / блокер для owner)
- 2 = **orange** (NEW — substantial robot fix)
- 3 = yellow (legacy, расхождение с бумагой / minor)
- 4 = blue (**legacy без изменений** — нужен ввод флориста)
- 8 = **dark blue** (NEW — robot clean fill)
- 10 = green (legacy, OK)

18 prod stock.moves с color=4 сохраняют свою «нужен ввод» семантику. Никакой миграции legacy не требуется.

### 13.3 Decision logic (псевдокод после расширения)
```python
if line needs florist input (нет данных, требует пересчёт):
    color = 4  # blue — legacy «нужен ввод» (бот ставит когда missing data)
elif line had wrong-card fix or pack-conversion or new-card-created or split-MIX:
    color = 2  # orange — substantial fix
elif line had minor qty fix (≤5) or price update or accept-Holded positive delta:
    color = 3  # yellow — minor delta vs paper
elif paper.qty == florist.qty and price match and codigo learned:
    color = 10  # green — perfect OK
elif line clean auto by bot (positional + obloecho codigo, no fixes needed):
    color = 8  # dark blue — robot filled clean
elif paper > Odoo with delta >5 (negative) or ×N suspect or unresolved:
    color = 1  # red — needs owner
else:
    color = 4  # blue (default — нужен ввод)
```

### 13.4 Mirror
`master-context/review_status_automation.py` (existing) → расширить с orange (ID 2) и dark blue (ID 8) branches. Legacy blue (4) остаётся как было. Owner финализирует через Studio.

Action 1217 gate (6.3 step 4) `startswith('OK')` отсечёт «нужен ввод» (review_status текст не начинается на «OK»), pedido не закроется автоматом — корректное поведение.

---

## 14. Что нужно от supervisor session

### 14.1 Перед стартом
- Прочитать reception_algorithm.md (этот документ) ✓
- Прочитать SESSION_HANDOVER_2026-04-29.md ✓
- Прочитать memory feedbacks в `master-context/memory/` (17 правил + MEMORY.md index — git-tracked для целостности базы знаний)
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

### 14.6 Fingerprint каждого закрытого pedido — конкретный формат
В chatter каждого закрытого pedido — fingerprint в третьем «Лог» слое коммента:
```
[Лог] 🤖 Claude AI session=<short_id> algo=v<n> closed_at=<UTC iso8601>
```
Конкретный пример:
```
[Лог] 🤖 Claude AI session=a4197a9 algo=v3 closed_at=2026-04-30T14:23:01Z
```
Где:
- `session=` — сокращённый session ID (первые 7 chars от agent / supervisor session ID)
- `algo=v<n>` — версия reception_algorithm.md (берётся из header `<!-- v: N | ... -->`)
- `closed_at=` — UTC ISO8601 timestamp момента когда action 1217 завершился (state=purchase + picking done verified)

Pour traceability: один grep по chatter в Odoo даст все pedidos закрытые в конкретной сессии или конкретной версии algorithm. Помогает отследить regression если algorithm refined и старые closures не валидны.

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

## 16. Warehouse / dirección entrega mapping (decision 2026-04-30)

**Правило (owner verbatim 2026-04-30):** «если адрес доставки (локация) по бумаге отличается от записи в pedido — это важная проблема, но ты её не можешь решить — блокер, даже если все линии зелёные. Доводишь всё что можешь и оставляешь на блокере на решения меня».

### 16.1 Mapping paper-адрес → warehouse (Espafloria 3 магазина + 1 archived)
| Paper «Dirección de entrega» содержит | Warehouse | picking_type_id | Notes |
|---|---|---|---|
| **Olimpic** / **Castelldefels** | Blau (id=4) | 28 (BLA/IN/) | Магазин Blau, Castelldefels — пляжный |
| **Augusta 109** / **Augusta 109 bis** | Plaza (id=2) | 10 (PLA/IN/) | Магазин Plaza, Barcelona, Via Augusta 109 (bis) |
| **Gloria** / **Macinista** / **Diagonal** | Gloria (id=3) | 19 (GLO/IN/) | Магазин Gloria Macinista, Barcelona, Diagonal |
| **Muntaner 260** | Temporal (id=5) **+ planned scrap** | 37 (TMP/IN/) | Закрытый ИП проданный магазин. Принять на Temporal, потом списать что не продалось до даты продажи. Архивирован, но используется для legacy 2026 albaranes. |
| Прочее / пусто / неопределённое | flag → owner | — | Назначение на Andriy (id=2), пусть разберётся |

### 16.2 Workflow проверки address при reception
1. Парсю paper → извлекаю «Dirección de entrega» (раздел над «Datos fiscales»).
2. Читаю Odoo `purchase.order.picking_type_id.warehouse_id` (текущий warehouse).
3. Match:
   - Paper address содержит ключевое слово из 16.1 → expected warehouse.
   - Compare с current Odoo warehouse.
4. Если match → продолжаю, тригерю 1217.
5. Если **mismatch** → **БЛОКЕР**:
   - Не тригерю 1217.
   - Phase A на лайны можно сделать (это OK, не зависит от warehouse).
   - Создаю activity для owner с pedido id + предложенным правильным warehouse.
   - В chatter post: «🚧 Address mismatch: paper говорит {paper_addr} → ожидаю warehouse {expected}, текущий {current}. Жду owner для смены picking_type или подтверждения».
6. Owner либо меняет picking_type через UI, либо подтверждает текущий → закрываю activity, тригерю 1217.

### 16.3 Datos fiscales ≠ Dirección entrega
**Не путать.** Verdnatura paper имеет два блока:
- **Datos fiscales** — регистрация ESPAFLORIA SL (всегда «MUNTANER 260, B19776897»). Это НЕ адрес доставки.
- **Dirección de entrega** — куда физически едут товары (Olimpic / Augusta / Gloria etc.). Это и есть наш target.

При парсинге paper берём именно «Dirección de entrega», игнорируем «Datos fiscales».

### 16.4 Multi-paper split (12439827-B/G/P)
Один paper разнесён на 3 albaran с разными dirección entrega — каждый на свой магазин (Blau / Gloria / Plaza). Алгоритм 16.2 применяется per albaran отдельно. (См. handover §13.5 — особый кейс через supervisor + owner.)

### 16.5 Retroactive check для уже закрытых pedidos
Pilot 12187009 закрыт на Blau (BLA/IN/00060). Paper dirección «C. OLIMPIC Castelldefels» = Blau. **Match ✅** (подтверждено owner 11.1).

---

## 17. Где смотреть всё в Odoo

После прохода 166 pedidos owner видит:
- **Список pedidos** (фильтр Verdnatura 2026)
- `state` колонка: filter draft / purchase
- `picking_ids[0].state`: assigned / done
- **Color бейдж** (через review_color на stock.move агрегированно): синий/зелёный/жёлтый/оранжевый/красный
- **Activities** (mail.activity todo) на каждом non-зелёном pedido
- **Чат-лента** (mail.message с author_id=56) на каждом pedido — 3-слойный лог

Список activities = пошаговый review queue для owner: идти, отмечать «принято» или давать решение.

---

## 18. Pedido-level visual status indicator (decision 2026-04-30)

**Owner verbatim:** «мне очень важно сразу легко понимать глядя на pedido или список pedido — закрыто всё зелёное / закрытое есть жёлтое-оранжевое / не закрыто (на склад не ушло, надо решать какие-то проблемы лично)».

### 18.1 Три уровня pedido-level status
| Бейдж | Условие | Что значит |
|---|---|---|
| 🟢 **Closed clean** | `state='purchase'` AND все `picking.state == 'done'` AND все `stock.move.x_studio_review_color in (10, 8)` (green/dark blue) | Закрыт, всё чисто, owner может игнорировать |
| 🟡 **Closed needs review** | `state='purchase'` AND все `picking.state == 'done'` AND **хотя бы один** `stock.move.x_studio_review_color in (3, 2)` (yellow/orange), но **нет красных** | Закрыт, но есть substantial fixes — ревью в activity |
| 🔴 **Not closed** | `state != 'purchase'` OR любой `picking.state != 'done'` OR любой `stock.move.x_studio_review_color in (1, 4)` (red/blue legacy «нужен ввод») | Не закрыт, физика на склад не ушла (или частично), нужно решать лично |

### 18.2 Implementation design
**Поле:** `purchase.order.x_studio_pedido_status` (selection: `green` / `yellow` / `red`) — **computed** через server action или Studio compute.

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

**Trigger обновления:** server action на `on_create_or_write` для `stock.move.x_studio_review_color` и `stock.picking.state`. Recompute parent pedido status.

**Visual:** kanban view конфиг — color-by `x_studio_pedido_status` (green=10, yellow=3, red=1 в Odoo color palette). Или badge widget в list view.

### 18.3 Implementation status (open work)
🔴 **Не реализовано** — это design note. Implementation требует:
1. Studio: создать selection field `x_studio_pedido_status` на `purchase.order`.
2. Server action компьютирующая статус (база.automation на изменение related stock.move.x_studio_review_color).
3. List view конфиг — colored badge / decoration по статусу.

Сделать **после batch reception** (пока 166 pedidos closed по алгоритму, status не критичен — owner идёт по activity queue). Потом implement field + view → owner видит полный список с бейджами один взглядом.

### 18.4 Workaround до implementation
Owner может использовать существующие Odoo фильтры:
- **Closed all clean (🟢):** filter `state='purchase'` + `activity_ids = []` (нет activity). Activities не создаются для зелёных-чистых pedidos (по §8.4).
- **Closed needs review (🟡):** filter `state='purchase'` + `activity_ids != []` (есть activity).
- **Not closed (🔴):** filter `state='draft'` OR `state='purchase'` AND `picking_ids[0].state != 'done'`.
