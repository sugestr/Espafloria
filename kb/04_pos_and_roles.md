<!-- v: 2 | updated: 2026-05-02T23:30Z -->
# 04. POS, букеты, eWallet, роли, бонусы, CRM

**Что в файле:** техдок всего, что вокруг кассы. **Букеты — полная архитектура** (reserve-model v2). **eWallet — полная бухгалтерская и operational механика.** Роли (флорист/логист/бухгалтер). Бонусная модель. CRM. Всё, что в документе на 2026-04-25.

---

## 1. POS — конфигурация и текущее состояние

### 1.1. 3 кассы, 3 склада, 3 cash-метода

| POS | id | warehouse | picking_type | module_pos_hr | cash_control | advanced_employees |
|---|---|---|---|---|---|---|
| POS Plaza | 1 | Plaza (2) | Plaza: Pedidos de TPV (18) | ✅ | ✅ | [10, 11, 1] |
| POS Gloria | 2 | Gloria (3) | Gloria: Pedidos de TPV (27) | ✅ | ✅ | [10, 11, 1] |
| POS Blau | 3 | Blau (4) | Blau: Pedidos de TPV (36) | ✅ | ✅ | [10, 11, 1] |

**Config fix 2026-04-19:** POS Gloria/Blau изначально были на `warehouse_id=2` (Plaza), POS Blau с неправильным `picking_type_id=27` (Gloria). Поле `warehouse_id` скрыто из UI в Odoo 19 → починено через MCP RPC write. Историческая причина: кассы создавались когда склады уже существовали, но Odoo не проставил автоматически.

### 1.2. Payment methods

| ID | Name | type | journal | configs |
|---|---|---|---|---|
| 1 | Efectivo Plaza | cash | Efectivo Plaza (20, EFPL) | [1] |
| 4 | Efectivo Gloria | cash | Efectivo Gloria (21, EFGL) | [2] |
| 5 | **Efectivo Blaus** | cash | Efectivo Blau (22, EFBL) | [3] |
| 2 | Tarjeta | bank | Bank (15) | [1, 2, 3] |
| 3 | Cuenta de cliente | pay_later | — | [1, 2, 3] |
| 6 | 🌹 Собрать / изменить букет | bank (technical) | Bouquet Internal (24) | [1, 2, 3] |
| 8 | 🗑 Разобрать букет | bank (technical) | Bouquet Internal (24) | [1, 2, 3] |

**Cash per-POS — требование Odoo:** каждая касса свой cash-метод (constraint), GL `570001 Efectivo` общий, разные journal codes для per-POS bookkeeping.

**⚠️ Опечатка:** id=5 = `Efectivo Blaus` (лишняя s). Journal `Efectivo Blau` правильный. Cosmetic fix.

**Cuenta de cliente vs eWallet** — разные механики:
- **Cuenta de cliente** (id=3, `pay_later`) = в долг. Клиент уносит, оплата на партнёре как `account.receivable`, гасится отдельной транзакцией. Штатный Odoo flow для постоплаты.
- **eWallet** = предоплата. Клиент сначала пополняет, потом тратит баланс. Reward-механика на cart screen, **не payment method**. См. § 3 ниже.

### 1.3. Employee rights (Odoo 19 `pos_hr`)

| Tier | Права |
|---|---|
| **minimal** | Только продажи, без cash in/out, без закрытия смены |
| **basic** | + cash in/out, + открытие смены |
| **advanced** | + create product, + закрытие смены с пересчётом наличных, + управление конфигом через POS UI |

Все 3 флориста (Andriy + 2 Test) сейчас в `advanced` на всех 3 POS — могут открыть/закрыть смену, cash in/out, create product. Для рядового персонала это слишком — изучить OCA `pos_*_security` если будет на Odoo.sh.

**Гранулярность сверх 3 уровней** — на будущее (junior/senior/manager + manager-PIN approval flow).

**❓ Open:** финальный mix авторизации флориста при продаже — PIN / выбор из списка / автоматически по активной смене / комбинация. Сейчас PIN через `pos_hr`. Возможные варианты не финализированы.

### 1.4. Users

