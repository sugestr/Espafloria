<!-- v: 5 | updated: 2026-04-19T23:30Z -->
# 08. Current State Snapshot

**Дата:** 2026-04-19 (prod-сверка через Odoo MCP)
**Цель:** фото системы в текущем состоянии, чтобы не путаться с планами и брифами.

---

## Сводка по сущностям

| Модель | Всего | Примечание |
|---|---|---|
| `product.template` | **1995** | 1983 в карантине, 10 мигрированы сегодня, 12 в новом каталоге + 6 service templates |
| `product.product` (variants) | — | ~2000, в т.ч. 10 migrated variants |
| `product.category` | **80+** | + 4 новых сегодня (287 Flores Cortadas root + 288/289/290 subcat) |
| `purchase.order` | **188** | ~90% draft с amount_total=0 (импортированные albaran без цен) |
| `purchase.order.line` | 1000+ | По строкам pedido |
| `stock.move` с review-данными | **18** | IDs 461-478, большинство OK; выборка — в [03](03_odoo_receipt_review.md) |
| `product.supplierinfo` (learned codes) | **22** | 16 старых + 6 скопированных при миграции (на target templates) |
| `res.partner` (поставщики) | десятки | Видимые: Verdnatura (id=42), Serviflor (id=39) |
| `stock.warehouse` | **4** | Plaza/Gloria/Blau/Temporal (см. § A ниже) |
| `pos.config` | **3** | POS Plaza/Gloria/Blau — все на своих складах ✅ (config error починен 2026-04-19) |
| `res.users` (internal) | **2** | Andriy (id=2 admin) + POS Terminal (id=5 kiosk) |
| `hr.employee` | **3** | Andriy (1), Florista Test 1 (10), Florista Test 2 (11) |
| `pos.session` | 1 open | POS Plaza/00003 открыта 2026-04-19 14:26 UTC |
| `base.automation` (активных) | **2** | Review info conclusion (id=1), Auto migrate on flag v2 (id=6) |
| `ir.actions.server` custom | **4** | 1145 (Migrate UI trigger), 1146 (review_status), 1150 (calculate_in_shop), 1176 (Migrate execute v2.2) |

---

## A. Stock / Warehouse setup

4 active warehouses, каждый со своим stock location tree:

| ID | Name | Code | lot_stock_id | wh_input | wh_output |
|---|---|---|---|---|---|
| 2 | Plaza | PLA | 14 PLA/Stock | 15 PLA/Entrada | 17 PLA/Salida |
| 3 | Gloria | GLO | 20 GLO/Stock | 21 GLO/Entrada | 23 GLO/Salida |
| 4 | Blau | BLA | 26 BLA/Stock | 27 BLA/Entrada | 29 BLA/Salida |
| 5 | Temporal | TMP | 32 TMP/Stock | 33 TMP/Input | 35 TMP/Output |

**Plaza/Gloria/Blau** — 3 физические точки продаж. **Temporal (TMP)** — служебный/transit склад.

**Config fix 2026-04-19:** POS Gloria/Blau изначально были на `warehouse_id=2` (Plaza), и у POS Blau был неправильный `picking_type_id=27` (Gloria). Причина: кассы создавались когда склады Gloria и Blau уже существовали, но Odoo не проставил warehouse автоматически (поле скрыто из UI в Odoo 19, onchange при смене operation type не срабатывает). Починено:
- `picking_type_id` — через UI (Configuration → Settings → Inventory → Operation Type)
- `warehouse_id` — через прямой RPC write (поле hidden из UI)

---

## B. POS configuration (3 cashiers operational)

| POS | ID | warehouse | picking_type | module_pos_hr | cash_control | advanced_employees | basic | minimal |
|---|---|---|---|---|---|---|---|---|
| POS Plaza | 1 | Plaza (2) | Plaza: Pedidos de TPV (18) | ✅ | ✅ | [10, 11, 1] | [] | [] |
| POS Gloria | 2 | Gloria (3) | Gloria: Pedidos de TPV (27) | ✅ | ✅ | [10, 11, 1] | [] | [] |
| POS Blau | 3 | Blau (4) | Blau: Pedidos de TPV (36) | ✅ | ✅ | [10, 11, 1] | [] | [] |

**Payment methods:**

