<!-- v: 3 | updated: 2026-05-03T00:30Z -->
# 09. Pedido — работа с purchase orders

**Что в файле:** домен `purchase.order` (закупки у поставщиков): источники, жизненный цикл, reconciliation paper PDF ↔ Odoo, action 1217 finalizer, supplierinfo learning, partner_id Verdnatura. Reception_algorithm — главный artefact в `add/09_reception_algorithm.md`.

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
