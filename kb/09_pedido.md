<!-- v: 8 | updated: 2026-05-10T00:00Z -->
# 09. Pedido — работа с purchase orders

**Что в файле:** домен `purchase.order` (закупки у поставщиков): источники, жизненный цикл, reconciliation paper PDF ↔ Odoo, action 1217 finalizer, supplierinfo learning, partner_id Verdnatura, Serviflor ChatGPT pipeline (§ 12). Reception_algorithm — главный artefact в `add/09_reception_algorithm.md`.

**Status:** 🟡 READY — 188 pedido draft в системе после Holded re-import (2026-05-02), все state=draft, supplierinfo=0. Ждут прогона через reception_algorithm + action 1217.

---

## 1. Что такое pedido

**Pedido** = `purchase.order` в Odoo (= заказ поставщику, исп. albarán/factura). Каждый pedido имеет:

- `partner_id` — поставщик (Verdnatura=42, Serviflor=39, Rillo=43, Decora=44, ParEx=57)
- `partner_ref` — vendor reference (номер документа поставщика)
- `name` — внутренний номер Odoo (`P00188` или Holded import format `Holded albaran id: AC260511 Vendor ref:12561164`)
- `order_line` — строки с product_id, qty, price
- `state` — `draft` / `sent` / `purchase` / `done` / `cancel`
- `picking_ids` — связанные `stock.picking` (приёмки)
- Custom поля: `x_studio_claude_finalize` (триггер action 1217)

---

## 2. Источники pedido

### 2.1. Holded import
Bulk import из Holded (старая ERP). После reset 2026-05-02 — **188 pedido импортированы**, все Verdnatura, state=draft. Lines заполнены price/qty/product_id из Holded ETL (через xlsx с External ID lookup `holded_<id>` для product.template + auto-generated `product.product` variant).

**Ограничения Holded import:**
- Нет цен в фактуре Verdnatura (цены в albaran отдельно) → Holded цены ненадёжны.
- Placeholder lines для unmatched SKUs (`product_id=10` «НОВЫЙ ТОВАР»).
- Holded amount=0 на некоторых lines (бухгалтер не заполнил).

### 2.2. Make.com Telegram bot — Route 1
Через бот OCR + LLM создаёт pedido с нуля если не найден по `(supplier_vat, document_number)`. См. [02_makecom_bot.md § 5.4](02_makecom_bot.md). Сейчас не используется для Verdnatura (все 188 уже импортированы), Route 1 — для новых поставщиков / новых документов.

### 2.3. Manual create
Через Odoo UI — для разовых закупок мелких поставщиков.

### 2.4. ChatGPT external prompt — Serviflor pipeline
Отдельный backfill-канал для Serviflor исторических events: оператор гоняет ChatGPT 5.5 Thinking по промту v9.1-lite, на вход — папка одного event (online order + Todas + factura PDF + bookkeeper workbook + Holded compras evidence), на выход — flat ZIP с `1_purchase_order_*.xlsx` (+ опц `2/3_internal_transfer_*.xlsx` если есть real movement) + `5_supplierinfo_learning_import.xlsx` + control report + русский Odoo chatter text. См. § 12 ниже.

---

## 3. Жизненный цикл pedido (Verdnatura)

```
draft (Holded import / bot Route 1)
   │
   ├─→ Reconciliation:
   │      • Make.com bot Route 2 — обогащает строки на price/qty/comment, учит supplierinfo
   │      • Reception_algorithm (Claude agent) — paper-truth reconciliation на основе PDF
   │
   ├─→ Phase A writes (price_unit / product_qty / x_studio_supplier_sku / x_studio_supplier_product_name / x_studio_expected_qty / x_studio_item_comment)
   │
   ├─→ x_studio_claude_finalize=True → action 1217 (через base.automation 15)
   │      • button_confirm() → state=purchase, создаёт picking
   │      • Phase A2 — quantity write на stock.move
   │      • Soft-gate (≤5 stems delta) → если OK, button_validate
   │      • Picking → state=done
   │      • Chatter summary + activity (если orange/yellow/red lines)
   │
   └─→ purchase + picking done = closed
```

**ROLLBACK ветка** (`note` содержит `ROLLBACK_HOLDED_API`) — откат закрытых-без-бумаги pedidos через `stock.return.picking`. См. [add/09_reception_action_1217.py](add/09_reception_action_1217.py).

---

## 4. Источник истины при reconciliation

**Paper PDF от Verdnatura = единственная истина** (см. [01_project § 4.1](01_project.md), [99_invariants](99_invariants.md)).

| Источник | Что брать | Что игнорировать |
|---|---|---|
| Paper PDF | refs, qty, price, IVA, total | — |
| Holded import (Odoo lines) | product_id (на какую карту положили), `x_studio_expected_qty` (физический recount бухгалтера) | price, line.name, supplier_sku — **ненадёжны** |
| Algorithm decisions | переписывает что нужно, оставляет что верно | — |

**Hard rule:** без скачанного paper PDF — **не закрываем** pedido. См. [add/09_reception_handover_2026-04-29.md § 2.1](add/09_reception_handover_2026-04-29.md).

**Где живёт paper PDF:** `pedido.files/reception_paper/verdnatura_<docNum>.pdf` (170 файлов, level above KB). Bulk attach через GitHub raw URL — см. [add/09_reception_INSTR_attach_pdf.md](add/09_reception_INSTR_attach_pdf.md).

---

## 5. Reception_algorithm — главный artefact

**Spec:** [add/09_reception_algorithm.md](add/09_reception_algorithm.md) (current **v20.1**, 🟢 PROD-ready) + [add/09_reception_algorithm_v1.md](add/09_reception_algorithm_v1.md) (v1 baseline, исторический, для сравнения).

**Содержит:**
- Per-line decision tree (paper-truth, MIX consolidate, pack/stem, ⛔ placeholder, ×N inflation)
- Card creation rules в карантине
- Trigger 1217 + verify
- Iconography (зелёный/жёлтый/оранжевый/красный/синий)
- Idempotency re-run safe

**Test runs** на одном pedido — через [add/09_reception_INSTR_test_run.md](add/09_reception_INSTR_test_run.md). Bulk-run через всё — отдельный promp ещё не написан.

### ⚠️ Red flag: ×N inflation > 2 — проверять pack/stem ПЕРЕД paper-truth