| ID | login | groups | роль |
|---|---|---|---|
| 2 | espafloria@gmail.com | [1, 33, 88, +18] | Andriy admin (backend, POS manager, Studio) |
| 5 | pos_terminal@espafloria.local | [1, 87] | POS Terminal kiosk user для всех 3 планшетов |

**3 лицензии оплачены, использовано 2** (Andriy + POS Terminal). 3-я зарезервирована под бухгалтера.

**Политика POS Terminal:**
- Dedicated non-admin user для планшетов. Кража планшета = только POS-экран, без admin.
- Home action = «POS Config Kanban».
- `.local` в email — технический формат (Odoo требует валидный email), почта никуда не уйдёт.

**hr.employee (PIN-логин в POS, не лицензия):**

| ID | name | pin | роль |
|---|---|---|---|
| 1 | Andriy Klymenko | false | manager |
| 10 | Mega Florist 1111 | 1111 | future florist placeholder |
| 11 | 2 Florista Test | 2222 | future florist placeholder |

`hr.employee` **не занимает лицензию** — PIN-логин через `pos_hr` бесплатный. Каждая продажа прилипает к `pos.order.employee_id` — фундамент бонусной модели (см. § 6).

### 1.5. POS workflow caveats

**Закрытие смены:** advanced employee делает Cash In/Out + закрытие с пересчётом. При передаче смены (день→ночь): старый advanced закрывает (пересчёт, подпись), новый открывает.

**⚠️ После Close Register Odoo автоматически открывает экран Opening Control следующей сессии.** Если флорист случайно нажмёт Open Register или закроет вкладку → создаётся «полуоткрытая» pos.session в state `opening_control` без orders. Это **блокирует правки на pos.config** (нельзя менять journal/payment_method/warehouse).

**Правильно:** Close Register → закрыть вкладку браузера ИЛИ навигировать прочь (клик по логотипу Odoo), **НЕ нажимать Open Register** если не идёт смена сразу. Удалить такую сессию через UI нельзя; fallback — direct write `state='closed'` + `stop_at` через MCP. См. [99 §G8, §G9](99_invariants.md).

**POS PWA cache:** Chrome агрессивно кеширует config. После изменения `advanced_employee_ids` или `module_pos_hr` — **Reload Data** из гамбургер-меню (или Cmd+Shift+R). Safari подхватывает быстрее.

### 1.6. POS categories

`iface_available_categ_ids=[]`, `limit_categories=false` на всех 3 config. **Блокер UX кассира** — не может фильтровать по группам Rosas/Ramas/Plantas/Servicios. См. [01_project § 5.2.7](01_project.md).

`product.template.pos_categ_ids` (m2m, optional) — UI-группировка на экране кассира. **Отличается от** `product.template.categ_id` (m2o, required) — бухгалтерская/складская категория. Не смешивать.

---

## 2. Букеты — полная архитектура (v2 reserve-model)

> Refactored 2026-04-23. v1 deprecated.

### 2.1. Что моделирует

Букет — **`sale.order`** с:
- `partner_id=53` (`🌹 Букет на витрину`, technical partner)
- `state=sale`
- SO-picking в state `assigned` (компоненты зарезервированы, но не списаны)

**Имя:** `BP-YYYY-NNNN`, sequence per-warehouse:
- `espafloria.bouquet.plaza`
- `espafloria.bouquet.gloria`
- `espafloria.bouquet.blau`

**Почему `sale.order`, не отдельная модель и не MRP BoM:**
- В `sale.order` уже есть весь lifecycle: `sale → cancel`, attachments, line modifications, ценники, связь с POS через `sale_order_origin_id`.
- BoM пересчитывал бы каждый букет как уникальную BoM — overkill, не аналитично.
- Custom model потребовала бы свой UI, права, отчёты — велосипед.
- Reserve-model даёт правильную картинку склада: «этот цветок на витрине, в букете, уже не свободен» = `available_quantity` уменьшается, `reserved_quantity` растёт.

### 2.2. Pre-built vs Made-on-sale — одна сущность

| Форма | Когда |
|---|---|
| **Made-on-sale** | Флорист собирает при клиенте (Settle BP-* → правка → Cash) |
| **Pre-built** | Утром собран на витрину, днём продан (Settle существующий BP-* → Cash, без правок) |

