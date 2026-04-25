<!-- v: 1 | updated: 2026-04-25T00:00Z -->
# 00. Master Index — Espafloria Odoo

**Owner:** Andriy
**Company:** Espafloria SL (Barcelona, цветочный бизнес)
**Platform:** Odoo Online (SaaS) Custom — `espafloriasl.odoo.com`

---

## Зачем эта база

Knowledge base для проекта автоматизации Espafloria. Цель — в любой момент ответить:
- Что уже работает в проде?
- Какие архитектурные решения приняты и почему?
- Где источник правды по каждой сущности?
- Какие правила нельзя нарушать?
- Что ещё хотим / не сделано / на обсуждении?

Содержимое: **тех-документация** уже сделанного + **контекст хотелок** + **правила работы AI/инженера**.

---

## Карта файлов

| # | Файл | Что содержит | Когда читать |
|---|---|---|---|
| 00 | `00_index.md` | Этот файл — навигация, глоссарий, статусы | Всегда первым |
| **01** | **`01_project.md`** | **Бизнес + архитектурные истины + vision + roadmap + wishlist** | **Большая картина** |
| 02 | `02_makecom_bot.md` | Make.com Telegram бот: OCR + reconciliation + diagnostics + bot rules | Правки бота, debugging pedido |
| 03 | `03_inventory_pipeline.md` | Приёмка (`stock.move` review) + bill control + backorder | Работа с приёмкой, флорист UX, bill policy |
| **04** | **`04_pos_and_roles.md`** | **POS техдок + букеты (полная reserve-model) + eWallet (полная архитектура) + роли + бонусы + CRM + scrap** | **Любая POS работа** |
| 05 | `05_catalog.md` | Миграция каталога v2.2 (UI trigger + automation + execute) | Миграция карточек, новый каталог |
| 06 | `06_infra.md` | Odoo Online Custom + лимиты + установленные модули + испанский compliance | Планирование нагрузок, миграция платформы |
| 07 | `07_state_snapshot.md` | Живой снимок prod (ID, цифры, состояния) | Перед массовыми операциями |
| 08 | `08_holded_archive.md` | Бета-миграция Holded + .py исходники | При боевой миграции (повтор бета-флоу) |
| 99 | `99_invariants.md` | 5 жёстких правил + 11 Odoo 19 gotchas | **Перед любыми изменениями** |
| — | `CHANGELOG.md` | Журнал изменений | После каждой правки |
| — | `CLAUDE.md` | Инструкции для AI/инженера (на корне репо, не в master-context/) | Старт сессии |
| — | `README.md` | Правила репо | Онбординг |

---

## Артефакты — на одном уровне с .md (плоский layout)

| Файл | Что это |
|---|---|
| `calculate_in_shop_action.py` | Mirror `ir.actions.server` id=1150 |
| `migrate_variant_action.py` | Mirror id=1145 (UI trigger v2) |
| `migrate_variant_v2.2.py` | Mirror id=1176 (execute v2.2) |
| `review_status_automation.py` | Mirror id=1146 |
| `bouquet_on_payment_action.py` | Mirror id=1203 (4 ветки) |
| `bouquet_on_dismantle_action.py` | Mirror id=1209 |
| `bouquet_on_picking_action.py` | Mirror id=1205 (deprecated, automation 11 disabled) |
| `bouquet_on_order_paid_action.py` | Mirror id=1207 (deprecated, automation 12 disabled) |
| `prompt_ocr_v1.txt` | OpenAI OCR extractor (модуль 3) |
| `prompt_reconciliation_v3.5.txt` | OpenAI reconciliation engine (модуль 149) |
| `prompt_diagnostics_v3.1.txt` | OpenAI diagnostics (модуль 167) |
| `make_line_log_pack.txt` | Make.com шаблон — пачечная ветка |
| `make_line_log_unit.txt` | Make.com шаблон — штучная ветка |
| `commit_worker_delivery.sh` | Коммит-скрипт worker'а (~3 KB) |

> Note: в Project knowledge точки в именах заменяются на `_` (`prompt_reconciliation_v3_5.txt` vs `v3.5.txt` в репо).

---

## Глоссарий

