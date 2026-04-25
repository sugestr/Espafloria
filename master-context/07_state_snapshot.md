<!-- v: 1 | updated: 2026-04-25T00:00Z -->
# 07. Current state snapshot

**Что в файле:** живой снимок системы — конкретные ID, цифры, состояния. Обновляется при крупных изменениях. Это «фото на сегодня», не история.

> 📌 Архитектурные правила и принципы — в тематических файлах (01-06, 99). Здесь — только factual snapshot.

---

## 1. Сводка по сущностям

| Модель | Всего | Примечание |
|---|---|---|
| `product.template` | **1995** | 1983 в карантине, 10 мигрированы, 12 в новом каталоге + 6 service templates + 2 eWallet (top-up + discount) |
| `product.product` (variants) | ~2000 | в т.ч. 10 migrated variants, 2 eWallet (7857 top-up, 7862 discount), 1 archived orphan (7860) |
| `product.category` | **80+** | + 4 новых (287 Flores Cortadas root + 288/289/290 subcat) |
| `purchase.order` | **188** | ~90% draft с amount_total=0 (импортированные albaran без цен) |
| `purchase.order.line` | 1000+ | По строкам pedido |
| `stock.move` с review-данными | **18** | IDs 461-478 |
| `product.supplierinfo` (learned codes) | **22** | 16 старых + 6 скопированных при миграции |
| `res.partner` (поставщики) | десятки | Видимые: Verdnatura (id=42), Serviflor (id=39) |
| `stock.warehouse` | **4** | Plaza (2) / Gloria (3) / Blau (4) / Temporal (5) |
| `pos.config` | **3** | POS Plaza/Gloria/Blau — все на своих складах ✅ |
| `res.users` (internal) | **2** | Andriy (id=2 admin) + POS Terminal (id=5 kiosk) |
| `hr.employee` | **3** | Andriy (1), Florista Test 1 (10), Florista Test 2 (11) |
| `pos.session` | varies | Закрываются после тестов; auto-opening_control контролировать |
| `base.automation` (активных) | **5** | Review info (1), Auto migrate v2 (6), Bouquet POS→SO (10), Bouquet dismantle picking (11), Bouquet safety net pos.order (12) |
| `ir.actions.server` custom | **7** | 1145 (Migrate UI), 1146 (review_status), 1150 (calculate_in_shop), 1176 (Migrate execute v2.2), 1203 (Bouquet payment), 1205 (Bouquet stock.picking — automation 11/12 disabled), 1209 (Bouquet dismantle) |
| `loyalty.program` | **1** | id=2 «eWallet», все 3 POS, EUR |

---

## 2. Stock / Warehouse

| ID | Name | Code | lot_stock_id | wh_input | wh_output |
|---|---|---|---|---|---|
| 2 | Plaza | PLA | 14 PLA/Stock | 15 PLA/Entrada | 17 PLA/Salida |
| 3 | Gloria | GLO | 20 GLO/Stock | 21 GLO/Entrada | 23 GLO/Salida |
| 4 | Blau | BLA | 26 BLA/Stock | 27 BLA/Entrada | 29 BLA/Salida |
| 5 | Temporal | TMP | 32 TMP/Stock | 33 TMP/Input | 35 TMP/Output |

**Plaza/Gloria/Blau** — 3 физические точки. **Temporal (TMP)** — служебный/transit склад.

---

## 3. POS configuration

| POS | ID | warehouse | picking_type | advanced_employees |
|---|---|---|---|---|
| POS Plaza | 1 | Plaza (2) | Plaza: Pedidos de TPV (18) | [10, 11, 1] |
| POS Gloria | 2 | Gloria (3) | Gloria: Pedidos de TPV (27) | [10, 11, 1] |
| POS Blau | 3 | Blau (4) | Blau: Pedidos de TPV (36) | [10, 11, 1] |

**Payment methods** (см. [04_pos_and_roles § 1.2](04_pos_and_roles.md)):

| ID | Name | type | journal | configs |
|---|---|---|---|---|
| 1 | Efectivo Plaza | cash | Efectivo Plaza (20, EFPL) | [1] |
| 4 | Efectivo Gloria | cash | Efectivo Gloria (21, EFGL) | [2] |
| 5 | Efectivo Blaus | cash | Efectivo Blau (22, EFBL) | [3] |
| 2 | Tarjeta | bank | Bank (15) | [1, 2, 3] |
| 3 | Cuenta de cliente | pay_later | — | [1, 2, 3] |
| 6 | 🌹 Собрать / изменить букет | bank (technical) | Bouquet Internal (24) | [1, 2, 3] |
| 8 | 🗑 Разобрать букет | bank (technical) | Bouquet Internal (24) | [1, 2, 3] |

---

## 4. Users and access

| ID | login | groups | роль |
|---|---|---|---|
| 2 | espafloria@gmail.com | [1, 33, 88, +18] | Andriy admin |
| 5 | pos_terminal@espafloria.local | [1, 87] | POS Terminal kiosk |

**hr.employee:**

| ID | name | pin | роль |
|---|---|---|---|
| 1 | Andriy Klymenko | false | manager |
| 10 | 1 Florista Test | 1111 | test florist |
| 11 | 2 Florista Test | 2222 | test florist |

---

## 5. Catalog migration state

**10 мигрированных карточек** (см. [05_catalog § 8](05_catalog.md) для полной таблицы):

| Статус | Количество |
|---|---|
| В карантине (`categ_id child_of 207`) | 1983 (минус 10 ушли) |
| `x_studio_migration_status='migrated'` (target) | 10 |
| `active=False` + `archived` (source) | 10 |
| В новом каталоге (не карантин) | ~22 (12 ранее + 10 мигрированных) |