**Обе формы проходят один lifecycle.** Pre-built работает через тот же flow что Made-on-sale.

### 2.3. Четыре жизненных перехода

Все идут через **один payment method «🌹 Собрать / изменить букет» (id=6)** или **«🗑 Разобрать букет» (id=8)**, которые триггерят серверные actions 1203/1209.

| # | Триггер | Action ветка | Что делает (наш код) | Что делает (штатный Odoo) |
|---|---|---|---|---|
| **Create** | `pos.payment` method=6, **нет** Settle-линка | 1203 branch create | Создаёт SO BP-* на partner 53, `action_confirm()` → SO-picking `assigned`, **reverse POS-picking** | — |
| **Reassemble** | `pos.payment` method=6, **есть** Settle-линка на витринный SO | 1203 branch reassemble | `old.action_cancel()` (cancel old SO + его picking) → new SO BP-* с текущим составом, `action_confirm()`, reverse POS-picking | — |
| **Sell** | Settle BP-* + любой обычный payment (Cash/Card/eWallet/...) — **НЕ** method=6/8 | 1203 branch sell — **только chatter** | «💰 Продан флористом клиенту через POS-NNN» | Cancel SO-picking; POS-picking списывает компоненты; `qty_delivered` ++ через POS payment hook |
| **Dismantle** | `pos.payment` method=8 | 1209 (отдельный action) | `old.action_cancel()`, **reverse POS-picking** → стоки на склад | — |

### 2.4. Почему Sell ничего не cancel'ит вручную

Подтверждено тестом 1.1 (23 апр 2026): Odoo 19 при Settle+обычный payment **штатно** cancels SO-picking, POS-picking создаёт свой move, `qty_delivered` обновляется. **Условие:** SO-picking на момент Settle должен быть в `assigned`, не cancel.

**Старая v1 ломала это правило** (cancel SO-picking сразу после confirm) → в v2 убрано.

### 2.5. Маркер сборки (product 7864 «🌹 Работа по сборке букета»)

Service product, default 5€ IVA 10%. Бизнес-логика:
- Флорист **сам добавил с 5€** → бонус ему за сборку (личная мотивация, см. § 6).
- **Забыл добавить** → action 1203 branch create/reassemble авто-вставит с `qty=1, price=0` → бонуса нет, но маркер для аналитики есть.

### 2.6. Constants (ломать только согласованно)

| Константа | Значение | Где |
|---|---|---|
| `TECH_PARTNER_ID` | **53** | `🌹 Букет на витрину` res.partner |
| `BOUQUET_ASSEMBLE_METHOD_ID` | **6** | «🌹 Собрать / изменить букет» payment method |
| `BOUQUET_DISMANTLE_METHOD_ID` | **8** | «🗑 Разобрать букет» payment method |
| `ASSEMBLY_MARKER_PRODUCT_ID` | **7864** | «🌹 Работа по сборке букета» |

При переименовании / замене любого — менять в **обоих** actions (1203 и 1209) и в snapshot `.py` файлах (см. [99 §2](99_invariants.md)).

### 2.7. Скидка — на уровне букета, не на строках

Скидка применяется на уровне букета (общий `discount` на финальной строке), **не на компонентах**. Скидка по строкам компонентов «неудобно и недостоверно» — решение владельца.

**⚠️ Gotcha при создании SO с line discount:** `sale.order.line.discount` перезатирается на create из-за pricelist onchange. После create делать `.write({'discount': X})` на линиях. См. [99 §G11](99_invariants.md).

### 2.8. Архитектурный summary (table)

| Сценарий | Method оплаты | Наш код | Штатный Odoo |
|---|---|---|---|
| 1. Собрать на витрину | 🌹 (6) | 1203 branch create: SO BP-*, confirm → assigned, reverse POS-picking | — |
| 2. Модификация | 🌹 (6) | 1203 branch reassemble: cancel old, create new BP-*, confirm → assigned, reverse POS-picking | — |
| 3. Продажа клиенту | Cash/Card/eWallet | 1203 branch sell: только chatter | cancel SO-picking, POS-picking списывает, qty_delivered += 1 |
| 4. Разборка | 🗑 (8) | 1209: cancel old, reverse POS-picking | — |
| 5. Собрал+продал одним чеком | Cash/Card + маркер в корзине | Обычный POS-чек | Стандартный |

