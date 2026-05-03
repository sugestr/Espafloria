<!-- v: 4 | updated: 2026-05-03T17:30Z -->
# 03. Inventory pipeline — приёмка и bill control

**Что в файле:** техдок приёмки (`stock.picking` / `stock.move` слой, review-status, calculate_in_shop, sentinel -1) + bill control policy (`purchase` vs `receive`) + backorder logic. **Reconciliation слой** (бот + `purchase.order.line`) — отдельно в [02_makecom_bot.md](02_makecom_bot.md).

**Status:** 🟢 PROD — review automation активна (id=1146); 188 pedido draft в системе после Holded re-import; stock.move = 0 пока pedidos не подтверждены.

---

## 1. Архитектурный слой

**Разделение двух слоёв** ([01_project § 4.1](01_project.md)):

| Слой | Модели | Задача |
|---|---|---|
| Reconciliation | `purchase.order`, `purchase.order.line` | Сопоставление бумаги с заказом, vendor code learning. См. [02_makecom_bot](02_makecom_bot.md) |
| **Receipt Review** (этот файл) | `stock.picking`, `stock.move` | Фактическая приёмка, ввод факта флористом |

Эти слои **не должны смешиваться.** Все прошлые неудачи — от попыток объединить «что заказано» и «что приехало».

---

## 2. Кастомные поля на `stock.move` (9 штук)

| Поле | Тип | Related/Compute | Назначение |
|---|---|---|---|
| `x_studio_paper_qty` | float | related → `purchase_line_id.product_qty` | Количество по бумаге |
| `x_studio_paper_unit` | many2one (uom.uom) | related → `purchase_line_id.uom_id` | Единица бумаги. ⚠️ Это **record**, не string ([99 §G5](99_invariants.md)) |
| `x_studio_expected_qty_info` | float | related → `purchase_line_id.x_studio_expected_qty` | Оценка логиста (числовое) |
| `x_studio_expected_qty_info_display` | char | compute | Display-обёртка (прячет нули) |
| `x_studio_received_packs` | float | — | **Ввод флориста**: реальные пачки |
| `x_studio_diff_vs_expected` | float | compute | `quantity - expected_qty_info` (если > 0) |
| `x_studio_avg_per_pack` | float | compute | `quantity / packs` (если packs > 0) |
| `x_studio_review_status` | char | через automation 1 | Текст UI-бейджа («от бумаги +5», «OK 📦 4.9 шт/пак») |
| `x_studio_review_color` | integer | через automation 1 | ID цвета бейджа (1/3/4/10) |

**Штатные Odoo поля (используем как есть):**
- `quantity` — фактические штуки (**ввод флориста**).
- `purchase_line_id` — связь с pedido line.
- `picking_id` — связь с Transfer.
- `product_uom_qty` — Demand (НЕ трогаем как бизнес-поле).

**Удалены 18 апреля (дубли):** `x_studio_received_units` (= штатный `quantity`), `x_studio_expected_quantity` (= `x_studio_paper_qty`), `x_studio_supplier_unit` (= `x_studio_paper_unit`).

---

## 3. Sentinel `-1` vs `0` для `quantity`

| Значение | Семантика |
|---|---|
| `quantity = -1` | «Штуки ещё не пересчитаны флористом» |
| `quantity = 0` | «Реально ничего не приехало» (валидное бизнес-значение) |
| `quantity > 0` | «Принято N штук» |

**Для `x_studio_received_packs`:**
- `< 0` — не используется.
- `= 0` — «пачки не введены» (если пачечная строка).
- `> 0` — «принято N пачек».

**Почему разная семантика:** у `quantity` есть штатный default (Odoo подставляет ожидаемое) → sentinel нужен. У packs default = 0, и это можно трактовать как «не введено».

---

## 4. Review-status automation

| Параметр | Значение |
|---|---|
| Automation | `Review → generate info conclusion` (id=1) |
| Trigger | `on_create_or_write` |
| Watched fields | `quantity`, `x_studio_received_packs` (узкий список — [99 §G2](99_invariants.md)) |
| Server action id | 1146 |
| Snapshot file | `add/03_review_status_automation.py` |

### 4.1. Severity levels

| Level | Цвет | ID | Смысл |
|---|---|---|---|
| 0 | 🟢 green | 10 | OK |
| 1 | 🔵 blue | 4 | Нужен ввод («посчитать!», «...и пачки?») |
| 2 | 🟡 yellow | 3 | Расхождение с бумагой / пачками |
| 3 | 🔴 red | 1 | Расхождение с логистом |

**Приоритет (в коде):**
```python
level = max(level, 1)  # missing (blue)
level = max(level, 2)  # vs paper (yellow)
level = 3  # vs logist (red) — жёстко перебивает всё
```