При дельте `Odoo_qty / paper_qty > 2` **НЕ применять paper-truth слепо**. Сначала:
1. Paper UD VENTA — содержит ли «Paquete»? Если да — paper qty в paquetes, не stems.
2. Odoo `product_uom` — какой unit на purchase.order.line (Tallo/Unidades vs Paquete id=31).
3. **Match check:** если paper UD=Paquete и Odoo unit=stem с совпадающим ratio (Odoo qty ≈ paper qty × stems_per_paq) — **Holded бухгалтер ПРАВ**, он раскрыл паки и пересчитал стебли. Не переписывай qty.

**Историческая ошибка:** SKIMMIA Yuki ×8 на pedido 12267946 (29 апреля 2026) — agent переписал Odoo qty с 40→5 «по paper-truth», получив × 8 inflation. На самом деле paper говорил 5 paquetes, Odoo бухгалтер забил 40 stems (ratio 8 stems/paq) — корректный recount после открытия паков. Применение paper-truth → склад остался с 5 stems вместо 40. Owner поймал, велел rollback.

Полный decision tree (4 ветви pack/stem) — в [add/09_reception_algorithm.md §A](add/09_reception_algorithm.md) «Pack-conversion alone» + §B detect pack/stem.

---

## 6. Action 1217 (`x_studio_claude_finalize`)

**Mirror:** [add/09_reception_action_1217.py](add/09_reception_action_1217.py).

**Триггер:** `purchase.order.x_studio_claude_finalize=True` через `base.automation 15` с фильтром `state in ['draft', 'purchase']`.

**Три ветки:**

| Ветка | Условие | Что делает |
|---|---|---|
| **ROLLBACK** | `note` содержит `ROLLBACK_HOLDED_API` | `stock.return.picking` wizard, откат stock.move |
| **CONFIRM** | state=draft | `button_confirm()` → picking создаётся в `assigned` |
| **VALIDATE** | state=purchase + picking exists | Phase A2 quantity write + soft-gate + `button_validate()` |

**Soft-gate:** дельта между paper qty и Odoo qty по строке ≤ 5 stems = auto-OK. > 5 — review_status≠OK → блок Validate.

### ⚠️ Ограничения 1217

- **Не работает на `state=purchase`.** Pre-flight жёстко проверяет `state=='draft'`. Если pedido частично подтверждён (Phase A прошла, picking создан, но gate отвалил) — flip flag не помогает. Нужен либо ручной Validate в UI, либо отдельный «validate-only» server action.
- **Не различает minor variance.** Final gate отвергает любой `x_studio_review_status` кроме префикса `OK*`. Параллельная automation 1146 пишет «от бумаги ±N» при дельте — gate стоит насмерть. Workaround: для minor variance (≤ 2 stems) Phase A пишет `x_studio_expected_qty=paper_qty` чтобы gate не запутался.
- `safe_eval` ограничения: нет `STORE_ATTR`, `hasattr`, `__name__` — везде используется `.write({})` вместо attribute set.

---

## 7. Reconciliation: bot vs algorithm

| Канал | Когда | Артефакты |
|---|---|---|
| **Make.com bot Route 2** | Online: новый PDF приехал в Telegram, обогащает existing pedido | [02_makecom_bot.md](02_makecom_bot.md), [add/02_prompt_reconciliation_v3.5.txt](add/02_prompt_reconciliation_v3.5.txt) |
| **Reception_algorithm (Claude agent)** | Bulk reconciliation 2026 backlog, 188 Holded-imported pedidos, paper PDF на диске | [add/09_reception_algorithm.md](add/09_reception_algorithm.md) |

Оба используют общие принципы (см. [02_makecom_bot § 2 Reconciliation principles](02_makecom_bot.md)) — learned vendor codes, operator hits, identity safety > coverage, paper-truth для qty/price.

---

## 8. Кастомные поля pedido

### 8.1 На `purchase.order.line` (5 полей)

Заполняются ботом / агентом во время reconciliation:

| Поле | Тип | Назначение |
|---|---|---|
| `x_studio_expected_qty` | float | Оценка логиста / физический recount бухгалтера |
| `x_studio_item_comment` | char | Лог reconciliation от бота (см. [02_makecom_bot § Line-log шаблоны](02_makecom_bot.md)) |
| `x_studio_operator_hit` | char | Ручная подсказка для LLM-reconciliation |
| `x_studio_supplier_product_name` | char | Название с бумаги (заполняется ботом) |
| `x_studio_supplier_sku` | char | SKU с бумаги (заполняется ботом) |

**Удалено:** `x_studio_expected_qty_2` (мусорное).

### 8.2 На `purchase.order` (header)
- `x_studio_claude_finalize` (bool) — триггер action 1217.

### 8.3 На `stock.move` (related fields, 9 штук)
См. [03_inventory_pipeline § 2](03_inventory_pipeline.md) — это уже stock-side слой приёмки.

---

## 9. Bill control policy

См. [03_inventory_pipeline.md § 6](03_inventory_pipeline.md):
- **Цветы / горшечка** (FLORES CORTADAS, PLANTAS EN MACETAS) → `purchase` (On ordered quantities) — платим по бумаге, расхождения «49 из 50» норма.
- **Остальное** → `receive` (On received quantities).

Применено к ~900 карточкам цветочных категорий 2026-04-18.

---

## 10. Партнёр Verdnatura

**`partner_id = 42`** (НЕ 23 — 23 это посторонняя запись «Washington State Department of Social and Health Services», у неё 0 supplierinfo). После reset id сохранён.

**`VERDNATURA LEVANTE SL`**, испанский поставщик, factura в EUR, IVA 10% G на цветах.

---

## 11. Открытое