### 2.9. Что ушло в историю (v1 deprecated)

- Product id=7865 `[BQ-DISMANTLE]` → archived (разборка теперь через method=8).
- Actions 1205 (stock.picking layer) и 1207 (pos.order safety net) → automations 11/12 disabled, actions остались в базе на случай отката.
- Branch dismantle в 1203 → удалена, перенесена в 1209.
- `cancel SO-picking` после `action_confirm()` → убрано (ломало reserve-model).

### 2.10. Snapshot files

- `add/04_bouquet_on_payment_action.py` ↔ `ir.actions.server id=1203` (4 ветки)
- `add/04_bouquet_on_dismantle_action.py` ↔ `ir.actions.server id=1209` (только dismantle)
- Deprecated (в репо для истории): `add/04_bouquet_on_picking_action.py` (1205), `add/04_bouquet_on_order_paid_action.py` (1207)

### 2.11. Открытое по букетам

| # | Хотим | Статус |
|---|---|---|
| 2.11.1 | Photo на готовом букете (`sale.order.line.photo`) | 🔴 Studio Image field — 5 минут на Online |
| 2.11.2 | Две цены (shop vs online) через pricelist | 🔴 Native pricelists на POS config + website |
| 2.11.3 | Печать ценника (термопринтер, brand layout) | 🔴 — |
| 2.11.4 | Связь с eWallet (предоплата за заказной букет) | 🟡 По отдельности готово, end-to-end не проверено |
| 2.11.5 | Списание завядшей розы из существующего букета | 🟡 Через Reassemble (qty=0). Связка с workflow scrap+photo (§5) — будущее |
| 2.11.6 | Себестоимость букета | ❓ Rolling avg компонентов на момент создания, или fix at create? |
| 2.11.7 | Что в чеке клиенту | ❓ «Ramo personalizado #B-2026-0001» (одна строка) или развёрнутый список компонентов? |

---

## 3. eWallet — полная архитектура

**Status:** 🟢 PROD — JE 19/20/21 верифицированы (top-up Tata 100€ + redemption 3€ + close session). Используется как механизм **предоплаты за букет под заказ**.

### 3.1. Активные модули

- `loyalty` — base (loyalty.program / card / reward / rule)
- `pos_loyalty` — интеграция с POS
- `sale_loyalty` — интеграция с Sale Orders (для будущего Sale flow)
- `website_sale_loyalty` — eCommerce (когда будет сайт)
- `pos_discount` — POS-side скидочный модуль

### 3.2. Программа

| Поле | Значение |
|---|---|
| `loyalty.program` id | **2** |
| name | `eWallet` |
| `program_type` | `ewallet` |
| `is_payment_program` | True |
| currency | EUR |
| `pos_config_ids` | `[]` (пусто = все 3 POS, баланс ходит между Plaza/Gloria/Blau) |
| `available_on` | POS + Sales + Website |
| `applies_on` | `future` (нельзя топнуть и сразу же потратить в том же чеке) |
| `trigger` | `auto` (loyalty.card создаётся автоматически при продаже trigger product клиенту) |
| `trigger_product_ids` | [7857] |
| `reward_ids` | [2] (один reward `1€ per point discount`) |

### 3.3. Продукты

| ID | Name | Роль | Income Account | Tax | available_in_pos |
|---|---|---|---|---|---|
| 7857 | Top-up eWallet | Пополнение (trigger product) | **438000 Anticipos** | 0% | True |
| 7862 | eWallet | Discount/redemption (`discount_line_product_id` на reward 2) | **438000 Anticipos** | 0% | False |
| 7860 | eWallet (orphan) | — | — | — | **archived 2026-04-21** |

### 3.4. Бухгалтерская механика (verified 2026-04-21 на JE 19/20/21)

**Пополнение через POS** (Top-up eWallet продаётся клиенту, оплачивается кешем):
```
Dr 430100 Trade receivables (PoS) N €    ← промежуточный POS receivable
Cr 438000 Anticipos de clientes  N €    ← liability (наш долг клиенту)
```
И параллельно cash-side:
```
Dr 570001 Efectivo               N €
Cr 430100 Trade receivables      N €
```
Нетто: `Dr 570 / Cr 438` — клиент пополнил.

