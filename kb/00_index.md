<!-- v: 6 | updated: 2026-05-10T00:00Z -->
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

## Структура папки

```
kb/
├── <chapter>.md         ← главы (00-09 + 99)
├── README.md, CHANGELOG.md
├── add/                 ← все служебные артефакты с префиксом блока NN_
└── memory/              ← auto-memory Claude
```

**Принцип:** в корне `kb/` живут только главы. Все артефакты (mirrors `.py`, prompts `.txt`, INSTR-инструкции, audit reports, sub-specs) — в `add/` с префиксом блока к которому относятся.

---

## Карта глав

| # | Файл | Что содержит | Когда читать |
|---|---|---|---|
| 00 | `00_index.md` | Этот файл — навигация, глоссарий, статусы | Всегда первым |
| **01** | **`01_project.md`** | **Бизнес + архитектурные истины + vision + roadmap + wishlist** | **Большая картина** |
| 02 | `02_makecom_bot.md` | Make.com Telegram бот: OCR + reconciliation + diagnostics | Правки бота, debugging pedido |
| 03 | `03_inventory_pipeline.md` | Приёмка (`stock.move` review) + bill control + backorder | Работа с приёмкой, флорист UX, bill policy |
| **04** | **`04_pos_and_roles.md`** | **POS техдок + букеты + eWallet + роли + бонусы + CRM + scrap** | **Любая POS работа** |
| 05 | `05_catalog.md` | Карточки товара + миграция toolkit v2.2 | Миграция карточек, новый каталог |
| 06 | `06_infra.md` | Odoo Online Custom + лимиты + установленные модули + испанский compliance | Планирование нагрузок, миграция платформы |
| 07 | `07_state_snapshot.md` | Живой снимок prod (ID, цифры, состояния) | Перед массовыми операциями |
| 08 | `08_holded_archive.md` | Holded migration archive + .py исходники | При повторе миграции |
| **09** | **`09_pedido.md`** | **Purchase orders + reconciliation (Holded import + Make.com bot Route 2 + reception_algorithm)** | **Работа с pedido, reconciliation** |
| 99 | `99_invariants.md` | 5 жёстких правил + 11 Odoo 19 gotchas | **Перед любыми изменениями** |
| — | `CHANGELOG.md` | Журнал изменений | После каждой правки |
| — | `CLAUDE.md` | Инструкции для AI/инженера (на корне репо) | Старт сессии |
| — | `README.md` | Обзор + структура | Онбординг |

---

## Артефакты в `add/`

Каждый артефакт имеет префикс блока `NN_` к которому относится. Сортировка по блокам.

### Блок 00 — meta / KB tooling

| Файл | Назначение |
|---|---|
| `add/00_INSTR_kb_cleanup_pass.md` | Recipe для периодической компактификации KB (противоречия / дубли / stale / расползание) |

### Блок 02 — Make.com bot

| Файл | Назначение |
|---|---|
| `add/02_prompt_ocr_v1.txt` | OpenAI OCR extractor (модуль 3) |
| `add/02_prompt_reconciliation_v3.5.txt` | OpenAI reconciliation engine (модуль 149) |
| `add/02_prompt_diagnostics_v3.1.txt` | OpenAI diagnostics (модуль 167) |
| `add/02_make_line_log_pack.txt` | Make.com шаблон — пачечная ветка |
| `add/02_make_line_log_unit.txt` | Make.com шаблон — штучная ветка |

### Блок 03 — inventory pipeline

| Файл | Назначение |
|---|---|
| `add/03_calculate_in_shop_action.py` | Mirror `ir.actions.server` id=1150 |
| `add/03_review_status_automation.py` | Mirror id=1146 |

### Блок 04 — POS

| Файл | Назначение |
|---|---|
| `add/04_pos_audit_2026-04-25.md` | Аудит 10 POS-операций × Odoo 19 ready solutions |
| `add/04_bouquet_on_payment_action.py` | Mirror id=1203 (4 ветки) |
| `add/04_bouquet_on_dismantle_action.py` | Mirror id=1209 |
| `add/04_bouquet_on_picking_action.py` | Mirror id=1205 (deprecated) |
| `add/04_bouquet_on_order_paid_action.py` | Mirror id=1207 (deprecated) |