**Расхождение с логистом считается серьёзнее расхождения с бумагой** — логист физически пересчитывал, бумага могла не проверяться.

### 4.2. Примеры production-статусов

- `"от бумаги +5"` → штуки 25 при бумаге 20, yellow.
- `"OK 📦 4.9 шт/пак"` → 49 штук / 10 пачек, green.
- `"посчитать!"` → quantity = -1, blue.

### 4.3. Stock move IDs в проде (на 2026-04-19)

18 stock.move с заполненным `x_studio_review_status` (IDs 461-478). Большинство — автостатус «OK». Выборка:

| ID | Paper | Unit | Logist | Qty | Packs | Status | Color |
|---|---|---|---|---|---|---|---|
| 464 | 20 | Units | 25 | 25 | 0 | «от бумаги +5» | 3 (yellow) |
| 466 | 25 | Units | 26 | 26 | 0 | «от бумаги +1» | 3 (yellow) |
| 467 | 10 | Paquete (31) | 49 | 49 | 10 | «OK 📦 4.9 шт/пак» | 10 (green) |
| 468 | 3 | Paquete (31) | 10 | 10 | 3 | «OK 📦 3.33 шт/пак» | 10 (green) |
| 477 | 10 | Paquete (31) | 49 | 49 | 10 | «OK 📦 4.9 шт/пак» | 10 (green) |

**`uom_id = 31`** = «Paquete (Усреднённый)» — единственная пачечная единица сейчас. Если появятся `Ramo`, `Bunch` — обновить условие в скрипте:
```python
is_pack = 'paq' in unit or 'pack' in unit or 'paquete' in unit
```

---

## 5. Кнопка «Посчитать в магазине»

| Параметр | Значение |
|---|---|
| Server action | `calculate_in_shop` (id=1150) |
| Binding | `stock.picking` (list + form view) |
| Snapshot file | `add/03_calculate_in_shop_action.py` |

**Что делает:**
```python
for picking in records:
    for move in picking.move_ids:
        if move.purchase_line_id and move.picking_id and move.picking_id.picking_type_id.code == 'incoming':
            move['quantity'] = -1
```

Сбрасывает `quantity` в `-1` (sentinel) для всех incoming moves выбранного picking — флорист видит «нужно пересчитать».

**⚠️ Намеренное решение:** кнопка **не сбрасывает** `x_studio_received_packs`. Причина: оставляем возможность отследить работу уволенного бухгалтера на старых 181 albaran 2026 года. После массового импорта можем пересмотреть.

---

## 6. Bill control policy

**Принято 2026-04-18.** Разделение по типам товара.

### 6.1. Цветы / горшечка → `purchase` (On ordered quantities)

| Категория | id |
|---|---|
| `FLORES CORTADAS` | 212 |
| `PLANTAS EN MACETAS` | 213 |

**Что значит:**
- Vendor bill ждёт `product_qty` (paper), не `qty_received`.
- Платим по бумаге поставщика, независимо от расхождений приёмки.

**Причины:**
- Цветы — живой товар, расхождения «49 из 50» — норма.
- Поставщику платят по его factura, бизнес не спорит за мелочи.
- Receipt важен для склада, но не должен диктовать сумму bill.

**Сделано 2026-04-18:** ~900 карточек FLORES CORTADAS + PLANTAS EN MACETAS → `purchase`.

### 6.2. Остальное → `receive` (On received quantities)

DECORACION, EMBALAJE, ENTREGA, PRODUCTOS ESPECIALES, Consumibles → `receive`. ~1085 карточек.

### 6.3. Проверка в Odoo

```
Покупки → Товары → фильтр: Method = "On ordered quantities"
```

---

## 7. Backorder logic

**Правило:** **ожидаем ли реальный довоз?**

| Решение | Когда |
|---|---|
| **Create Backorder** | Ждём вторую машину / довоз |
| **No Backorder** | Поставка фактически завершена, остаток не приедет |

**НЕ решает** сам факт расхождения. Расхождение «недопоставка без довоза» = просто недопоставка, **No Backorder**.

**Если поставщик не привезёт никогда** → No Backorder + **отдельная финансовая работа:** претензия поставщику, запрос credit note, корректирующий vendor bill через бухгалтера.

**Backorder ≠ решение финансовой проблемы.** Закрытие backorder'а не означает что вопрос с деньгами закрыт — это отдельный трек.

Когда довоз приехал — работаем в новом backorder receipt, не в старом.

---

## 8. Compute поля (формулы)

### 8.1. `x_studio_diff_vs_expected`
```python
for r in self:
    received_units = r.quantity or 0.0
    expected_units = r.x_studio_expected_qty_info or 0.0
    if expected_units:
        r['x_studio_diff_vs_expected'] = received_units - expected_units
    else:
        r['x_studio_diff_vs_expected'] = False
```