**Редемпция** (клиент покупает букет на M €, eWallet покрывает X € из M):
```
Dr 438000 Anticipos              X €    ← гашение пассива
Cr 700000 Merchandise sold       (X − VAT)
Cr 477000 IVA repercutido        VAT
```
Если M > X — остаток (M − X) идёт через обычный cash flow (Dr 570 / Cr 700+477).

### 3.5. Operational invariant

В любой момент `sum(loyalty.card.points)` (по всем картам всех клиентов) **должен равняться** кредитовому балансу 438 Anticipos на тот же момент. **Расхождение = bug.**

### 3.6. Critical fix 2026-04-21

При автогенерации program Odoo создал discount product 7862 с `property_account_income_id = False`. Это означало бы при первой редемпции списание eWallet ушло бы в 700 Ventas (default из category), не гасило 438. **Зафиксировано через MCP write — теперь оба продукта пишут в 438.**

### 3.7. Где смотреть баланс

- **Per-customer:** Contacts → клиент → smart button "Loyalty Cards" / "Coupons" → code, balance, history.
- **Per-program:** Sales → Products → Gift cards & eWallet → eWallet → smart button "eWallets" → список карт.
- **In POS:** при поиске клиента в "Choose Customer" видно `eWallet: N €` справа от имени.

### 3.8. Как применить eWallet при продаже (POS UI)

Клиент выбран → товары в корзине → кнопка ⋮ (три точки) рядом с Note → пункт Rewards/eWallet → строка-минус автоматически в корзине → Total пересчитывается. **Это reward-механика на cart screen, НЕ payment method на payment screen.**

### 3.9. Хронологические правила (нельзя нарушать)

1. **Top-up product активируется в POS ТОЛЬКО ПОСЛЕ создания loyalty.program.** Иначе ghost liability на 438 без карты (происходило 2026-04-21 до фикса — 230€ очищено через mass delete).
2. **Top-up и discount product → 438 Anticipos + tax 0%** (multipurpose voucher, EU Directive 2016/1065). VAT начисляется при редемпции на конкретный товар, не при выдаче ваучера.
3. **`applies_on=future`** — клиент не может топнуть и потратить в одном чеке (защита от race condition).

### 3.10. Setup-процедура (если нужно создать новую loyalty программу)

1. Создать top-up product с `available_in_pos=False`.
2. Создать `loyalty.program` (type eWallet или Gift Card), привязать top-up через `trigger_product_ids`.
3. Создать `discount_line_product_id` (или подтвердить что Odoo создал автоматически), выставить Income Account 438.
4. Только теперь — `available_in_pos=True` на top-up product.
5. Reload POS session (frontend кеширует config).

---

## 4. Роли в бизнесе

### 4.1. Лицензирование

**Принцип:** минимум полных Odoo-лицензий, максимум работы через планшет + PIN.

| Роль | Odoo-доступ | Устройство | Авторизация |
|---|---|---|---|
| **Флорист** | Без личной учётки | Планшет на стене + телефон + сканер (приоритет) | PIN + смена |
| **Главный флорист / Manager** | Жена + директор — **полный backend** ИЛИ extended PIN | Десктоп / планшет | Учётка ИЛИ PIN |
| **Логист** | Полная учётка | Планшет / телефон / десктоп | Odoo creds |
| **Бухгалтер** | Полная учётка | Десктоп | Odoo creds |
| **Владелец / аналитик** | Полная учётка + admin | Всё | Odoo creds |

### 4.2. Шифт-модель

- Сотрудник регистрируется на начало смены (`hr.attendance` или custom).
- На POS в выпадающем списке продавцов — **только те, кто на смене**.
- Продажа / онлайн-заказ / приёмка / списание → привязано к смене конкретного сотрудника.

**Модули установлены 2026-04-19:** `pos_hr` (PIN), `hr_attendance` (check-in/check-out через Kiosk Mode), `base_geolocalize` (dependency).

### 4.3. Флорист — что делает на планшете

**Главный принцип:** флорист — не «пользователь Odoo», а **оператор быстрых процессов**. Минимум кликов, максимум сканирования и фото.