| Термин | Значение |
|---|---|
| **Pedido** | Purchase order в Odoo (= заказ поставщику) |
| **Albarán** | Товарная накладная поставщика (испанский документ) |
| **Factura** | Счёт-фактура (испанский документ) |
| **Receipt / Transfer** | `stock.picking` приёмки в Odoo |
| **Paper qty** | Количество по бумаге поставщика (`purchase.order.line.product_qty`) |
| **Logist qty** | Ожидаемое реальное количество по оценке логиста (`x_studio_expected_qty`) |
| **Actual qty** | Фактически принятое количество флористом (`stock.move.quantity`) |
| **Sentinel -1** | `quantity = -1` = «штуки не пересчитаны флористом» (отличать от `0` = реально ничего не приехало) |
| **Learned vendor code** | Выученный ботом маппинг supplier_sku → product variant (`product.supplierinfo.product_code`) |
| **Operator hit** | Ручная подсказка оператора для LLM-reconciliation (`x_studio_operator_hit`) |
| **Карантин Holded** | Категория `⛔ Карантин Holded` (id=207) — все импортированные карточки |
| **Target variant** | Новая карточка-вариант, в которую мигрирует карантинная (`x_studio_target_variant`) |
| **OLD_ SKU** | Префикс на `default_code`/`barcode` архивированной source-карточки после миграции v2.2 |
| **Skeleton** | Пустой target `product.template` с правильной категорией + `list_price=0.0` явно, готовый принять данные с source через migration script v2.2 |
| **Flat / multivariant target** | Forma target для миграции: flat = 1 template ↔ 1 variant; multivariant = 1 template ↔ N variants. Определяет куда пишется картинка |
| **`pos_hr` tier** | Тиринг прав кассира в Odoo 19: minimal / basic / advanced |
| **POS Category** | `pos.category` (m2m через `pos_categ_ids`) — UX-группировка на экране кассира. Отличается от `product.category` (categ_id, m2o, бухгалтерская) |
| **POS Terminal user** | Dedicated non-admin `res.users` (id=5, login `pos_terminal@espafloria.local`) — один на все 3 планшета |
| **Efectivo per-POS** | Каждая касса имеет свой `pos.payment.method` типа cash (constraint Odoo). Одинаковый GL `570001`, разные journals |
| **🌹 Букет на витрину** | Technical `res.partner` id=53. На него висят все `sale.order BP-*` как владелец |
| **BP-YYYY-NNNN** | Имя `sale.order` для букета, per-warehouse sequence |
| **Reserve-model (букет v2)** | SO BP-* имеет SO-picking в state `assigned` — компоненты зарезервированы, не списаны. Sell branch — штатный Odoo 19 cancel'ит picking сам |
| **Маркер сборки** | `product.product` id=7864 (`🌹 Работа по сборке букета`), service, default 5€. Флорист добавил вручную → бонус; забыл — скрипт авто-вставит с 0€ |
| **eWallet** | Loyalty program (id=2, `program_type=ewallet`) для предоплаты. Top-up product 7857, discount product 7862. Income Account 438 Anticipos, tax 0% |

---

## Статусы компонентов

- 🟢 **PROD** — работает в проде, источник правды.
- 🟡 **READY** — инфраструктура готова, данных пока нет / не end-to-end проверено.
- 🔴 **CONCEPT** — только в планах/брифах, не реализовано.
- ⚠️ **CLEANUP** — техдолг, надо зачистить.
- ⬜ **TODO** — открытая работа.
- ❓ **DISCUSS** — требует обсуждения с владельцем.

---

## Внешние ссылки-артефакты

| Артефакт | Где | Что |
|---|---|---|
| Make.com blueprint | через Make MCP | 55 модулей, 4 Route. ~230 KB. Достаём live через `mcp:make` |
| Google Sheets: products | [link](https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE) | ETL справочник Holded→Odoo |
| Google Sheets: albaran | [link](https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58) | ETL для albaran→pedido |
| Регламент сотрудников | Google Doc (29 MB, Holded-based) | Ждёт переработки под Odoo |
| POS_AUDIT | `../POS_AUDIT_2026-04-25.md` | Аудит 10 POS-операций × Odoo 19 ready solutions, рекомендация по Odoo.sh |

---

## Workflow работы AI/инженера

1. **Старт сессии** → читать [99_invariants.md](99_invariants.md) (5 правил + 11 gotchas).
2. **Большая картина** → [01_project.md](01_project.md) (бизнес, архитектура, roadmap, wishlist).
3. **Работа по теме** → идти в тематический файл (02-08).
4. **Перед изменениями в Odoo** → **обязательно** [99](99_invariants.md) — особенно §4 (свериться с docs 19 / community / live) и §5 (штатное перед custom).
5. **После любого изменения** → запись в [CHANGELOG.md](CHANGELOG.md).
6. **Скрипты с Python** → mirror `.py` файл в master-context/ (см. [99 §2](99_invariants.md)).
7. **git commit/push** — у user'а в локальном терминале (Cowork mode не модифицирует .git/).

---

## Что в файлах НЕ держим (anti-patterns)

- ❌ Истории отдельных сессий-исправлений (это в `CHANGELOG.md`).
- ❌ Удалённых полей и deprecated сущностей (упомянуть один раз в snapshot, дальше забыть).
- ❌ Длинных списков «может быть когда-нибудь» (это шум — реализация по запросу).
- ❌ Дублирование между файлами (один источник правды на тему).
- ❌ Дат-дедлайнов «до 20 апреля» (даты быстро устаревают).