| ID | Name | type | journal | configs |
|---|---|---|---|---|
| 1 | Efectivo Plaza | cash | Efectivo Plaza (20, code EFPL) | [1] |
| 4 | Efectivo Gloria | cash | Efectivo Gloria (21, EFGL) | [2] |
| 5 | **Efectivo Blaus** | cash | Efectivo Blau (22, EFBL) | [3] |
| 2 | Tarjeta | bank | Bank (15) | [1, 2, 3] |
| 3 | Cuenta de cliente | pay_later | — | [1, 2, 3] |

Каждая касса cash-метод уникальный per-POS (Odoo constraint), одинаковый GL account `570001 Efectivo`, различаются по journal code для per-POS tracking бухгалтером. Tarjeta (bank) и Cuenta de cliente (pay_later) — shared between 3 configs.

⚠️ **Опечатка:** `pos.payment.method` id=5 = `Efectivo Blaus` (с лишней s). Journal `Efectivo Blau` правильный. Мелочь для cosmetic fix — см. [09](09_open_work.md).

**Employee rights (Odoo 19 `pos_hr`):**
- **minimal** — только продажи, без cash in/out, без закрытия смены
- **basic** — + cash in/out, + открытие смены
- **advanced** — + create product, + закрытие смены с пересчётом наличных, + управление конфигом через POS UI

Все 3 флориста (Andriy + 2 Test) в `advanced` на всех 3 POS → могут: открыть/закрыть смену, cash in/out (инкассация, личный вклад, «купил тряпки»), create product.

**Session state 2026-04-19 14:26 UTC:** POS Plaza/00003 open (запустил Andriy).

**POS categories (`pos.category`):** не настроены. Все 3 config: `iface_available_categ_ids=[]`, `limit_categories=false`. Это блокер для UX кассира (кассир не может быстро фильтровать по группам Rosas/Ramas/Plantas/Servicios) — см. [09 P0](09_open_work.md).

**Chrome vs Safari cache note:** POS PWA агрессивно кеширует конфиг в браузере. После изменения `advanced_employee_ids` или `module_pos_hr` — необходим **Reload Data** из гамбургер-меню (или Cmd+Shift+R). Эмпирически: Safari подхватывает быстрее, Chrome требует явный Reload.

---

## C. Users and access policies

| ID | login | name | groups | role |
|---|---|---|---|---|
| 2 | espafloria@gmail.com | Andriy Klymenko | [1 Internal User, 33 Administration settings, 88 POS Manager, + 18 функциональных] | admin (backend, POS manager, Studio) |
| 5 | pos_terminal@espafloria.local | POS Terminal | **только [1 Internal User, 87 POS / User]** | kiosk user для планшетов касс |

**Лицензий:** 3 оплачены. Использовано 2 (Andriy + POS Terminal). 3-я зарезервирована под бухгалтера.

**Политика POS Terminal:**
- **Цель** — dedicated non-admin user для планшетов во всех 3 магазинах. Если планшет украдут — у нападающего только доступ к POS-экрану, без admin-прав и без настроек.
- **Домашний экран** — home action = «POS Config Kanban». Даже если откроешь root URL `espafloriasl.odoo.com` — сразу видишь 3 плитки касс, а не website.
- **Email формат логина** (`pos_terminal@espafloria.local`) — требование Odoo. `.local` не резолвится нигде, почта никуда не уйдёт — это только технический формат.
- **Пароль** — был установлен как `PosTerminal2026!` при создании, рекомендовано сменить на финальный.

**hr.employee (работают на кассе через PIN в POS):**

| ID | name | pin | user_id | роль |
|---|---|---|---|---|
| 1 | Andriy Klymenko | false (снят 2026-04-19) | [2] | manager (advanced на всех POS) |
| 10 | 1 Florista Test | 1111 | — | test florist basic → advanced |
| 11 | 2 Florista Test | 2222 | — | test florist basic → advanced |

`hr.employee` **не занимает лицензию** — PIN-логин через `pos_hr` бесплатный. Каждая продажа прилипает к `pos.order.employee_id`, это фундамент будущей бонусной модели (см. [99 §33](99_invariants.md)).

**Модули установлены сегодня (2026-04-19):**
- `pos_hr` (pre-installed) — PIN-логин сотрудников в POS
- `hr_attendance` — check-in/check-out через Kiosk Mode (future: базовая зарплатная часть)
- `base_geolocalize` — dependency для hr_attendance (geo-tagging check-in)