| # | Что | Статус |
|---|---|---|
| 11.1 | Bulk-run reception_algorithm через все 188 pedidos | 🟡 (готов supervisor prompt — pilot 2-3 pedido → batch) |
| 11.2 | Сравнение algorithm v1 vs v19 → выпуск v20 | ✅ done 2026-05-03 (v20 в проде) |
| 11.3 | Bulk attach paper PDF к pedido (post-reset) | 🟡 готов INSTR |
| 11.4 | Make.com bot Route 1 modernization (дубль-check, learned codes) | 🔴 |
| 11.5 | OLD_ SKU awareness в bot для исторических pedido | 🔴 |
| 11.6 | Multi-warehouse split одного albarán | 🔴 (custom) |
| 11.7 | **Post-bulk vendor price audit** (после full bulk Verdnatura ~167 pedido) — single subagent run: пройти все templates с >1 supplierinfo Verdnatura, применить scaled threshold (avg<3€ → ratio≤2.5+abs≤1.5; <8€ → 1.7+3; <20€ → 1.4+5; >20€ → 1.25+10), flag suspicious через `mail.activity` на template + `@Andriy` mention. Owner идёт по полкам / открывает activities → решает split / keep на каждой. Это catch-up на bookkeeper miss-matches которые subagent не отловил. | 🔴 (after bulk done) |
| 11.8 | Serviflor 2 заблокированных events (28 апр factura 2874 + credit note 2971; 5 мая factura 3031) — нет workbook бухгалтера. Решение: **#13 (28 апр)** — догон в Mode A через Flora-файл (логист+флористы) как заменитель bookkeeper workbook; **#14 (5 мая)** — пилот нового workflow Mode B без бухгалтера. | 🟡 в работе (см. § 13) |
| 11.9 | Retro-fix 11 Serviflor TMP/INT pickings → правильные per-warehouse picking_types (16/25/34 по source location) | ✅ done 2026-05-08 (server action 1234, SQL UPDATE bypass constraint state=done; 130 связанных stock.move согласованы; Temporal warehouse 5 оставлен активным как garbage bucket; см. [99_invariants G12 + G13](99_invariants.md)) |

---

## 12. Serviflor pipeline (ChatGPT v9.1-lite)

### 12.1. Зачем отдельный pipeline
У Serviflor **нет стабильного supplier `codigo`** на товарах — на новой поставке тот же физический товар может прийти с другим VBN (другой производитель на аукционе). Make.com бот учит supplierinfo по `(partner, codigo)` → у Serviflor этот ключ не стабильный, прямой матч по нему опасен (попадание в чужую карту).

`Codigo de fabricacion` у Serviflor — **нестрогий**: список кодов через запятую, trace-ID партии, иногда пусто, иногда повторяется на разных товарах. Примеры: `0027, 11920, 146548, ...` или `RANUBUL, RANUBUSA, ...`. Это **не строгий SKU**.

Решение — 4-уровневая модель идентификации:
- **Supplier Product Name** — человекочитаемое имя + атрибуты (color, origin, grower, height, pot, pack info)
- **Supplier Codigo** — **только если** реальный reusable supplier code; если у Serviflor только trace-ID — оставляем пустым
- **Supplier Identity Key** — композитный semantic ключ для recognition memory: `SV|ART:<name>|COLOR:<c>|ORIGIN:<co>|GROWER:<g>|POT:<p>|HEIGHT:<h>|QUALITY:<q>|PIECES_UNIT:<pu>|UNITS_PER_PACK:<up>|PACK_MODE:<PACK|UNIT>|ATTR:<...>`. Главный ключ matching.
- **Supplier Lot Code** — trace конкретной поставки (factura row + online row + entrega + stockline ID), не reusable

**Анти-правило:** не засорять `Vendor Product Code` нестрогим `Codigo de fabricacion` — иначе ложные matches и каталог раздувается.

Исторически Serviflor backfill 12/14 events шёл **внешним ChatGPT-каналом** (не через Make.com бот). Промт-снимок v9.1 — [add/09_serviflor_chatgpt_prompt_v9.1.txt](add/09_serviflor_chatgpt_prompt_v9.1.txt). После окончания «бухгалтер-era» **этот pipeline закрыт**, повторно не используется. Дальнейшая работа — см. § 13 «Новый workflow без бухгалтера».

### 12.2. Pipeline event-by-event
**Вход** (одна папка на event):
- Serviflor online order XLSX (placed-order evidence)
- Serviflor Todas XLSX (опц., processing/fulfilment evidence)
- Factura PDF + опц. credit note (commercial payable truth)
- Bookkeeper workbook XLSX (SKU-mapping + bought packs + units per pack + actual recount + Plaza/Gloria/Blau split + primary warehouse evidence)
- Holded Compras evidence XLSX (опц., accepted/SKU evidence)

**Reference data** (одни и те же на все events) — `pedido.files/serviflor/`:
- `Compras Exportar items-2025.xlsx` + `-2026.xlsx` — Holded Compras export
- `Product Variant (product.product)-2.xlsx` — Odoo product.product catalog
- `Supplier Pricelist (product.supplierinfo)-4.xlsx` — known supplierinfo
- `odoo-pedido - serviflor.csv` — already-imported pedido список (anti-duplicate guard)
- `serviflor_compras_2025_selection_analysis.xlsx` + `-2026` — выборки compras
- `serviflor_event_index.xlsx` — master index 14 events со статусом

**Выход** (flat ZIP, прямо в attachment Pedido):
- `1_purchase_order_<warehouse>_import.xlsx` — clean PO import
- `1b_purchase_order_line_price_fix.xlsx` — second pass price enforcement (v9.1 hardening)
- `2_internal_transfer_*_to_*.xlsx` — только если real movement primary→другие магазины
- `3_internal_transfer_*_to_*.xlsx` — то же
- `4_import_control_summary.xlsx` — lightweight control report
- `5_supplierinfo_learning_import.xlsx` — learned supplierinfo с composite Identity Key
- русский Odoo chatter text для копи-пасты в pedido log

### 12.3. Жёсткие гейты v9.1
- Factura PDF = payable truth, workbook не override.
- `Order Lines/Unit Price` → `order_line/price_unit` (hard blocker если mapping иной).
- `/Database ID` колонки только numeric (Tallo=1, Paquete=31; tax 68=10%G, 7=21%G).
- Dynamic primary receipt warehouse — НЕ всегда Plaza, выводится из workbook/Compras evidence.
- Pack vs Unit per-line classification без silent guess (uncertain → 🟠 review).
- Excel PASS ≠ Odoo PASS — после import обязательная visual проверка Odoo line Amount = factura subtotal.
- Two-step price enforcement: после import основной PO применяется 1b file для перезаписи цен (защита от Odoo onchange recalculation).

### 12.4. Status backlog (на 2026-05-08)

**14 events identified** (период Dec 2025 → 5 мая 2026). См. `pedido.files/serviflor/serviflor_event_index.xlsx`.

