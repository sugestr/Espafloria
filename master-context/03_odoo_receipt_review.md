<!-- v: 2 | updated: 2026-04-19T15:00Z -->
# 03. Приёмка и Review (stock.move)

Статус: 🟢 **PROD** — работает, 18 stock.move с review-статусами в проде.

---

## Главный архитектурный принцип

**Разделение двух слоёв:**

| Слой | Модели | Задача |
|---|---|---|
| Reconciliation | `purchase.order`, `purchase.order.line` | Сопоставление бумаги с заказом, vendor code learning |
| **Receipt Review** | `stock.picking`, `stock.move` | Фактическая приёмка, ввод факта флористом |

**Ключевое правило:** они **не должны смешиваться**. История прошлых итераций — все неудачи были от попыток объединить «что заказано» и «что приехало».

См. также: [02_makecom_bot.md](02_makecom_bot.md) (reconciliation слой), [99_invariants.md](99_invariants.md) (правила).

---

## Кастомные поля на `stock.move` (9 штук после hot-fix)

После чистки (18 апреля) осталось 9 полей:

| Поле | Тип | Related/Compute | Назначение |
|---|---|---|---|
| `x_studio_paper_qty` | float | related → `purchase_line_id.product_qty` | Количество по бумаге |
| `x_studio_paper_unit` | many2one (uom.uom) | related → `purchase_line_id.uom_id` | Единица бумаги. ⚠️ **Это record, не string!** Использовать `.display_name` или `.name`. |
| `x_studio_expected_qty_info` | float | related → `purchase_line_id.x_studio_expected_qty` | Оценка логиста (числовое) |
| `x_studio_expected_qty_info_display` | char | compute | Display-обёртка (прячет нули) |
| `x_studio_received_packs` | float | — | **Ввод флориста**: реальные пачки |
| `x_studio_diff_vs_expected` | float | compute | `quantity - expected_qty_info` (если > 0) |
| `x_studio_avg_per_pack` | float | compute | `quantity / packs` (если packs > 0) |
| `x_studio_review_status` | char | пишется через automation | Текст UI-бейджа («от бумаги +5», «OK 📦 4.9 шт/пак») |
| `x_studio_review_color` | integer | пишется через automation | ID цвета бейджа (1/3/4/10) |

**Штатные Odoo поля (не кастомные):**
- `quantity` — фактические штуки (**ввод флориста**)
- `purchase_line_id` — связь с pedido line
- `picking_id` — связь с Transfer
- `product_uom_qty` — Demand (НЕ трогаем как бизнес-поле)

**Удалены 18 апреля (дубли):**
- `x_studio_received_units` (замещён штатным `quantity`)
- `x_studio_expected_quantity` (дубль `x_studio_paper_qty`)
- `x_studio_supplier_unit` (дубль `x_studio_paper_unit`)

---

## Sentinel `-1` vs `0` для quantity

**Семантика:**
- `quantity = -1` → «штуки ещё не пересчитаны флористом»
- `quantity = 0` → «реально ничего не приехало» (валидное бизнес-значение)
- `quantity > 0` → «принято N штук»

**Для пачек (`x_studio_received_packs`):**
- `< 0` — не используется (seldom)
- `= 0` — «пачки не введены» (ЕСЛИ это пачечная строка)
- `> 0` — «принято N пачек»

**Почему разная семантика у quantity и packs:**
- У `quantity` всегда есть штатный default (Odoo подставляет ожидаемое) → sentinel нужен
- У `x_studio_received_packs` default = 0, и это можно трактовать как «не введено»

---

## Review-status automation (production code)

**Automation:** `Review → generate info conclusion` (id=1)
**Trigger:** on_create_or_write
**Watched fields (после hot-fix 18 апреля):** `quantity`, `x_studio_received_packs` (остальные убраны)
**Server action id:** 1146

**Code:** см. `review_status_automation.py`

**Severity levels:**

| Level | Цвет | ID | Смысл |
|---|---|---|---|
| 0 | 🟢 green | 10 | OK |
| 1 | 🔵 blue | 4 | Нужен ввод («посчитать!», «... и пачки?») |
| 2 | 🟡 yellow | 3 | Расхождение с бумагой / пачками |
| 3 | 🔴 red | 1 | Расхождение с логистом |