### Блок 05 — catalog migration

| Файл | Назначение |
|---|---|
| `add/05_migrate_variant_action.py` | Mirror id=1145 (UI trigger v2) |
| `add/05_migrate_variant_v2.2.py` | Mirror id=1176 (execute v2.2) |

### Блок 07 — state ops

| Файл | Назначение |
|---|---|
| `add/07_INSTR_wipe_test_transactions.md` | Сборник рецептов для зачистки транзакционных данных (POS / sales / accounting / stock / loyalty) |

### Блок 08 — Holded archive

| Файл | Назначение |
|---|---|
| `add/08_fetch_holded_images_55.py` | One-shot script: fetch + resize Holded images via API |

### Блок 09 — pedido / reception

| Файл | Назначение |
|---|---|
| `add/09_reception_algorithm.md` | Spec алгоритма приёмки albaranes (current **v20.1**, 🟢 PROD-ready) |
| `add/09_reception_algorithm_v1.md` | v1 baseline алгоритма (исторический, для сравнения с v20) |
| `add/09_reception_action_1217.py` | Mirror prod-action 1217 (finalize-флаг + soft-gate + Phase A2 + ROLLBACK) |
| `add/09_reception_handover_2026-04-29.md` | Snapshot prod-state на 2026-04-29 (operational rules + gotchas) |
| `add/09_reception_audit_v12_prompt.md` | Independent audit prompt для v12 алгоритма |
| `add/09_reception_audit_v12_report.md` | Output v12 audit (5 BLOCKER + 11 MAJOR + ...) — input для re-audit |
| `add/09_reception_audit_v14_prompt.md` | Re-audit prompt для v14 (post-fix) |
| `add/09_reception_INSTR_attach_pdf.md` | Recipe: bulk attach paper PDF к Verdnatura pedido (post-reset) |
| `add/09_reception_INSTR_test_run.md` | Recipe: single-pedido test run алгоритма (test версии + side-by-side diff) |
| `add/09_serviflor_chatgpt_prompt_v9.1.txt` | ChatGPT external prompt v9.1-lite для одиночных Serviflor events: вход = supplier files + bookkeeper workbook + Compras evidence → выход = PO/transfer/supplierinfo XLSX готовые к Odoo import. Учим pricelist через композитный Supplier Identity Key (у Serviflor нет стабильного `codigo`). v9.1 vs v8.5: two-step PO price enforcement (1_purchase_order + 1b_purchase_order_line_price_fix), lightweight 4_import_control_summary, supplier enrichment как REQUIRED-IF-EXISTS metadata. |

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
| **Sentinel -1** | `quantity = -1` = «штуки не пересчитаны флористом» (отличать от `0`) |
| **Learned vendor code** | Выученный ботом маппинг supplier_sku → product variant (`product.supplierinfo.product_code`) |
| **Operator hit** | Ручная подсказка оператора для LLM-reconciliation (`x_studio_operator_hit`) |
| **Карантин Holded** | Категория `⛔ Карантин Holded` (id=207) — все импортированные карточки |
| **Target variant** | Новая карточка-вариант, в которую мигрирует карантинная (`x_studio_target_variant`) |
| **OLD_ SKU** | Префикс на `default_code`/`barcode` архивированной source-карточки после миграции v2.2 |
| **Skeleton** | Пустой target `product.template` с правильной категорией + `list_price=0.0` явно |
| **Flat / multivariant target** | Forma target для миграции: flat = 1:1, multivariant = 1:N |
| **`pos_hr` tier** | Тиринг прав кассира в Odoo 19: minimal / basic / advanced |
| **POS Category** | `pos.category` (m2m через `pos_categ_ids`) — UX-группировка на экране кассира |
| **POS Terminal user** | Dedicated non-admin `res.users` (id=5) — один на все 3 планшета |
| **Efectivo per-POS** | Каждая касса свой `pos.payment.method` cash (constraint Odoo) |
| **🌹 Букет на витрину** | Technical `res.partner` id=53. На него висят `sale.order BP-*` |
| **BP-YYYY-NNNN** | Имя `sale.order` для букета, per-warehouse sequence |
| **Reserve-model (букет v2)** | SO BP-* имеет SO-picking в state `assigned` — компоненты зарезервированы |
| **Маркер сборки** | `product.product` id=7864 (`🌹 Работа по сборке букета`), service, default 5€ |
| **eWallet** | Loyalty program (id=2, `program_type=ewallet`) для предоплаты |

