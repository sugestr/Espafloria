<!-- v: 3 | updated: 2026-05-02T23:30Z -->
# 07. Current state snapshot

**Что в файле:** живой снимок системы — конкретные ID, цифры, состояния. Обновляется при крупных изменениях. Это «фото на сегодня», не история.

> 📌 Архитектурные правила и принципы — в тематических файлах (01-06, 99). Здесь — только factual snapshot.

---

## 1. Сводка по сущностям

| Модель | Всего | Примечание |
|---|---|---|
| `product.template` | **2142** | 2115 нормированных карточек в карантине (`categ_id child_of 207`) + 27 служебных вне карантина (eWallet/Gift Card/Deposit/Discount/Tips/Anticipo/Down Payment/Settle/DUA VAT/Booking Fees/маркер букета/делivery/2 archived legacy) |
| `product.product` (variants) | **2144** | в основном 1:1 с template (flat), несколько multivariant |
| `product.category` | **80+** | 287 Flores Cortadas root + 288/289/290 subcat + 207 ⛔ Карантин Holded |
| `purchase.order` | **188** | re-imported из Holded (все state=draft, ждут reconciliation через action 1217). VERDNATURA LEVANTE SL — основной поставщик |
| `purchase.order.line` | 1000+ | По строкам pedido |
| `product.supplierinfo` (learned codes) | **0** | будет наполняться при reconciliation pedidos |
| `stock.picking` / `stock.move` / `stock.move.line` | **0** | пусто — pedidos не подтверждены |
| `stock.quant` | **0** | пусто (был UPDATE quantity=0 + DELETE при wipe) |
| `pos.session` / `pos.order` / `pos.payment` | **0** | пусто после wipe тестовых данных |
| `account.move` / `account.payment` | **0** | пусто |
| `sale.order` | **0** | пусто |
| `loyalty.card` / `loyalty.history` | **0** | пусто (программа eWallet активна, карт ещё нет) |
| `res.partner` | **15** | Espafloria, Andriy, 4 поставщика (SERVIFLOR 39, VERDNATURA 42, RILLO 43, DECORA 44, ParEx 57), POS Terminal 45, SCA GANADERA 49, Simplified Invoice ES 35, 🌹 Букет 53, 🤖 Claude AI 56, 2 future florist placeholders (46/47), 🚨REEMPLAZAR PROVEEDOR 38 |
| `stock.warehouse` | **4** | Plaza (2) / Gloria (3) / Blau (4) / Temporal (5) |
| `pos.config` | **3** | POS Plaza/Gloria/Blau — все на своих складах ✅ |
| `res.users` (internal) | **2** | Andriy (id=2 admin) + POS Terminal (id=5 kiosk) |
| `hr.employee` | **3** | Andriy (1), Mega Florist 1111 (10, pin 1111), 2 Florista Test (11, pin 2222) |
| `base.automation` (активных) | **5** | Review info (1), Auto migrate v2 (6), Bouquet POS→SO (10), Bouquet dismantle picking (11), Bouquet safety net pos.order (12) |
| `ir.actions.server` custom | **7+** | 1145 (Migrate UI), 1146 (review_status), 1150 (calculate_in_shop), 1176 (Migrate execute v2.2), 1203 (Bouquet payment), 1209 (Bouquet dismantle), 1217 (reconcile finalize) — все mirror в `kb/add/` |
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
| 10 | Mega Florist 1111 | 1111 | future florist placeholder |
| 11 | 2 Florista Test | 2222 | future florist placeholder |

---

## 5. Catalog migration state

После reset каталог содержит **только нормированные карточки в карантине** + 27 служебных вне карантина. Migration toolkit v2.2 (UI trigger + automation + execute) на месте, но мигрированных карточек 0 — миграция начнётся заново после готовности target skeletons.