**Закрытие смены workflow:**
- Basic employee — только пробивает чеки, не может закрывать смену
- Advanced employee — может Cash In/Out в середине смены (инкассация в банк, «купил тряпки за 20€»), закрывает смену с пересчётом наличных
- Смена при передаче (день→ночь): старый advanced закрывает (пересчёт, подпись), новый открывает новую. Это правильный financial discipline — никто один не может уйти с деньгами.

---

## D. Catalog migration state

**Инфраструктура v2.2 operational:**

| Объект | ID | Model | Роль |
|---|---|---|---|
| `ir.actions.server` | 1145 | product.template | UI trigger (Actions→Migrate). Mirror: `migrate_variant_action.py` |
| `ir.actions.server` | 1176 | product.product | Execute v2.2 (основная логика). Mirror: `migrate_variant_v2.2.py` |
| `base.automation` | 6 | product.product | `on_create_or_write`, watched `x_studio_migrate_now` (27133), filter migrate_now=True + target!=False + status!=archived, action [1176] |

Два пути запуска (паритет подтверждён): UI (через 1145) и MCP (напрямую update на variant). См. [06](06_catalog_migration_toolkit.md).

**Category tree (создано 2026-04-19):**

```
287 Flores Cortadas (root, NEW)
├── 288 Rosa Uniflora
├── 289 Ramas y Follaje
└── 290 Flores Variadas
```

**10 мигрированных карточек:**

| Статус | Количество | Комментарий |
|---|---|---|
| В карантине (`categ_id child_of 207`) | **1983** | Минус 10 ушли сегодня (6 deliveries + 4 flores) |
| `x_studio_migration_status='migrated'` (target) | **10** | 6840→7828 и ещё 5 deliveries; ROSA/MARFULL/CRISANTEMO/EUCALIPTO |
| `active=False` + `x_studio_migration_status='archived'` (source) | **10** | OLD_ префикс на SKU/barcode |
| В новом каталоге (не карантин) | ~22 | 12 ранее + 10 мигрированных |

**Post-migration TODOs:** bulk tax adjust, POS categories setup, POS tile visual test, Make.com bot OLD_ SKU awareness (см. [09](09_open_work.md), [02](02_makecom_bot.md)).

---

## Кастомные поля (после hot-fix)

### `purchase.order.line` — **5 полей**
| Поле | Тип |
|---|---|
| `x_studio_expected_qty` | float |
| `x_studio_item_comment` | char |
| `x_studio_operator_hit` | char |
| `x_studio_supplier_product_name` | char |
| `x_studio_supplier_sku` | char |

**Удалено:** `x_studio_expected_qty_2` (мусорное).

### `stock.move` — **9 полей**
| Поле | Тип | Related/Compute |
|---|---|---|
| `x_studio_paper_qty` | float | related `purchase_line_id.product_qty` |
| `x_studio_paper_unit` | many2one | related `purchase_line_id.uom_id` |
| `x_studio_expected_qty_info` | float | related `purchase_line_id.x_studio_expected_qty` |
| `x_studio_expected_qty_info_display` | char | compute |
| `x_studio_received_packs` | float | — |
| `x_studio_diff_vs_expected` | float | compute |
| `x_studio_avg_per_pack` | float | compute |
| `x_studio_review_status` | char | через automation |
| `x_studio_review_color` | integer | через automation |

### `product.template` + `product.product` — **7 парных + 3 variant-only + 1 flag**
| Поле | Tmpl | Variant (related) | Назначение |
|---|---|---|---|
| `x_studio_codigo_fabrica` | ✅ | ✅ | Legacy supplier code from Holded |
| `x_studio_holded_url` | ✅ | ✅ | Ссылка на Holded |
| `x_studio_holded_created` | ✅ | ✅ | Дата создания |
| `x_studio_botanic_name` | ✅ | ✅ | Botanical tags (many2many → product.tag) |
| `x_studio_legacy_source` | ✅ | ✅ | Миграция: откуда приехала (template.m2o → product.product) |
| `x_studio_target_variant` | ✅ | ✅ | Миграция: куда мигрировать |
| `x_studio_migration_status` | ✅ | ✅ | Статус (quarantine/mapped/migrated/archived) |
| `x_studio_migration_note` | — | ✅ | Текст-справка на target (append) |
| `x_studio_variant_legacy_source` | — | ✅ | (product.product only) |
| `x_studio_variant_migration_status` | — | ✅ | (product.product only) |
| `x_studio_migrate_now` | — | ✅ (id 27133) | **NEW 2026-04-19** boolean flag-trigger для automation 6 |