**Импортировано: 12/14** ([cross-check Odoo](https://espafloriasl.odoo.com/odoo/purchase) — все 12 в `state=purchase`, 13 internal transfers Done):

| # | Event | Factura | Pedido ID | Odoo amount_untaxed | Paper base | Match |
|---|---|---|---|---|---|---|
| 1 | 2025-12-11 | 7630 | 48708 | 306.22 | 306.22 | ✅ |
| 2 | 2025-12-18 | 7893 | 48719 | 553.42 | 553.42 | ✅ |
| 3 | 2026-01-06 | 81+113 | 48874 | 2142.73 | 2165.73 | ⚠ Δ 23€ partial fulfilment |
| 4 | 2026-01-08 | 128 | 48888 | 748.90 | 748.90 | ✅ |
| 5 | 2026-01-15 | 238 | 48908 | 993.65 | 993.65 | ✅ |
| 6 | 2026-01-22 | 358 | 48937 | 1858.64 | 1858.64 | ✅ |
| 7 | 2026-01-28 | 494 | 48957 | 782.54 | 782.54 | ✅ |
| 8 | 2026-02-26 | 1137 | 48979 | 1675.94 | 1675.94 | ✅ |
| 9 | 2026-03-10 | 1369 | 49008 | 1643.31 | 1643.31 | ✅ |
| 10 | 2026-03-12 | 1461 | 49023 | 886.32 | 886.32 | ✅ |
| 11 | 2026-03-26 | 1797 | 48628 | 1905.35 | 1905.35 | ✅ |
| 12 | 2026-04-07 | 2057 | 49040 | 1065.20 | 1065.20 | ✅ |

**Заблокировано: 2/14** (нет workbook бухгалтера):
- **#13 — 2026-04-28, factura 2874 + credit note 2971** (1838.07€ base / -117€ correction)
- **#14 — 2026-05-05, factura 3031** (2362.28€ base)

Решение для 2 заблокированных — см. [§ 11.8](#11-открытое). Варианты: (a) workbook постфактум от бухгалтера; (b) production import без split (один primary warehouse по факту разгрузки, без transfer-перебросов, recount = paper qty); (c) оставить в Holded read-only, не догонять — оплата уже прошла банком. Owner-выбор до cutover.

### 12.7. Temporal warehouse как garbage bucket (осознанная фича)

`stock.warehouse` id=5 «Temporal» (code=TMP) держится активным как **сборник проблемных кейсов**:
- Orphaned `stock.move` с `picking_id=False` от Verdnatura retro-fix'ов (когда Odoo не даёт менять uom/qty на done move — старая move обнуляется и создаётся новая с правильным uom; старая остаётся orphaned). На 2026-05-08 — 19 таких moves, все `location_dest_id=TMP/Stock`, продукты с префиксом 🚫.
- Будущие cleanup-кейсы которые временно нужно куда-то «убрать» до разбора.

**Не архивировать.** К концу дня условно должно быть пусто, но если что-то там лежит — это видимый сигнал «есть незакрытый кейс».

**Anti-pattern:** не использовать TMP как способ обойти proper workflow. Это последний resort, не стандартный канал.

### 12.5. Operator workflow (один event)

[Архивный режим — не повторяется. Текущий workflow — § 13.]

1. Подготовить папку event (5 поддиректорий: online_order/, processed_todas/, factura/, bookkeeper_workbook/, holded_compras_evidence/).
2. ChatGPT 5.5 Thinking → загрузить промт v9.1 + reference data + папку event.
3. Получить ZIP — открыть `4_import_control_summary.xlsx` + русский chatter text.
4. Если 🔴 blockers — стоп, разбираться. Если 🟠 reviews — owner-decision.
5. Если 🟢/READY — Odoo Settings → Import → загрузить `1_purchase_order_*.xlsx`.
6. Сразу следом — `1b_purchase_order_line_price_fix.xlsx` (перезаписать цены).
7. Visually verify: Odoo line Amount = factura line subtotal на каждой payable строке.
8. Если есть transfers — загрузить `2_*` и `3_*` (Inventory → Operations → Transfers import).
9. Загрузить `5_supplierinfo_learning_import.xlsx` (Purchase → Vendor Pricelists import).
10. На созданном Pedido в chatter — paste русский summary + attach factura PDF + workbook + ZIP.
11. Подтвердить PO (`button_confirm`), validate picking. По умолчанию это делается в pedido вручную, потому что Serviflor backfill идёт без `x_studio_claude_finalize=True` (это для Verdnatura reception_algorithm).

---

## 13. Новый workflow Mode B — pedido recognition без бухгалтера

**Status:** 🟡 в проектировании на 2026-05-08. Pilot на event #13 (Serviflor 28 апр factura 2874) — pedido P14636, draft state, ждёт review логиста и confirm. Полная Make.com бот реализация — отдельная инициатива (см. § 13.9 Roadmap).

### 13.1. Контракт workflow

**Вход** (любой из вариантов):
- Verdnatura: paper PDF (albarán) + опц. factura PDF
- Serviflor: factura PDF + online order XLSX + опц. Todas XLSX (split files)
- Любой поставщик: factura PDF минимум

**Выход** — `purchase.order` в `state=draft` со всеми lines pre-filled, готовый к review логистом:
- Каждая factura-line → `purchase.order.line`
- `product_id` = best-guess карта Odoo (4-уровневый matching — § 13.3)
- Studio metadata fields populated (см. § 13.6)
- `x_studio_match_confidence` per line (confident/probable/candidates/create_new) — цвет статуса
- `x_studio_alternative_cards` — список кандидатов для cycling
- `x_studio_supplier_photo_url` — URL фото поставщика для визуальной проверки
- `x_studio_item_comment` — reasoning текст с переносами строк (см. § 13.8 формат)
- Логист открывает pedido → review через Alt/New кнопки + photo pair → confirm.

### 13.2. Стадии распознавания

1. **Parse supplier files**: text extraction из PDF (если text-PDF) или OCR (если image PDF). XLSX через openpyxl. Photo URLs из hyperlinks в Todas xlsx.
2. **Build composite identity** для каждой factura-line — composite key formula в § 13.3.
3. **4-tier matching** — § 13.3.
4. **Score → confidence**:
   - L1 hit (existing supplierinfo с identity key match) → `confident`
   - L2 hit (active 2026 pool, semantic match high score) → `probable` или `confident`
   - L2/L3 multiple competing matches → `candidates` + populate `alternative_cards`
   - No match anywhere → `create_new`
5. **Photo URL construction** — § 13.4
6. **Build factura_lot_code** для trace: `Factura: NNNN/YYYY row N | Entrega: ... | Online: ... row N | Stockline: ...`
7. **Generate item_comment** с переносами строк (§ 13.8)
8. **Create pedido in Odoo** — via MCP create_record × N lines (или import xlsx если pipeline через бот)

### 13.3. Identity matching algorithm

**Composite key format** (per supplier prefix):
```
SV|ART:<NORMALIZED_NAME>|COLOR:<c>|ORIGIN:<co>|GROWER:<g>|HEIGHT:<h>|POT:<p>|PIECES_UNIT:<pu>|UNITS_PER_PACK:<up>|PACK_MODE:<PACK|UNIT>|ATTR:<...>
```

VN| для Verdnatura, SV| для Serviflor. Хранится в `product.supplierinfo.x_studio_supplier_identity_key`.

**4-уровневый matching pyramid** (по убыванию надёжности):

**L1 — Learned identity:**
- Search `product.supplierinfo` где `partner_id=vendor` AND `x_studio_supplier_identity_key` совпадает (exact или fuzzy с small edit distance)
- Hit → берём `product_id` оттуда. Confidence = `confident`.

**L2 — Active 2026 pool:**
- Pool = unique `product.product` появлявшиеся в `purchase.order.line` за 2026 год (любой поставщик)
- Score formula: ART exact match=100, word overlap×5+50, 1-word overlap=20
- Bonus: color match +10, height ±5cm match +5, origin match +5
- Top score >= 60 → confident. >= 30 → probable. < 30 → candidates с top 2-3.

**L3 — Wider quarantine search:**
- Если L2 не дал → расширяем до всего `categ_id child_of 207 (Карантин Holded)` + `child_of 287 (Flores Cortadas)`
- Тот же scoring но threshold 30 → candidates всегда.

**L4 — No match → `create_new`:**
- Не нашли вообще → mark `x_studio_match_confidence='create_new'` + `x_studio_alternative_cards=[product_id_default_placeholder]`

**Anti-rules:**
- НЕ матчить по supplier `codigo` напрямую (§ 12.1 — нестрогий)
- НЕ overwrite ручную правку логиста (если он уже выбрал — не пересчитывать)
- При сомнениях → `candidates` лучше чем wrong `confident`

### 13.4. Photo URL patterns (для supplier_photo_url field)

**Serviflor** (через FloraPlaza CDN):
- Generic by VBN: `https://img.floraplaza.nl/?f=ART_fotos%5CVBN%5Cvbn{VBN}.jpg`
- Specific lot photo (если supplier дал в Todas): `https://img.floraplaza.nl/?f=LIVE_fotos%5C0x{HASH40}.jpg`
- **Source extraction**: hyperlink из Todas XLSX колонки `Photo` (текст ячейки = «Photo», hyperlink target = реальный URL — используй openpyxl `cell.hyperlink.target`)
- Fallback: если Todas нет — конструировать generic pattern по VBN online order

**Verdnatura**:
- Pattern: `https://cdn.verdnatura.es/image/catalog/1600x900/{default_code}`
- Source: `default_code` (SKU) товара в Odoo карте

**Display**:
- `x_studio_supplier_photo_url` — Char field, raw URL
- `x_studio_supplier_photo_html` — Html computed field, оборачивает URL в `<img max-width:100% max-height:128px object-fit:contain>` для inline preview в tree row

### 13.5. Logist review UI в pedido form

Tab «Products» в pedido form — `purchase.order.line` tree view. Customizations в `ir.ui.view id=4467`:

**Колонки (слева направо)**:

| # | Column | Покажет | Когда видно |
|---|---|---|---|
| 1 | Product | product_id (default карта от агента) | always |
| 2 | Our photo | image_128 from product card | always |
| 3 | New + (red `btn-danger`) | кнопка create-from-supplier | only `confidence='create_new'` |
| 4 | New + (grey `btn-secondary`) | кнопка create (с confirm dialog) | when `confidence != 'create_new'` |
| 5 | Alt → (yellow `btn-warning`) | кнопка cycle через alternatives | when `pick_position != ''` (alternatives > 1) |
| 6 | Alt | "1/2", "2/2" — позиция в cycle | when alternatives > 1 |
| 7 | URL | supplier_photo_url (clickable) | always |
| 8 | Supplier photo | inline image от поставщика (computed HTML) | always |
| 9 | Comment | item_comment_text (computed text mirror, multiline word-wrap) | always |
| 10 | Match badge | confidence (color-coded: green/yellow/red/blue) | optional=hide (toggle) |
| 11 | Alternatives tags | many2many tags список кандидатов | optional=hide (toggle) |

**Логист actions**:

- **Photo pair** (Our photo + Supplier photo) — визуальная сверка «правильно ли заматчили». Если визуально совпадает → confidence ОК.
- **Alt → click** — server action 1236 cycles `product_id` через `x_studio_alternative_cards` без изменения qty/price (server-side write минует product_id onchange). Counter `Alt` обновляется.
- **New + click (grey)** — confirm dialog «Нужна ли действительно новая карта? Попробуй сначала Alt». Если ОК → server action 1239 (Step 3, реализован). Защита от случайного создания дубликатов.
- **New + click (red)** — для статуса `create_new`. Без confirm, сразу триггерит 1239.
- **New + click (red)** — то же действие, но цвет красный сигнализирует «агент рекомендует новую карту, alternatives нет/не подходят».

### 13.6. Studio fields catalog

На `purchase.order` (header):

| Field | Type | Store | Default | Purpose |
|---|---|---|---|---|
| `x_studio_view_mode` | Selection | True | `'logist'` (`ir.default 34`) | Role-based view mode toggle: `logist` / `bookkeeper`. **Только видимость полей**, не permissions и не данные. См. § 13.12 |
| `x_studio_claude_finalize` | Boolean | True | False | Trigger checkbox для action 1217 finalize (см. § 6) |

На `purchase.order.line` добавлены 2026-05-08 для Mode B:

| Field | Type | Store | Purpose |
|---|---|---|---|
| `x_studio_match_confidence` | Selection | True | `confident` / `probable` / `candidates` / `create_new`. Источник истины — agent/Make.com bot после matching |
| `x_studio_alternative_cards` | M2M → product.product | True | **Список кандидатов** по композитному identity key (включая текущий `product_id`). Заполняется agent'ом/ботом при `probable`/`candidates`. Action 1236 (Alt →) циклит через этот список. Удалить = сломать Alt button |
| `x_studio_pick_position` | Char (computed) | False | "1/2" / "2/2" — индекс текущего product_id в alternative_cards. Пустая строка для `len(alternatives) <= 1`. Используется в `invisible` Alt button |
| `x_studio_supplier_photo_html` | Html (computed) | False | Wraps `x_studio_supplier_photo_url` в `<img>` для inline preview в tree (widget="html") |
| `x_studio_our_photo` | Binary (related → `product_id.image_128`) | False | Превью **нашей** карты product_id. Не путать с supplier_photo* |
| `x_studio_item_comment_text` | Text (computed mirror char `x_studio_item_comment`) | False | Read-only multiline mirror для word-wrap в tree (widget="text"). Источник правды = `x_studio_item_comment` (writable char) |

Pre-existing (от ChatGPT v9.1 промта supervisor'а / Make.com bot output):

| Field | Type | Semantic |
|---|---|---|
| `x_studio_supplier_product_name` | Char | Полное человеко-читаемое название как **поставщик** его передал. Пример: «Codiaeum vari Mrs Iceton \| MX \| h=19 \| pot small» |
| `x_studio_supplier_sku` | Char | SKU/codigo **поставщика** для конкретной line (Verdnatura `default_code`, Serviflor VBN/Artikel) |
| `x_studio_supplier_lot_code` | Char | **Trace** на конкретный lot/факту/entrega поставщика (например `factura 002874/2026 → entrega 12345 → row N`). Используется для history/dispute, не для matching |
| `x_studio_supplier_photo_url` | Char | **URL** картинки на CDN поставщика для **этой конкретной line** (не на template-уровне, не наш сайт). Сейчас источники: Serviflor → FloraPlaza CDN (`https://img.floraplaza.nl/?f=ART_fotos%5CVBN%5Cvbn{VBN}.jpg`), Verdnatura → `https://cdn.verdnatura.es/image/catalog/1600x900/{default_code}`. **Не массив, одна ссылка.** Может быть пустым если bot не нашёл photo. Логист использует для визуального match через `x_studio_supplier_photo_html` |
| `x_studio_item_comment` | Char | **Writable** агентский comment (reasoning + recommendation). Format § 13.8 |
| `x_studio_expected_qty` | Float | Bookkeeper recount (paper-truth). Sums to total in tree |
| `x_studio_operator_hit` | Char | Operator hint (например ground truth from Make.com line-log) |

Identity key field — на `product.supplierinfo`:
- `x_studio_supplier_identity_key` (char) — composite key formula `<vendor>|ART:<artikel>|COLOR:<color>|...`, см. § 13.3 + § 13.9.

### 13.7. Server actions

| ID | Name | Trigger | Purpose |
|---|---|---|---|
| 1236 | Cycle to next match | tree button on line | rotates `product_id` через `alternative_cards`. **Не** меняет confidence. **Не** триггерит product_id onchange (preserves qty/price/taxes/uom). |
| 1237 | Verify match (mark confident) | unused | обнавливает `match_confidence='confident'`. Не используется в текущей UI. |
| 1239 | Create card from supplier | tree button on line | **Implemented (Step 3)** — создаёт `product.template` (auto-variant) в категории `⛔ Карантин Holded` (id=207), SKU = next free `8400xxx`, cost=line.price_unit, list_price=cost×3, taxes_id=82 (sales 10% R), supplier_taxes_id=68 (purchase 10% R), Holded Link = supplier_photo_url, supplierinfo с composite identity key, back-link через chatter на pedido + на новой карте, `mail.activity` TODO «Загрузить фото и проверить карту» deadline +7 дней. После create открывает форму карты в modal. **Фото загружается вручную** — auto-fetch URL→image_1920 невозможен на Odoo Online (см. §13.10). |
| 1240 | Migrate item_comment char→text | unused | Не понадобилась — финальное решение через computed text mirror. |
| 1242 | Set view: Logist | header button | `record.write({'x_studio_view_mode': 'logist'})`. См. § 13.12 |
| 1244 | Set view: Bookkeeper | header button | То же для `'bookkeeper'`. См. § 13.12 |
| 1234 | Retro-fix Serviflor TMP/INT | executed 2026-05-08 | One-shot, выполнен. |

**Удалено 2026-05-09:**
- Field `x_studio_pick_choice` (M2O legacy, id 27786) — заменён cycle button
- Server action 1235 «Swap product on pick_choice change» — зависел от удалённого field
- Server action 1243 «Set view: Buyer» — Buyer mode merged в Logist (см. § 13.12)
- `base.automation 16` (Pick choice swap) — деактивирована ранее, после удаления field тоже потеряла смысл

### 13.8. item_comment formatting rule

Бот / агент / любой источник item_comment должен писать **с `\n\n` (двойной перенос) между смысловыми блоками**:

```
🟢/🟡/🟠/🔴 STATUS: краткий summary одной строкой

Reasoning:
- bullet 1
- bullet 2

Альтернатива: ...

Logist decide.
```

**НЕ** писать всё одной строкой. Comment column в tree рендерится через `widget="text"` с word-wrap — multiline воспринимается читаемо.

Цветовые маркеры в начале:
- 🟢 OK = confident match, action не нужен
- 🟡 OK = probable, визуальная проверка по photo
- 🟠 REVIEW = candidates, цикли через Alt
- 🔴 (или 🚧) = create_new или blocker

### 13.9. Step 3 — Create card from supplier (реализовано 2026-05-08)

Server action 1239 на pedido.line button. Полная цепочка:

**Что делает:**
1. **Name** — из `line.name`, с префиксом `🚧🟠 <name> (auto-created)` чтобы было видно карты-черновики в каталоге.
2. **SKU (`default_code`)** — scan существующих `8400xxx`, берём next free integer. Карантинная band 84000000-84099999 зарезервирована под auto-created карты.
3. **Category** — `⛔ Карантин Holded` (id=207). Все новые карты падают сюда независимо от типа товара. После Step 6 (clean catalog hierarchy) — переключиться на категоризацию по keywords.
4. **Pricing** — `standard_price = line.price_unit`, `list_price = cost × 3` (наценка по дефолту, флорист поправит).
5. **Taxes** — `taxes_id=[82]` (sales 10% R), `supplier_taxes_id=[68]` (purchase 10% R). Hardcoded для цветов; при категоризации не-цветочной продукции — поправить вручную.
6. **Holded Link (`x_studio_holded_url`)** — переиспользуем существующее поле под supplier_photo_url. Это URL картинки на CDN поставщика (Serviflor FloraPlaza или Verdnatura cdn.verdnatura.es). Логист открывает Link → правый клик → Save Image → upload в product image на форме.
7. **Supplierinfo** — создаётся запись `product.supplierinfo` с `partner_id=line.partner_id`, `price=line.price_unit`, `product_code=line.x_studio_supplier_identity_key` (composite SV|ART|COLOR|...), `product_name=line.name`. Это и есть «обучение» — при следующих pedido та же L1 запись подхватит карту автоматически.
8. **Привязка к line** — `line.product_id = new_template.product_variant_id.id`, `line.x_studio_match_confidence='confident'`. **Не** триггерит product onchange (preserves qty/price/taxes на line).
9. **Back-link** — `mail.message` чаттер пост на pedido (с link на новую карту) и на новой карте (с link на pedido + WHY/SOURCE/PRICING). Trace «откуда пришла карта».
10. **Activity TODO** — `mail.activity` с deadline +7 дней «Загрузить фото и проверить карту» назначается логисту. Чтобы карта не оставалась с placeholder image.
11. **Open form** — после create возвращаем `ir.actions.act_window` `target='new'` (modal popup) на новую карту чтобы логист сразу мог подправить.

**Composite identity key (Supplier Identity Key)** — формат:
```
SV|ART:<artikel>|COLOR:<color>|ORIGIN:<origin_code>|GROWER:<grower>|HEIGHT:<height>|POT:<pot>|PIECES_UNIT:<n>|UNITS_PER_PACK:<n>|PACK_MODE:UNIT
```
Все поля опциональны (если поставщик не передал — пропускается). Ключ детерминированный → один и тот же товар у поставщика всегда даёт один и тот же key → одна supplierinfo запись → 1:1 mapping в L1.

### 13.10. Photo storage — manual upload only

**Auto-fetch URL → image_1920 на Odoo Online: невозможно.** Все пути упираются:
- `safe_eval` server actions не пускают `import requests` / `import urllib` (`Forbidden opcode IMPORT_NAME`).
- `base_import.execute_import` ожидает base64 в `image_1920`, не URL — даёт `Incorrect padding` exception.
- Прямая запись URL string в `image_1920` не триггерит fetch (поле бинарное, ждёт bytes).
- Custom JS widget — нет на Online.
- Custom Python module — нет на Online (только Odoo.sh).

**Текущий workflow (manual):**
1. Server action 1239 пишет supplier_photo_url в `x_studio_holded_url`.
2. Логист открывает форму карты (она открывается автоматически в modal).
3. Кликает на Holded Link (`widget="url"` → ссылка кликабельная) → открывает картинку в новом tab.
4. Save image → drag&drop в image-zone карты product → Save.
5. После выгрузки внешнего хостинга → картинка хранится локально в Odoo навсегда.

**Будущий путь (Make.com бот, Step 4):** Бот при создании pedido draft заранее fetch'ит supplier_photo_url → base64 → записывает в `x_studio_supplier_photo_b64`. Server action 1239 при create декодирует base64 → image_1920 (это safe_eval разрешает: `b64decode` доступен через `base64` module если он whitelisted, иначе через работу с bytes напрямую). Итог: zero-click card creation с фото.

### 13.11. Roadmap — что построить далее

**Step 4 — Make.com бот integration** 🔴
- Route 1 (current OCR + reconciliation) дополнить:
  - Для Serviflor: parser xlsx (online + Todas) + extract photo URLs из hyperlinks
  - Для всех: composite identity key construction
  - 4-tier matching algorithm (адаптировано из ChatGPT v9.1 + § 13.3)
  - Output: pedido draft state с populated Studio fields
- Route 2 (existing line-log) — оставить как есть для accept/recount после приёмки

**Step 4.5 — Distribution UI inside Odoo** 🔴 (deferred)
- Сейчас распределение **по магазинам** (Plaza/Gloria/Blau qty per line) делается **вне Odoo** через Flora-xlsx workbook (логист собирает, шаблон в `pedido.files/serviflor-бухгатер-chatgpt/_final4/<event>/Flora_*.xlsx`).
- Флора-файл = `(VBN, Артикул, Цвет, Высота, Длина, Origin, Фото, Связок, шт./связке, Всего шт., Подсказка, → Plaza, → Gloria, → Blau, Остаток)`. «Остаток=0» = perfect distribution; ненулевой = нераспределено / партия пришла не полностью.
- Перенос в Odoo требует: 3 Studio Integer fields per line (`x_studio_qty_plaza/gloria/blau`), constraint sum = expected_qty, color на остатке, экспорт в xlsx для floriste-команды (которая распределяет фактически в магазине).
- **Решение:** оставить external xls workflow до запуска Make.com бота (Step 4). Distribution UI делаем когда уже есть стабильный pedido draft → recognition pipeline.

**Step 5 — Inline form view** 🟡
- Click на pedido.line → modal с large photos, dropdown alternatives, prominent confidence, full comment
- Нужен если tree view UX окажется ограниченным на production scale (>50 lines per pedido)
- Сейчас не критичен — tree-list работает приемлемо

**Step 6 — Catalog hierarchy** 🔴
- См. § 58 в KB обсуждениях. Нужна перед запуском POS.
- Чистая иерархия категорий (Flores Cortadas / Plantas / Accessories с подкатегориями)
- Migration script для top-N карт из карантина
- После → Step 3 «Create from supplier» использует новую иерархию для категоризации

### 13.12. View mode toggle (role-based field visibility)

Pedido форма физически проходит **2 роли** последовательно:
1. **Логист** (= matching + distribution): сматчить продукты, разнести по магазинам через external Flora-xls.
2. **Бухгалтер**: проверить суммы / налоги / payment terms, провести в учёт.

(Третья роль «Распределитель» merge'нута в Logist — distribution делается тем же человеком сразу после matching, см. Step 4.5 deferred.)

Каждой роли нужна своя «оптика» — без шума от полей другой роли. Реализовано через **Selection field + button toggle + column_invisible expressions**.

#### 13.12.1. Архитектура

| Компонент | ID | Что делает |
|---|---|---|
| Selection field `x_studio_view_mode` на purchase.order | 27797 | `'logist'` / `'bookkeeper'`, default `'logist'` (`ir.default 34`) |
| Server action «Set view: Logist» | 1242 | Header button → `write({'x_studio_view_mode': 'logist'})` |
| Server action «Set view: Bookkeeper» | 1244 | То же для `'bookkeeper'` |
| 2 кнопки в header view 4467 | — | Текущий mode = `btn-primary` синий, остальной = `btn-secondary` серый. Click → server action → form reload |

При создании новой pedido автоматически берётся `'logist'` (через `ir.default`).

#### 13.12.2. Какие колонки скрыты в Bookkeeper mode

Через `column_invisible="parent.x_studio_view_mode == 'bookkeeper'"`:

- `x_studio_our_photo` (Our photo)
- `x_studio_pick_position` (Alt позиция «1/2»)
- `x_studio_supplier_photo_url` (URL вспомогательный)
- `x_studio_supplier_photo_html` (Supplier photo рендер)
- `x_studio_item_comment_text` (Comment computed text mirror)
- `x_studio_supplier_product_name` (Supplier name)
- Кнопки: `New +` (red+grey) и `Alt →`

#### 13.12.3. Какие колонки **всегда видны** в обоих modes

Без `optional` атрибута (нельзя скрыть через slider-меню юзером):

- `x_studio_our_photo` в Logist mode (force visible — это критичная часть UX)
- `x_studio_pick_position`, `x_studio_supplier_photo_html`, `x_studio_item_comment_text`, `x_studio_supplier_product_name` в Logist

Это потому что Odoo column chooser persistence хранится в browser localStorage **общим** для всех mode'ов в рамках одного view. Если поле имеет `optional`, юзер может его un-tick в одном mode'е — и предпочтение применится к другому mode тоже. Чтобы Logist-essential поля всегда были видны в Logist mode независимо от localStorage предпочтений в Bookkeeper'е — `optional` убрано.

#### 13.12.4. Колонки управляемые юзером per-browser

С `optional="show/hide"` (видны в slider-меню, юзер toggles вручную):

- `x_studio_match_confidence` (Match badge) — `optional="hide"`
- `x_studio_alternative_cards` — `optional="hide"`
- `product_description_variants` (Custom Description) — `optional="show"`
- `x_studio_supplier_sku` (Supplier Codigo) — `optional="show"`
- `x_studio_supplier_lot_code` (Supplier Lot Code) — `optional="show"`
- `x_studio_item_comment` (raw char) — `optional="hide"`
- `x_studio_operator_hit` (operator HIT) — `optional="show"`
- `x_studio_expected_qty` — `optional="show"`
- `x_studio_margin_x_display` (Margin) — `optional="show"`
- `x_studio_sales_price_now` — `optional="show"`
- `x_studio_qty_received_stems` (Real Recv) — `optional="show"`
- Standard `discount` (Disc.%), `qty_received` — управляются Odoo defaults

#### 13.12.5. Mechanics — column_invisible vs optional vs localStorage

| Mechanism | Где живёт | Per-user? | Per-mode? | Override-able? |
|---|---|---|---|---|
| `column_invisible="<expr>"` | Server XML | Нет (на всех) | Да (через expression) | Нет — server-side rule |
| `optional="show/hide"` | Server XML — задаёт **default** | Нет | Нет | Юзер может toggle через slider |
| User toggle (slider menu) | Browser localStorage (`optional_fields,<view>,<user>,<view_id>`) | Да | **Нет** (общий для mode'ов) | Юзер сам ставит/снимает |

**Подвох**: localStorage не различает `view_mode`. Если в Bookkeeper'е снять галку с поля у которого есть optional — она снимется и в Logist'е тоже. Решение: для критичных полей режима убрать `optional` (они станут force-visible в нужном mode через column_invisible).

#### 13.12.6. Header формы

В header pedido (Vendor Reference, Payment Terms, Claude AI Finalize Trigger, Expected Arrival, Other Info tab) — **mode не применяется**. Все поля видны в обоих modes.

Решение owner'а 2026-05-09: header не трогаем, mode переключает только line tree visibility.

#### 13.12.7. Pre-existing pedido — bulk migration

Все 184 pedido в системе на момент 2026-05-09 получили `x_studio_view_mode='logist'` через bulk update. Новые pedido автоматически берут `'logist'` через `ir.default 34`.

#### 13.12.8. Future modes — если понадобится

Если потом распределитель или флорист-в-магазине окажутся отдельными ролями — добавляется:
1. Новое selection value (например `'distributor'`, `'shop'`) в field 27797.
2. Новая server action (например 1245).
3. Новая кнопка в header view 4467.
4. Соответствующие column_invisible expressions для новых полей.

Архитектура расширяемая — но прежде чем добавлять mode стоит проверить что текущие 2 mode'а не покрывают use case (часто distinguishing roles в UX = шум, а не польза).

---

## См. также

- [02_makecom_bot.md](02_makecom_bot.md) — Make.com bot reconciliation engine.
- [03_inventory_pipeline.md](03_inventory_pipeline.md) — stock-слой приёмки (review_status, calculate_in_shop, sentinel -1).
- [05_catalog.md](05_catalog.md) — карточки товара (placeholder lines reassign на real cards).
- [99_invariants.md](99_invariants.md) — правила работы.
- [add/09_reception_algorithm.md](add/09_reception_algorithm.md) — current spec.
- [add/09_reception_algorithm_v1.md](add/09_reception_algorithm_v1.md) — v1 baseline.
- [add/09_reception_action_1217.py](add/09_reception_action_1217.py) — finalizer mirror.
- [add/09_reception_handover_2026-04-29.md](add/09_reception_handover_2026-04-29.md) — операционные правила.
- [add/09_reception_audit_v12_prompt.md](add/09_reception_audit_v12_prompt.md), [add/09_reception_audit_v14_prompt.md](add/09_reception_audit_v14_prompt.md) — audit prompts.
- [add/09_reception_INSTR_attach_pdf.md](add/09_reception_INSTR_attach_pdf.md) — bulk PDF attach recipe.
- [add/09_reception_INSTR_test_run.md](add/09_reception_INSTR_test_run.md) — single-pedido test run recipe.