**Операции:**
- Продажа через POS (сканирование штрихкода — основной сценарий).
- Сборка букета (см. § 2).
- Приёмка товара (см. [03_inventory § Receipt](03_inventory_pipeline.md)).
- Списание с фото-согласованием (см. § 5).
- Системные задания от Odoo (см. § 7).

**Привязка к сотруднику:**
- При каждой продаже PIN-код подтверждает «кто продал».
- Список ограничен теми, кто на активной смене.

### 4.4. Логист — закупка → приёмка → оплата

**Закупка:**
- Быстрый выбор поставщика, поиск товара (SKU / name / `x_studio_codigo_fabrica` / learned vendor code).
- Указание qty в разных единицах (пачки / штуки).
- Опционально — распределение по магазинам.
- Цена может меняться день ко дню.
- Учёт особенностей: один товар у разных поставщиков → разные артикулы / разное в пачке / разная цена. Подаренные единицы — отдельный учёт.

**Связь с приёмкой флориста (формулировка владельца):**
> «Дорогой флорист, мы тут тебе помогли и уже посчитали… но ВСЁ РАВНО ВСЁ ПЕРЕСЧИТАЙ САМ»

`x_studio_expected_qty` — подсказка флористу, **не факт**. Флорист обязан пересчитать сам. См. [03_inventory § Sentinel -1](03_inventory_pipeline.md).

**Контроль поставщиков:**
- Недопоставки (paper > actual).
- Пересортица.
- Расхождения по цене (paper vs factura/bill).
- Подаренные единицы.
- Случаи, когда логист увидел проблему в пути ещё до магазина.

**Распределение по магазинам:** поддерживаем оба варианта — **в момент закупки** (логист сразу разносит части одного albarán на 2-3 склада) **ИЛИ вторым документом** (сначала всё на один warehouse, потом internal transfer). Зависит от потребности логиста и конкретной ситуации.

**Open для логиста:**
- ❓ Финальный UX (планшет vs телефон vs десктоп).
- ❓ Видит ли логист состояние vendor bill / оплаты, или только закупка→приёмка.
- ❓ Фиксация причины расхождения (поставщик / транспорт / разбилось / простили).

### 4.5. Бухгалтер — три задачи

1. **Sales reconciliation** — POS sessions × Telegram-чаты магазинов × банковские поступления. Сейчас вручную, цель — автоматический workflow.
2. **Expense pipeline + испанская категоризация** — счета (аренда, коммуналка) → PGCE PYMEs 2008 → оплата → сбор фактур → Modelo 303/347/349.
3. **Супервайзинг цикла** — закупили → привезли → распаковали → ценники → витрина → продажа. В Holded требовал отдельный Google Sheets, в Odoo цель — Kanban view.

См. [01_project § 5.7 Бухгалтерия](01_project.md) для статуса.

---

## 5. Списание (scrap) — workflow с фото-согласованием

### 5.1. Принцип (бизнес-инвариант)

**Списание без фото-согласования главного флориста = НЕ списание.** Альтернатива — забытые списания и неотслеживаемые потери.

### 5.2. Процесс

1. **Флорист:** выбирает позиции → фото-доказательство → указывает тип списания → отправляет на согласование.
2. **Главный флорист / Manager** (жена / директор): notification → проверка → подтверждение или отклонение.
3. После подтверждения → списание со склада.

### 5.3. Типы списания

- **Завял** (естественная порча).
- **Сломался** (механическое повреждение).
- **Потерян** (не найден в инвентаризации).
- **Ушёл в mix / пересортица** (с одной карточки, оприходован на другую).
- **Забыт к списанию** (списание задним числом — индикатор процессной проблемы).

### 5.4. Реализация (закрывается штатно на Online)

Не custom модуль, а связка native Odoo 19:

1. **Quality Control Point** на operation type «Scrap» → `Take a Picture` check (обязательное фото). [Docs](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/quality/quality_check_types/picture_check.html).
2. **Approvals app** — тип «Stock Write-off», approver = главный флорист.
3. **Server Action** на `stock.scrap.action_validate`: проверяет что есть quality.check pass + approval approved → иначе блокирует.
4. **Studio:** selection-поле «Тип списания» (5 значений выше).