| Статус | Количество |
|---|---|
| В карантине (`categ_id child_of 207`) — нормированные карточки от Holded | **2115** |
| Служебные вне карантина (eWallet, Gift Card, Discount, Deposit, маркер букета, Tips, Anticipo, DUA VAT, Settle, Booking Fees, delivery, archived legacy) | **27** |
| `x_studio_migration_status='migrated'` (target) | **0** |
| Migration toolkit (1145, 1176, automation 6, x_studio_migrate_now flag) | ✅ ready |

**Category tree:**
```
287 Flores Cortadas
├── 288 Rosa Uniflora
├── 289 Ramas y Follaje
└── 290 Flores Variadas

286 Deliveries
291 Espafloria Internal (маркер букета 7848 + archived 7849)
292 Embalaje
207 ⛔ Карантин Holded — 2115 templates
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
| 1145 | Migrate UI trigger v2 | product.template | `add/05_migrate_variant_action.py` |
| 1146 | Review → generate info conclusion | stock.move | `add/03_review_status_automation.py` |
| 1150 | calculate_in_shop | stock.picking | `add/03_calculate_in_shop_action.py` |
| 1176 | Migrate execute v2.2 | product.product | `add/05_migrate_variant_v2.2.py` |
| 1203 | Bouquet on payment (4 ветки) | pos.order | `add/04_bouquet_on_payment_action.py` |
| 1205 | Bouquet on stock.picking (deprecated) | stock.picking | `add/04_bouquet_on_picking_action.py` |
| 1207 | Bouquet on pos.order paid (deprecated) | pos.order | `add/04_bouquet_on_order_paid_action.py` |
| 1209 | Bouquet dismantle | pos.order | `add/04_bouquet_on_dismantle_action.py` |

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

**0 записей** после wipe тестовых транзакций. Будут наполняться при reconciliation pedidos через action 1217 + reception_algorithm. До reset было 22 (16 старых + 6 скопированных миграцией) — git history.

---

## 11. Bill control state

| Метод | Количество template | Категории |
|---|---|---|
| `purchase` (On ordered) | ~900 | FLORES CORTADAS + PLANTAS EN MACETAS |
| `receive` (On received) | ~1085 | DECORACION, EMBALAJE, ENTREGA, PRODUCTOS ESPECIALES, Consumibles |

См. [03_inventory § 6](03_inventory_pipeline.md).

---

## 12. Pedido pipeline state

После full reset каталога + re-import albaranes из Holded:
- **188 purchase.order** — все 100% `state=draft`, supplier VERDNATURA LEVANTE SL (id=42).
- Last imported ID **47995**, `Holded albaran id: AC260511 Vendor ref:12561164`.
- 0 stock.picking / stock.move (pedidos не подтверждены).
- 0 product.supplierinfo (учёные vendor codes будут наполняться через reconciliation action 1217 + reception_algorithm).

---

## 13. Что делает систему живой прямо сейчас

1. **Make.com бот** — обрабатывает входящие документы в Telegram (активно).
2. **Holded** — параллельно основная система (до cutover).
3. **Odoo POS** — три кассы готовы (first-sale + eWallet prepayment + букетный flow ранее верифицированы end-to-end до wipe тестовых транзакций).
4. **Odoo catalog migration** — инфраструктура v2.2 работает, готова к новому циклу миграции (после reset 0 мигрированных).
5. **Odoo eWallet** — программа активна, ready для предоплат под букеты.
6. **Pedido reconciliation** — 188 albaranes импортированы из Holded в state draft, ждут прогона через reception_algorithm + action 1217.

---

## См. также

- [01_project.md](01_project.md) — бизнес и архитектурные истины.
- [02_makecom_bot.md](02_makecom_bot.md) — техдок бота.
- [03_inventory_pipeline.md](03_inventory_pipeline.md) — приёмка + bill control.
- [04_pos_and_roles.md](04_pos_and_roles.md) — POS, букеты, eWallet, роли (полная архитектура).
- [05_catalog.md](05_catalog.md) — миграция каталога (полный ID-registry).
- [06_infra.md](06_infra.md) — платформа и лимиты.
- [99_invariants.md](99_invariants.md) — правила работы.