### 8.2. `x_studio_avg_per_pack`
```python
for r in self:
    packs = r.x_studio_received_packs or 0.0
    units = r.quantity or 0.0
    if packs > 0:
        r['x_studio_avg_per_pack'] = units / packs
    else:
        r['x_studio_avg_per_pack'] = False
```

### 8.3. `x_studio_expected_qty_info_display`
```python
for record in self:
    qty = record.x_studio_expected_qty_info
    if qty:
        if float(qty).is_integer():
            record['x_studio_expected_qty_info_display'] = str(int(qty))
        else:
            record['x_studio_expected_qty_info_display'] = str(qty)
    else:
        record['x_studio_expected_qty_info_display'] = ''
```

(Костыль: Odoo плохо прячет `0.0` в list view для float, поэтому char-обёртка.)

---

## 9. 3-точечная сверка в pedido

На `purchase.order.line` — **штатные Odoo поля** (без custom):

| Поле | Что показывает | Роль |
|---|---|---|
| `product_qty` | Заказано | **Paper** (бумага поставщика) |
| `x_studio_expected_qty` | — | **Logist** (оценка логиста) |
| `qty_received` | Сумма всех `stock.move.quantity` | **Actual** (факт флориста) |
| `qty_invoiced` | В vendor bill попало | Бонус — сверка с биллингом |

**Формулы расхождений:**
- `product_qty - qty_received` = недопоставка.
- `product_qty - qty_invoiced` = «бумага vs бухгалтерия» (должно быть 0).
- `qty_received - qty_invoiced ≠ 0` → бухгалтер не всё провёл.

**🔴 Open:** добавить `qty_received` + `qty_invoiced` в Studio-view `purchase.order.line`. Делать вручную в UI (2 минуты).

---

## 10. Кастомные поля на `purchase.order.line`

### 10.1 Bot-written fields (5)

Заполняются ботом/агентом во время reconciliation:

- `x_studio_expected_qty`
- `x_studio_item_comment`
- `x_studio_operator_hit`
- `x_studio_supplier_product_name`
- `x_studio_supplier_sku`

Полная таблица + описание — в [09_pedido § 8.1](09_pedido.md).

### 10.2 Studio analytics fields — variable packs UoM workaround (v4 NEW, май 2026)

**Проблема:** Verdnatura packs имеют **переменное** содержимое (3 stems/pack на одной поставке, 13 stems/pack на другой того же продукта). Odoo нативно ожидает **фиксированный** Paquete:Tallo коэффициент на product.template (по умолчанию 10:1). Это «catch weight» паттерн (рестораны, рыба, цветы).

**Что есть в Odoo 19 нативно:**
- `product.packaging` — только fixed-size packs (6-pack Coca-Cola). ❌ не подходит.
- Lots tracking — каждая пачка как lot с custom-полем «stems»; операционно тяжело.
- **Catch Weight** в core нет.