**Полный 1-click flow с tier-validation** — нужен OCA `stock_scrap_tier_validation` → требует Odoo.sh.

### 5.5. Кто инициирует

**Обычный флорист инициирует списание сам** — выбирает позицию, делает фото-фиксацию, отправляет на approval. Главный флорист одобряет/отклоняет. Это часть workflow выше (§ 5.2), решено явно: не «только главный инициирует», а **«обычный → фото → approval»**.

### 5.6. Open

- ❓ Notification главному флористу о pending approval — Odoo activity / Telegram / email.

---

## 6. Бонусная модель

**Status:** 🟡 CONCEPT — модель согласована, **коэффициенты калибруются после сбора реальных данных**.

### 6.1. Структура зарплаты флориста

| Компонент | Сумма / правило |
|---|---|
| **Базовая ставка** | **900 €** — гарантировано всегда |
| **Минимум гарантии** | **1400 €** (минимум Испании) — если личные бонусы не дотягивают, доплачиваем до 1400, **но ставим флориста на карандаш** |
| **Личные бонусы** | От 0 до ∞ — всё сверх 1400 идёт сверху |

### 6.2. Что входит в 900 € (без бонусов)

- Приём цветов, физическая приёмка.
- Мытьё холодильников, чистка витрин, уборка.
- Открытие/закрытие магазина.
- Системные задания (пересчёт, фото-отчёты).
- Сборка букетов на витрину **без продажи** (если флорист собрал но не продал — маркер 7864 авто-вставлен с 0€, бонуса нет).

### 6.3. Что даёт личный бонус

**Все продажи, привязанные к сотруднику:**
- Offline через POS (любой из 3 магазинов).
- Online: Flowwow / Glovo / WhatsApp / Instagram / сайт.
- Сборка букета **с самостоятельно добавленным маркером 5€** → бонус.

**Принципы:**
- **Личные, не коллективные.** Флорист конкурирует, не делит смену (см. [01_project § 4.3](01_project.md)).
- **Работает во всех каналах:** offline POS + online.
- **Индикатор проблем:** стабильно только 900 € → флаг «не справляется» → разбор → возможно увольнение.

### 6.4. Калибровка (3 этапа)

1. **Сейчас (запуск):** без формул, только сбор данных (personal sales report).
2. **2-3 месяца работы:** анализируем — средняя производительность, верхний/нижний квартили.
3. **Моделирование коэффициентов:** не переплатить (маржа), не демотивировать (топ-флористы).
4. **Запуск формулы во все каналы.**

### 6.5. Технические предпосылки (без них модель не работает)

- ✅ `hr.employee` с PIN (есть).
- 🔴 `hr.attendance` или custom shift-model с регистрацией начала смены.
- 🔴 PIN-авторизация на каждой продаже.
- 🔴 Personal sales report (per-employee dashboard).
- 🔴 Единая воронка online-заказов с идентификацией обработчика.

---

## 7. Системные задания (smart tasks for shops)

**Принцип:** Odoo активно выдаёт магазину задачи, не только принимает действия.

### 7.1. Типы заданий

- **Частичная инвентаризация:** «пересчитать розы / SKU XYZ».
- **Rolling correction:** при первой продаже твёрдого товара (ваза, декор) — задание пересчитать SKU в магазине. Не блокер продажи, параллельная задача.
- **Срочная перепечатка ценника** (товар изменил цену → старый ценник на витрине устарел).
- **Фото-отчёт:** «помой холодильник + пришли фото», «проверь ценники наклеены — пришли фото».
- **Push-уведомление о прибытии товара:** «едет поставка №X, приготовься».
- **Привлечение внимания планшета** к срочной задаче (всплывающий badge / звук).

### 7.2. Реализация (закрывается штатно на Online)