**Приоритет (в коде):**
```python
level = max(level, 1)  # missing (blue)
level = max(level, 2)  # vs paper (yellow)
level = 3  # vs logist (red) — жёстко перебивает всё
```

**Расхождение с логистом считается серьёзнее расхождения с бумагой** — логист физически пересчитывал, бумага могла не проверяться.

**Примеры реальных production-статусов:**
- `"от бумаги +5"` → штуки 25 при бумаге 20, yellow
- `"OK 📦 4.9 шт/пак"` → 49 штук / 10 пачек, green
- `"посчитать!"` → quantity = -1, blue

---

## Кнопка «Посчитать в магазине»

**Server action:** `calculate_in_shop` (id=1150)
**Binding:** `stock.picking` (list + form view)
**Code:** см. `calculate_in_shop_action.py`

```python
for picking in records:
    for move in picking.move_ids:
        if move.purchase_line_id and move.picking_id and move.picking_id.picking_type_id.code == 'incoming':
            move['quantity'] = -1
```

**⚠️ Намеренное решение:** кнопка **не сбрасывает** `x_studio_received_packs`. Причина: оставляем возможность отследить работу уволенного бухгалтера на старых 181 albaran 2026 года. После массового импорта можем пересмотреть логику.

---

## Bill control policy (принято 18 апреля)

**Для цветов/горшечки** (категории `FLORES CORTADAS` id=212 и `PLANTAS EN MACETAS` id=213):
- `purchase_method = 'purchase'` — **On ordered quantities**
- Vendor bill ждёт `product_qty` (paper), а не `qty_received`
- Платим по бумаге поставщика, независимо от расхождений приёмки

**Причины:**
- Цветы — живой товар, расхождения «49 из 50» — норма
- Поставщику платят по его factura, бизнес не спорит за мелочи
- Receipt важен для склада, но не должен диктовать сумму bill

**Для ваз/декора/упаковки/сервисов:**
- `purchase_method = 'receive'` — On received quantities
- Позже можем мигрировать точечно

**Сделано 18 апреля:** 900 карточек FLORES CORTADAS + PLANTAS EN MACETAS → `purchase`.
Все остальные (1095) остались на `receive`.

**Проверка в Odoo:**
```
Покупки → Товары → фильтр: Method = "On ordered quantities"
```

---

## 3-точечная сверка в pedido (штатные поля Odoo)

На `purchase.order.line` используем **штатные Odoo поля** (без custom):

| Поле | Что показывает | Роль |
|---|---|---|
| `product_qty` | Заказано | **Paper** (бумага поставщика) |
| `x_studio_expected_qty` | — | **Logist** (оценка логиста) |
| `qty_received` | Сумма всех `stock.move.quantity` | **Actual** (факт флориста) |
| `qty_invoiced` | В vendor bill попало | Бонус — сверка с биллингом |

**TODO:** добавить `qty_received` + `qty_invoiced` в Studio-view `purchase.order.line`. Делать вручную в UI (2 минуты).

**Использование:**
- `product_qty - qty_received` = недопоставка
- `product_qty - qty_invoiced` = «бумага vs бухгалтерия» (должно быть 0)
- `qty_received - qty_invoiced` ≠ 0 → бухгалтер не всё провёл

---

## Backorder logic

**Правило принятия решения:** **ожидаем ли реальный довоз?**

- Ждём вторую машину / довоз → **Create Backorder**
- Поставка фактически завершена, остаток не приедет → **No Backorder**

**НЕ решает:** сам факт расхождения. Расхождение «недопоставка без довоза» — просто недопоставка, No Backorder.

Когда довоз приехал — работаем в новом backorder receipt, не в старом.

---

## Compute поля (формулы)

### `x_studio_diff_vs_expected`
```python
for r in self:
    received_units = r.quantity or 0.0
    expected_units = r.x_studio_expected_qty_info or 0.0
    if expected_units:
        r['x_studio_diff_vs_expected'] = received_units - expected_units
    else:
        r['x_studio_diff_vs_expected'] = False
```

