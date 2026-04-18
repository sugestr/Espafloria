<!-- v: 2 | updated: 2026-04-18T20:00Z -->
# 08. Current State Snapshot

**Дата:** 2026-04-18 (после hot-fix session)
**Цель:** фото системы в текущем состоянии, чтобы не путаться с планами и брифами.

---

## Сводка по сущностям

| Модель | Всего | Примечание |
|---|---|---|
| `product.template` | **1995** | Из них 1983 в карантине, 10 служебных, 12 в новом каталоге |
| `product.product` (variants) | — | Считать вручную, не меньше 1995 |
| `product.category` | **80+** | Root + 79 в `⛔ Карантин Holded` |
| `purchase.order` | **188** | ~90% draft с amount_total=0 (импортированные albaran без цен) |
| `purchase.order.line` | 1000+ | По строкам pedido |
| `stock.move` с review-данными | **6** | Первые реальные приёмки |
| `product.supplierinfo` (learned codes) | **16** | Только Verdnatura, все на `product_tmpl_id` (не variant) |
| `res.partner` (поставщики) | десятки | Видимые: Verdnatura (id=42), Serviflor (id=39) |
| `pos.config` | **3** | POS Plaza, Gloria, Blau (все active, все warehouse_id=2) |
| `base.automation` (активных) | **1** | «Review → generate info conclusion» (id=1) |
| `ir.actions.server` custom | **3** | 1145 (Migrate), 1146 (review_status), 1150 (calculate_in_shop) |

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

**Удалено:** `x_studio_expected_qty_2` (мусорное, «expected_qtyыыыы»).

> ℹ️ Счёт по документации на 2026-04-18 после hot-fix. Если фактически в Odoo 6 полей — отдельный worker со сверкой через Odoo MCP обновит.

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

**Удалено:** `x_studio_received_units`, `x_studio_expected_quantity`, `x_studio_supplier_unit` (дубли).

### `product.template` + `product.product` — **7 парных + 3 variant-only**
| Поле | Tmpl | Variant (related) | Назначение |
|---|---|---|---|
| `x_studio_codigo_fabrica` | ✅ | ✅ | Legacy supplier code from Holded |
| `x_studio_holded_url` | ✅ | ✅ | Ссылка на Holded |
| `x_studio_holded_created` | ✅ | ✅ | Дата создания |
| `x_studio_botanic_name` | ✅ | ✅ | Botanical tags (many2many → product.tag) |
| `x_studio_legacy_source` | ✅ | ✅ | Миграция: откуда приехала |
| `x_studio_target_variant` | ✅ | ✅ | Миграция: куда мигрировать |
| `x_studio_migration_status` | ✅ | ✅ | Статус (quarantine/mapped/migrated/archived) |
| `x_studio_migration_note` | — | ✅ | Текст-справка на target |
| `x_studio_variant_legacy_source` | — | ✅ | (product.product only) |
| `x_studio_variant_migration_status` | — | ✅ | (product.product only) |

**⚠️ Deprecated но не удалено (Studio protection):** `x_studio_many2many_field_4qh_1jkvk330u` (New Tags) — label переименован в `[DEPRECATED] New Tags`.

---

## Статистика миграции каталога

| Статус | Количество | Комментарий |
|---|---|---|
| В карантине (`categ_id child_of 207`) | **1983** | Ждут миграции |
| `sale_ok = False` на карантине | **1983 (100%)** | ✅ блокирует POS продажу |
| `x_studio_migration_status = 'quarantine'` | 0 | поле не заполнено (hot-fix не трогал) |
| `x_studio_legacy_source != False` | 0 | Миграции ещё не было |
| В новом каталоге (не карантин) | ~12 | Созданы вручную / ранее |

**Вывод:** migration toolkit готов, но **ещё ни одна карточка не мигрирована**. Работа впереди.

---

## Bill control policy (после hot-fix)

| Метод | Количество template | Категории |
|---|---|---|
| `purchase` (On ordered) | **~900** | FLORES CORTADAS + PLANTAS EN MACETAS |
| `receive` (On received) | **~1085** | Всё остальное: DECORACION, EMBALAJE, ENTREGA, PRODUCTOS ESPECIALES, Consumibles |