**Category tree:**
```
287 Flores Cortadas
├── 288 Rosa Uniflora
├── 289 Ramas y Follaje
└── 290 Flores Variadas

286 Deliveries
207 ⛔ Карантин Holded
```

---

## 6. eWallet

**Programма** id=2, `program_type=ewallet`, EUR, все 3 POS.

| Product ID | Name | Income Account |
|---|---|---|
| 7857 | Top-up eWallet | 438000 Anticipos |
| 7862 | eWallet (discount) | 438000 Anticipos |
| 7860 | eWallet (orphan) | archived |

JE 19/20/21 верифицированы (Tata 100€ + redemption 3€). См. [04_pos § 3](04_pos_and_roles.md).

---

## 7. Server actions custom

| ID | Название | Model | Snapshot file |
|---|---|---|---|
| 1145 | Migrate UI trigger v2 | product.template | `migrate_variant_action.py` |
| 1146 | Review → generate info conclusion | stock.move | `review_status_automation.py` |
| 1150 | calculate_in_shop | stock.picking | `calculate_in_shop_action.py` |
| 1176 | Migrate execute v2.2 | product.product | `migrate_variant_v2.2.py` |
| 1203 | Bouquet on payment (4 ветки) | pos.order | `bouquet_on_payment_action.py` |
| 1205 | Bouquet on stock.picking (deprecated) | stock.picking | `bouquet_on_picking_action.py` |
| 1207 | Bouquet on pos.order paid (deprecated) | pos.order | `bouquet_on_order_paid_action.py` |
| 1209 | Bouquet dismantle | pos.order | `bouquet_on_dismantle_action.py` |

---

## 8. Active automations

| ID | Название | Model | Trigger | Watched fields |
|---|---|---|---|---|
| 1 | Review → generate info conclusion | stock.move | on_create_or_write | `quantity`, `x_studio_received_packs` |
| 6 | Auto migrate on flag (v2) | product.product | on_create_or_write | `x_studio_migrate_now` (27133) |
| 10 | Bouquet POS→SO on payment | pos.order | on_create_or_write | (триггер 1203) |
| 11 | Bouquet dismantle cancel POS picking | stock.picking | (disabled) | — |
| 12 | Bouquet dismantle safety net on pos.order paid | pos.order | (disabled) | — |

**Filter automation 6:** `[('x_studio_migrate_now', '=', True), ('x_studio_target_variant', '!=', False), ('x_studio_migration_status', '!=', 'archived')]`.

---

## 9. Кастомные поля (после hot-fix)

### 9.1. `purchase.order.line` — 5 полей

| Поле | Тип |
|---|---|
| `x_studio_expected_qty` | float |
| `x_studio_item_comment` | char |
| `x_studio_operator_hit` | char |
| `x_studio_supplier_product_name` | char |
| `x_studio_supplier_sku` | char |

**Удалено:** `x_studio_expected_qty_2` (мусорное).

### 9.2. `stock.move` — 9 полей

См. [03_inventory_pipeline § 2](03_inventory_pipeline.md).

### 9.3. `product.template` + `product.product` — 7 парных + 3 variant-only + 1 flag

См. [05_catalog § 10](05_catalog.md).

**⚠️ Deprecated:** `x_studio_many2many_field_4qh_1jkvk330u` («[DEPRECATED] New Tags»), Studio protection не даёт удалить.

---

## 10. `product.supplierinfo` (learned codes)

**Всего: 22 записи.** 16 старых на карантинных source template + 6 скопированных при миграции (ID 299-305 на target templates 7834-7837). Все от VERDNATURA LEVANTE SL (partner_id=42).

Примеры скопированных:
- 302-305 (CRISANTEMO 7836): product_codes 181190/199235/199939/197433.
- 299 (ROSA 7834): 24547.
- 300 (MARFULL 7835): из 110294.
- 301 (EUCALIPTO 7837): UOM=Paquete (Усреднённый, id=31).

При массовом импорте albaran ожидаем рост до сотен/тысяч.

---

## 11. Bill control state

| Метод | Количество template | Категории |
|---|---|---|
| `purchase` (On ordered) | ~900 | FLORES CORTADAS + PLANTAS EN MACETAS |
| `receive` (On received) | ~1085 | DECORACION, EMBALAJE, ENTREGA, PRODUCTOS ESPECIALES, Consumibles |

См. [03_inventory § 6](03_inventory_pipeline.md).

---

## 12. Последний реальный pedido в системе

- ID 34414, `Holded albaran id: AC260511 Vendor ref:12561164`
- Supplier: VERDNATURA LEVANTE SL (id=42).
- state: `purchase`, amount_total: 324.23 EUR.
- date_order: 2026-03-29.

---

## 13. Что делает систему живой прямо сейчас

1. **Make.com бот** — обрабатывает входящие документы в Telegram (активно).
2. **Holded** — параллельно основная система (до cutover).
3. **Odoo POS** — три кассы прошли first-sale + eWallet prepayment chain end-to-end + букетный flow (4 ветки) end-to-end.
4. **Odoo catalog migration** — инфраструктура v2.2 работает, 10 карточек переехали.
5. **Odoo eWallet** — программа активна, готова принимать предоплаты под букеты на заказ.

---

## См. также

- [01_project.md](01_project.md) — бизнес и архитектурные истины.
- [02_makecom_bot.md](02_makecom_bot.md) — техдок бота.
- [03_inventory_pipeline.md](03_inventory_pipeline.md) — приёмка + bill control.
- [04_pos_and_roles.md](04_pos_and_roles.md) — POS, букеты, eWallet, роли (полная архитектура).
- [05_catalog.md](05_catalog.md) — миграция каталога (полный ID-registry).
- [06_infra.md](06_infra.md) — платформа и лимиты.
- [99_invariants.md](99_invariants.md) — правила работы.