---

## Статусы компонентов

- 🟢 **PROD** — работает в проде, источник правды.
- 🟡 **READY** — инфраструктура готова, данных пока нет / не end-to-end проверено.
- 🔴 **CONCEPT** — только в планах/брифах, не реализовано.
- ⚠️ **CLEANUP** — техдолг, надо зачистить.
- ⬜ **TODO** — открытая работа.
- ❓ **DISCUSS** — требует обсуждения с владельцем.

---

## Внешние ссылки

| Артефакт | Где | Что |
|---|---|---|
| Make.com blueprint | через Make MCP | 55 модулей, 4 Route. ~230 KB |
| Google Sheets: products | [link](https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE) | ETL справочник Holded→Odoo |
| Google Sheets: albaran | [link](https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58) | ETL для albaran→pedido |
| Регламент сотрудников | Google Doc (legacy, Holded-based) | Ждёт переработки под Odoo |
| Paper PDF / data | `../pedido.files/reception_paper/`, `../pedido.files/verdnatura/`, `../pedido.files/serviflor-бухгатер-chatgpt/` | На уровне выше KB (data, не KB). `serviflor-бухгатер-chatgpt/` — historical archive supervisor'а: `_final4/<event>/` (per-event inputs 14 events), `_final4/справочники/` (Compras 2025/2026, Product Variant, Supplier Pricelist, odoo-pedido CSV, selection analysis), `promts/` (17 версий v4_5→v9.1, эволюция), `__out/_done/<event>/` (агентовы output ZIPs для 12 успешных импортов), `serviflor_event_index.xlsx` (master index 14 events). |

---

## Workflow работы AI/инженера

1. **Старт сессии** → читать [99_invariants.md](99_invariants.md) (5 правил + 11 gotchas).
2. **Большая картина** → [01_project.md](01_project.md).
3. **Работа по теме** → тематическая глава (02-09).
4. **Артефакты по теме** → `add/NN_*` (префикс блока в имени).
5. **Reconciliation pedido** → [09_pedido.md](09_pedido.md) → [add/09_reception_algorithm.md](add/09_reception_algorithm.md) + [add/09_reception_action_1217.py](add/09_reception_action_1217.py). Test single — через [add/09_reception_INSTR_test_run.md](add/09_reception_INSTR_test_run.md).
6. **Bulk-attach paper PDF** (после DB reset) → [add/09_reception_INSTR_attach_pdf.md](add/09_reception_INSTR_attach_pdf.md).
7. **Перед изменениями в Odoo** → **обязательно** [99](99_invariants.md) — особенно §4 (свериться с docs 19 / live) и §5 (штатное перед custom).
8. **После любого изменения** → запись в [CHANGELOG.md](CHANGELOG.md).
9. **Скрипты с Python** → mirror `.py` файл в `kb/add/NN_*` (см. [99 §2](99_invariants.md)).
10. **git commit/push** — через Desktop Commander (Cowork) либо локальный терминал.

---

## Что в файлах НЕ держим (anti-patterns)

- ❌ Истории отдельных сессий-исправлений (это в `CHANGELOG.md`).
- ❌ Удалённых полей и deprecated сущностей (упомянуть один раз в snapshot, дальше забыть).
- ❌ Длинных списков «может быть когда-нибудь» (это шум — реализация по запросу).
- ❌ Дублирование между файлами (один источник правды на тему).
- ❌ Дат-дедлайнов «до 20 апреля» (даты быстро устаревают).