### `x_studio_avg_per_pack`
```python
for r in self:
    packs = r.x_studio_received_packs or 0.0
    units = r.quantity or 0.0
    if packs > 0:
        r['x_studio_avg_per_pack'] = units / packs
    else:
        r['x_studio_avg_per_pack'] = False
```

### `x_studio_expected_qty_info_display`
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

(Костыль: Odoo плохо прячет `0.0` в list view для float, поэтому делаем char-обёртку.)

---

## Запрещённые паттерны (lessons learned)

### ❌ Каскадные write() в automation rules
- Был automation, который при save receipt проходил все строки и писал quantity + status
- Результат: Odoo висел, automation триггерила сама себя
- **Правило:** line-level automation — только для **текущей** строки. Document-level действия — только явной кнопкой / server action.

### ❌ `On create` для reset quantity
- Пробовали: `Update Record → quantity = 0` на create stock.move
- Odoo позже сам подставляет ожидаемые значения → неработает
- **Правило:** не полагаться на `On create`, использовать explicit button.

### ❌ `After creation delay` (delayed actions)
- Срабатывал недетерминированно, иногда после Cancel state change
- **Правило:** не использовать delayed actions для reset-логики.

### ❌ Широкий `When updating field`
- Если в watched fields есть `picking_id` / `purchase_line_id` / структурные поля → automation запускается слишком часто, не только при вводе пользователя
- **Правило:** узкий список watched fields (сейчас только `quantity` + `x_studio_received_packs`)

### ❌ `.strip()` на `x_studio_paper_unit`
- Это `uom.uom` record, не string
- Правильно: `record.x_studio_paper_unit.display_name` или `.name`

### ❌ `hasattr()` в server action
- Недоступен в safe_eval sandbox
- Замена: `'field_name' in record._fields`

---

## Stock move IDs, которые уже обработаны (production tests)

На 2026-04-19 в проде **18 stock.move с заполненным `x_studio_review_status`** (IDs 461-478). Большинство — автостатус «OK»; ниже выборка из 5 интересных случаев (расхождения, пачечный расчёт):

| ID | Paper | Unit | Logist | Qty | Packs | Status | Color |
|---|---|---|---|---|---|---|---|
| 464 | 20 | Units | 25 | 25 | 0 | «от бумаги +5» | 3 (yellow) |
| 466 | 25 | Units | 26 | 26 | 0 | «от бумаги +1» | 3 (yellow) |
| 467 | 10 | Paquete (31) | 49 | 49 | 10 | «OK 📦 4.9 шт/пак» | 10 (green) |
| 468 | 3 | Paquete (31) | 10 | 10 | 3 | «OK 📦 3.33 шт/пак» | 10 (green) |
| 477 | 10 | Paquete (31) | 49 | 49 | 10 | «OK 📦 4.9 шт/пак» | 10 (green) |

**uom_id = 31** = «Paquete (Усреднённый)» — единственная пачечная единица в системе сейчас.
Если появятся другие (Ramo, Bunch) — проверить условие в review-status скрипте:
```python
is_pack = 'paq' in unit or 'pack' in unit or 'paquete' in unit
```
Для `Ramo` надо будет добавить `'ramo' in unit`.

---

## Открытые вопросы / будущее

- ⬜ Визуальная подсветка расхождений (сейчас только color в бейдже)
- ⬜ Блокировка Validate при критических отклонениях (сейчас всё можно валидировать)
- ⬜ Нормальный UX для флориста (tablet view) — см. [05_florists_logistics_accountant.md](05_florists_logistics_accountant.md)
- 🔴 Multi-warehouse split одного albarán — не реализован
- 🔴 Catch-weight compute стоимости — не реализован (см. [09_open_work.md](09_open_work.md))

---

## См. также

- [02_makecom_bot.md](02_makecom_bot.md) — reconciliation слой (purchase.order)
- [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md) — миграция карточек, чтобы коды поставщика ехали с карточкой
- [99_invariants.md](99_invariants.md) — все инварианты