1. **Project recurring tasks** ([docs](https://www.odoo.com/documentation/19.0/applications/services/project/tasks/recurring_tasks.html)) — repeat every, новая task при закрытии предыдущей.
2. **Assignee** = `res.users` (через `hr.employee.user_id`).
3. **Studio Image field** на task для photo proof (на мобиле HTML5 input → камера).
4. **Server Action constraint** на close: блокировать если `attachment_ids = []`.
5. **Activities + automated reminders** через Mail (escalation 3 часа без действия).
6. **Maintenance app** для холодильников (equipment) → maintenance request с photo proof.

### 7.3. POS-integration

- ✅ Backend Activities виден florисту при открытии Odoo (но не в POS UI).
- 🔴 **Task badge внутри POS UI на смене** — требует Odoo.sh + custom OWL widget.

---

## 8. CRM и клиенты

### 8.1. Зачем

Цветочный бизнес — **emotional, high-repeat, relationship-driven**. Клиенты возвращаются на личные даты (ДР, годовщины, 8 марта). Цель CRM: каждая продажа = начало long-term relationship, не разовая транзакция.

### 8.2. Клиентская карточка (через `res.partner`)

**Базовые данные** (штатно):
- Имя, телефон, email, адрес доставки.
- Канал привлечения (offline / Flowwow / Glovo / Instagram / сайт / рекомендация).
- Дата первой покупки.
- История заказов (через `partner_id`).

**Важные персональные даты** (через Studio fields):
- ДР клиента.
- ДР / годовщины близких (жена, мама, дочь).
- Прочие «он дарит цветы X раз в году».

### 8.3. Сегменты (план — после 2-3 месяцев данных)

- **VIP** (топ-20% по обороту).
- **Regular** (2+ покупки за квартал).
- **Dormant** (не покупал 3+ месяца) — риск потери.
- **New** (первая-вторая покупка) — нужна wow-экспа.

### 8.4. Лояльность

**Сейчас:** eWallet (см. § 3) как baseline. **Дальше:**
- Loyalty Cards program (баллы за покупки, отдельная `loyalty.program type=loyalty`).
- Персональные скидки.

### 8.5. Привязка клиента в POS

**Быстрый лукап:**
- По номеру телефона (самый частый).
- По имени (если флорист знает).
- По QR-карте лояльности.

**Не замедлять флориста:** новый клиент → быстрое создание (только телефон, остальное потом). Анонимный → продажа без привязки. Кнопка «добавить этого клиента сейчас» на чеке после продажи.

### 8.6. Каналы рассылок (план)

| Канал | Использование |
|---|---|
| **Email** | Новости, сезонные предложения |
| **WhatsApp** | Персональные напоминания, статус заказа |
| **SMS** | Срочные алерты (готов заказ, курьер выехал) |
| **Telegram** | Если клиент активен |
| **Instagram** | Визуальные промо через DM |

**Принципы:** opt-in по каналам, частота умеренная (1-2/месяц), персональный контент > массовый.

### 8.7. Open для CRM

| # | Что | Статус |
|---|---|---|
| 8.7.1 | Базовая клиентская карточка через POS | ✅ |
| 8.7.2 | История покупок | 🟡 (штатно, причесать view) |
| 8.7.3 | Сегментация (VIP/Regular/Dormant/New) | 🔴 |
| 8.7.4 | Email-рассылки через mass.mailing | 🔴 |
| 8.7.5 | Loyalty Cards program | 🔴 |
| 8.7.6 | WhatsApp интеграция | ❓ (Wati / 360dialog / custom) |
| 8.7.7 | Напоминания о датах | 🔴 (через `mail.activity` + scheduler) |
| 8.7.8 | GDPR compliance (opt-in, right to deletion) | 🔴 |
| 8.7.9 | Подписочные модели (букет/неделю) | ❓ |
| 8.7.10 | Партнёрские программы / реферралы | ❓ |

---

## См. также

- [01_project.md](01_project.md) — бизнес, архитектурные истины, roadmap, ideal state.
- [99_invariants.md](99_invariants.md) — правила работы + Odoo 19 gotchas.
- [03_inventory_pipeline.md](03_inventory_pipeline.md) — приёмка (детали ввода флориста, calculate_in_shop).
- [02_makecom_bot.md](02_makecom_bot.md) — Make.com бот (учит vendor codes, заполняет `x_studio_supplier_sku/expected_qty/item_comment`).
- [05_catalog.md](05_catalog.md) — миграция каталога (откуда берутся product.template).
- [07_state_snapshot.md](07_state_snapshot.md) — текущие prod-цифры (sessions, JE, etc).