Проверить можно через:
```
Purchase → Products → фильтр purchase_method = "purchase"
```

---

## Bot активность (production traces)

**Последний реальный pedido в системе:**
- ID 34414, `Holded albaran id: AC260511 Vendor ref:12561164`
- Supplier: VERDNATURA LEVANTE SL (id=42)
- state: `purchase`, amount_total: 324.23 EUR
- date_order: 2026-03-29

**Примеры комментариев, оставленных ботом:**
```
цена 0€→3.06€. Código 199478. /26-Apr-14
цена 0€→8.82€. Código 38592. /26-Apr-14
⚠️ кол-во не совпало: pedido 25 шт→бумага 20 шт. цена 0.43€→0.73€. Código 199235. /26-Apr-14
```

Формат полностью соответствует шаблонам в `templates/make_line_log_*.txt`.

---

## `product.supplierinfo` (learned codes)

**Всего: 16 записей.** Все на `product_tmpl_id` (не variant). Все от VERDNATURA (partner_id=42).

**Примеры:**

| product_tmpl | product_code (learned) | product_name (from paper) | price | date_start |
|---|---|---|---|---|
| 7799 `[8400745] 🚫 FREESIA DOUBLE ROSARIO` | 63146 | Freesia Double Soleil, COLOR Amarillo, ALTURA 52 cm, PESO/TALLO 16 gr | 0.3 | 2026-03-30 |
| 7632 `[8400686] 🚫 RS ROSA - Miss Piggy` | 193815 | RS A2 Miss Piggy+, COLOR Coral, ALTURA 60 cm | 0.4 | 2026-03-30 |
| 7375 `[8400236] 🚫 TULIPAN - MIX` | 38839 | TUL Columbus Double, COLOR Rosa, ALTURA 38 cm, PESO/TALLO 34 gr | 0.4 | 2026-03-30 |

**Почему так мало?**
- Боевой массовый ввод документов ещё не проходил
- Большинство 188 pedido были draft-импортом без цен
- Learned codes создаются только когда бот успешно матчит новый codigo при reconciliation

Когда начнётся массовый импорт albaran — ожидаем рост до сотен/тысяч записей.

---

## Server actions (custom, не штатные)

| ID | Название | Model | Binding | Code file |
|---|---|---|---|---|
| 1145 | Migrate to selected variant | product.template | product form+list | `code/migrate_variant_action.py` |
| 1146 | Execute Code (review status) | stock.move | — (через automation) | `code/review_status_automation.py` |
| 1150 | calculate_in_shop | stock.picking | stock.picking list+form | `code/calculate_in_shop_action.py` |

---

## Active automations

| ID | Название | Model | Trigger | Watched fields (после hot-fix) |
|---|---|---|---|---|
| 1 | Review → generate info conclusion | stock.move | on_create_or_write | `quantity`, `x_studio_received_packs` |

**До hot-fix в watched было 4 поля** (также `picking_id`, `purchase_line_id`) → вызывало лишние срабатывания. После чистки — только те, что реально значимы для review.

---

## Integration health

**Make.com ↔ Odoo XML-RPC:**
- Используется старый XML-RPC (`Content-Type: text/xml`), не JSON-RPC и не MCP
- Работает через user API key
- 19 разных вызовов в scenario (см. [02_makecom_bot.md](02_makecom_bot.md))

**Holded → Odoo:**
- Фотки через Holded API `/products/{id}/image` (скрипт `code/image_import_from_holded_api.py`)
- Товары / категории / albaran через CSV import (вручную)

---

## Что делает систему живой прямо сейчас

1. **Make.com бот** обрабатывает входящие документы в Telegram (активно)
2. **Holded** параллельно используется как основная система (пока)
3. **Odoo** — всё ещё в режиме подготовки / миграции

С 20 апреля (MVP) запустится **параллельный режим** — операции одновременно в Holded и Odoo с постепенным переходом.

---

## См. также

- [01_business_context.md](01_business_context.md) — что это всё должно делать
- [CHANGELOG.md](CHANGELOG.md) — что менялось и когда
- [99_invariants.md](99_invariants.md) — правила, которые защищают это состояние