**⚠️ Deprecated но не удалено (Studio protection):** `x_studio_many2many_field_4qh_1jkvk330u` (New Tags) — label переименован в `[DEPRECATED] New Tags`.

---

## Bill control policy (после hot-fix)

| Метод | Количество template | Категории |
|---|---|---|
| `purchase` (On ordered) | **~900** | FLORES CORTADAS + PLANTAS EN MACETAS |
| `receive` (On received) | **~1085** | Всё остальное: DECORACION, EMBALAJE, ENTREGA, PRODUCTOS ESPECIALES, Consumibles |

---

## Bot активность (production traces)

**Последний реальный pedido в системе:**
- ID 34414, `Holded albaran id: AC260511 Vendor ref:12561164`
- Supplier: VERDNATURA LEVANTE SL (id=42)
- state: `purchase`, amount_total: 324.23 EUR
- date_order: 2026-03-29

**Формат комментариев соответствует шаблонам `make_line_log_*.txt`** — см. [02](02_makecom_bot.md).

---

## `product.supplierinfo` (learned codes)

**Всего: 22 записи.** 16 старых (на карантинных source template) + 6 скопированных автоматически при миграции 2026-04-19 (ID 299-305 на target templates 7834-7837, по dedup rule `(partner_id, product_code)`). Все от VERDNATURA LEVANTE SL (partner_id=42).

Примеры скопированных:
- 302-305 (CRISANTEMO 7836): product_codes 181190/199235/199939/197433
- 299 (ROSA 7834): 24547
- 300 (MARFULL 7835): из 110294
- 301 (EUCALIPTO 7837): UOM=Paquete (Усреднённый, id=31)

Когда начнётся массовый импорт albaran после MVP — ожидаем рост до сотен/тысяч записей.

---

## Server actions (custom, не штатные)

| ID | Название | Model | Binding | Code file |
|---|---|---|---|---|
| 1145 | Migrate to selected variant (UI trigger v2) | product.template | product form+list | `migrate_variant_action.py` |
| 1146 | Execute Code (review status) | stock.move | — (через automation 1) | `review_status_automation.py` |
| 1150 | calculate_in_shop | stock.picking | stock.picking list+form | `calculate_in_shop_action.py` |
| 1176 | Migrate: execute (v2.2) | product.product | — (через automation 6) | `migrate_variant_v2.2.py` |

---

## Active automations

| ID | Название | Model | Trigger | Watched fields |
|---|---|---|---|---|
| 1 | Review → generate info conclusion | stock.move | on_create_or_write | `quantity`, `x_studio_received_packs` |
| 6 | Auto migrate on flag (v2) | product.product | on_create_or_write | `x_studio_migrate_now` (27133) |

**Filter 6:** `[('x_studio_migrate_now', '=', True), ('x_studio_target_variant', '!=', False), ('x_studio_migration_status', '!=', 'archived')]`
**Action 6:** выполнить `ir.actions.server` 1176 (execute v2.2).

---

## Integration health

**Make.com ↔ Odoo XML-RPC:** 19 вызовов в scenario, 1 Worker bottleneck (см. [02](02_makecom_bot.md) и [07](07_infrastructure_devops.md)).

**Holded → Odoo:** фотки через Holded API (`legacy_migrations/image_import_from_holded_api.py`); товары/категории/albaran — CSV import.

---

## Что делает систему живой прямо сейчас

1. **Make.com бот** — обрабатывает входящие документы в Telegram (активно)
2. **Holded** — параллельно основная система (пока)
3. **Odoo POS** — первая сессия прошла end-to-end (ROSA RED NAOMI + IVA 10% = 4€ через Efectivo Plaza, ticket 261-1-000002)
4. **Odoo catalog migration** — инфраструктура v2.2 работает, 10 карточек переехали

С 20 апреля (MVP) — параллельный режим Holded + Odoo с постепенным переходом.

---

## См. также

- [01_business_context.md](01_business_context.md) — бизнес-цели, user stories
- [02_makecom_bot.md](02_makecom_bot.md) — бот + Make.com scenario
- [05_florists_logistics_accountant.md](05_florists_logistics_accountant.md) — роли и их процессы
- [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md) — migration v2.2
- [09_open_work.md](09_open_work.md) — TODO
- [99_invariants.md](99_invariants.md) — правила, §38-43 новые из сессии 2026-04-19
- [CHANGELOG.md](CHANGELOG.md) — что менялось когда