**Третьесторонний модуль** ([Product Catch Weight (Inventory)](https://apps.odoo.com/apps/modules/19.0/product_catch_weight_inventory) от Kanak Infosystems): ✅ Odoo.sh, ✅ On Premise, ❌ **NOT compatible с Odoo Online**. Требует миграцию на Odoo.sh (one-way, против [99 §3](99_invariants.md)).

**OCA:** catch weight модуля нет.

**Наше решение (Odoo Online compatible):** Studio computed fields на purchase.order.line, обходящие static UoM conversion. Бот пишет правду в `x_studio_expected_qty` (per-line stem count), Studio fields пользуются им для корректных значений в UI/отчётах.

#### 10.2.1 Поля

| Field name | Type | Compute | Назначение |
|---|---|---|---|
| `x_studio_sales_price_now` | float (related) | `product_id.list_price` | Розничная цена в магазине ex IVA |
| `x_studio_margin_x_1` | float (computed) | `list_price / cost_per_stem`, где `cost_per_stem = price_unit × product_qty / expected_qty` (с fallback на product_qty) | Множитель маржи (target ×3 retail) |
| `x_studio_margin_x_display` | char (computed) | `×{margin:.1f}` для stem; `×{margin:.1f} 🌻 {cost_per_stem:.2f}` для pack (где expected_qty ≠ product_qty) | Badge-friendly текст; 🌻 = «расчёт per-stem из пачки» |
| `x_studio_qty_received_stems` | float (computed) | `sum(move.quantity for done moves)` | Реальный приход в стеблях (через picking truth) |
| `x_studio_unit_price_per_stem` | float (computed) | `price_subtotal / expected_qty` (fallback на product_qty) | Реальная цена за стебель |

Все computed, `store=False`, `readonly=True`.

#### 10.2.2 Visual decoration на pedido form (4-tier)

Margin × badge на `x_studio_margin_x_display` использует пороги синхронизированные с spec [§A2.7.3](add/09_reception_algorithm.md):

| Margin × | Цвет | Семантика | Бот действие |
|---|---|---|---|
| < 1.5 | 🔴 red | убыток / cost ≥ price | gate `override_to_paper` (если loss) или `blocker_c` |
| 1.5 — 2.5 | 🟡 yellow | тонко, ниже target | normal flow |
| 2.5 — 10 | 🟢 green | норма | normal flow |
| ≥ 10 | 🔵 blue | подозрительно высоко | gate `high_soft_flag` — activity, no override |

#### 10.2.3 Скрытые стандартные поля Odoo

Через `optional="hide"` в Studio inheritance views (toggle вернёт):

**На `purchase.order.line` tree (pedido form):**
- `qty_received` — конвертит stems → packs через static factor (для pack-линии 3 stems показывает 0.3 packs).

**В `purchase.history.list` (action 756 — Purchase History на product form):**
- `product_uom_qty` (Quantity) — то же: 4 packs × 10 = 40 (статически), реально пришло 13 stems.
- `price_unit_product_uom` (Unit Price) — `price_unit / 10` = 0.27, реально 0.83 €/stem.

#### 10.2.4 Расхождение `expected_qty ≠ qty_received_stems`

Если эти поля не совпадают на done-pedido — это **маркер post-validation correction**:

1. Retro-fix вручную через MCP (manual quant adjustment вне picking flow).
2. Owner пересмотрел расчёт бухгалтера задним числом.
3. Bot-gate сработал post-factum — §A2.7.3 override после picking validation.

Любой случай = «знаем правду, но в `move.quantity` остался старый value». Полезный инвариант для аудита.

#### 10.2.5 Что НЕ затронуто (структурно точно)

После того как товар прошёл receipt:
- `stock.quant` (текущий остаток) в Tallo ✅
- `stock.move.quantity` после picking в Tallo ✅
- Inventory Reports / Inventory Valuation ✅
- Sales Order Lines / POS / Sales Analysis / Margin reports — всё в Tallo ✅

UoM-distortion живёт **только** в 5 purchase-incoming view'ах (3 уже скрыты Studio'м, остальные 2 — Vendor Bills qty display и Purchase Analysis pivot — могут быть закрыты по запросу через те же inherit views).

### 10.3 Mirrors

Ничего custom Python — все поля и view edits через Studio (UI или MCP `ir.model.fields` + `ir.ui.view` updates). Нет `.py` mirrors.

---

## 11. Open work

| # | Что | Статус |
|---|---|---|
| 11.1 | `qty_received` + `qty_invoiced` в Studio view | ✅ done (10.2.3 — qty_received скрыт, заменён на `x_studio_qty_received_stems`) |
| 11.2 | Визуальная подсветка расхождений (`product_qty != qty_received` → красный) | 🔴 |
| 11.3 | Блокировка Validate при критических отклонениях | 🔴 |
| 11.4 | Native Barcode receipts UX для флориста на планшете | 🔴 (закрывается штатно — Odoo 19 Barcode app) |
| 11.5 | Photo (одна или несколько) к receipt — общий вид партии / конкретная проблема | 🔴 (через Studio Image / Quality «Take a Picture» check) |
| 11.6 | Push-уведомление магазину «едет поставка» | 🔴 (через `mail.activity` или Telegram бот) |
| 11.7 | Multi-warehouse split одного albarán | 🔴 (custom, отложено) |
| 11.8 | Catch-weight compute (`effective_unit_cost = paper_total / actual_units`) | 🔴 (custom Python модуль — Odoo.sh) |
| 11.9 | Логист распределяет по магазинам — **поддерживаем оба варианта** (в момент закупки или вторым документом, по ситуации) | ✅ принцип |
| 11.10 | Логист видит vendor bill state vs только закупка/приёмка | ❓ |
| 11.11 | Rolling correction идёт автоматом vs через утверждение | ❓ |
| 11.12 | Флорист видит только свои поставки vs весь список входящих | ❓ |

---

## См. также

- [02_makecom_bot.md](02_makecom_bot.md) — reconciliation слой (бот, OCR, learned codes).
- [01_project.md](01_project.md) — § 4.1 бизнес-правило «истина = пересчёт флористом».
- [04_pos_and_roles.md](04_pos_and_roles.md) — роль логиста и связь с приёмкой.
- [05_catalog.md](05_catalog.md) — откуда берутся карточки + миграция supplierinfo.
- [99_invariants.md](99_invariants.md) — гл. правила + Odoo 19 gotchas (G1-G5 про automation, G2 про watched fields).
- `add/03_review_status_automation.py` — mirror action 1146.
- `add/03_calculate_in_shop_action.py` — mirror action 1150.
