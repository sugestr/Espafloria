<!-- v: 12 | updated: 2026-04-23T01:40Z -->
# Master Context — Espafloria Odoo Automation

**Last updated:** 2026-04-19
**Owner:** Andriy
**Company:** Espafloria SL (цветочный бизнес, Испания)
**Platform:** Odoo.sh Custom (espafloriasl.odoo.com)
**Magazines:** Plaza, Gloria, Blau (3 POS кассы активны)

---

## 🎯 Конечная цель проекта

**Умная сеть цветочных магазинов**, где база и роботы (автоматизация) делают основную работу по контролю сотрудников и структурной целостности бизнеса — чтобы не тратить много денег на управляющий персонал, а направлять их на мотивацию сотрудников в поле.

Подробно: [10_vision_and_roadmap.md](10_vision_and_roadmap.md)

---

## Зачем этот контекст

Это **база знаний проекта автоматизации Espafloria** — для нового инженера, нового AI-ассистента, или для Andriy при работе после перерыва. Цель — уметь в любой момент ответить на вопросы:

- Что уже работает в проде?
- Какие бизнес-решения приняты и почему?
- Где источник правды по каждой сущности?
- Какие правила нельзя нарушать?
- Что ещё не сделано?

---

## Как пользоваться

1. **Новый инженер / новая сессия** → читайте в порядке номеров файлов (01 → 02 → …).
2. **Работа по конкретной теме** → идите прямо к нужному файлу.
3. **Перед правками в Odoo** → обязательно прочитайте `99_invariants.md`.
4. **После любого изменения в системе** → обновите `CHANGELOG.md`.

---

## Карта файлов

| # | Файл | О чём | Когда читать |
|---|---|---|---|
| 00 | `00_master_index.md` | Этот файл | Всегда первым |
| 00s | `00_source_files_index.md` | Карта исходных файлов (blueprint, prompts, PDFs, Google Sheets) | Перенос в другой AI, аудит |
| 01 | `01_business_context.md` | Бизнес-цели, user stories, 3 источника истины | Перед любыми архитектурными решениями |
| 02 | `02_makecom_bot.md` | Telegram-бот: OCR + reconciliation engine | Правки бота, debugging pedido |
| 03 | `03_odoo_receipt_review.md` | Приёмка: stock.move, review-status, кнопки | Работа с приёмкой, флорист UX |
| 04 | `04_holded_migration.md` | Импорт из Holded: категории, товары, изображения | Миграция данных |
| 05 | `05_florists_logistics_accountant.md` | Роли и их процессы (placeholder для регламента) | Настройка рабочих мест |
| 06 | `06_catalog_migration_toolkit.md` | Server action `Migrate to selected variant` | Миграция каталога в новые variants |
| 07 | `07_infrastructure_devops.md` | Odoo.sh Custom, ограничения | Планирование нагрузок |
| 08 | `08_current_state_snapshot.md` | Фото базы данных после hot-fix 18 апр | Перед массовыми операциями |
| 09 | `09_open_work.md` | TODO: маркетплейсы, POS, Route 1, регламент | Приоритизация работы |
| **10** | **`10_vision_and_roadmap.md`** | **Конечная цель + 15 стратегических шагов** | **Стратегические решения, онбординг** |
| **11** | **`11_crm_and_customers.md`** | **CRM, клиенты, лояльность, рассылки** | **Работа с клиентами, маркетинг** |
| **12** | **`12_ai_workflow.md`** | **Multi-chat архитектура (orchestrator / workers / reviewer)** | **Любой AI-чат при старте работы** |
| 99 | `99_invariants.md` | 37 железных правил проекта | **Всегда** перед изменениями |
| — | `CHANGELOG.md` | Журнал всех изменений | После каждой правки |
| — | `VERSIONS.md` | Индекс версий всех файлов | Быстрая проверка актуальности |
| — | `SYNC_STATE.md` | Состояние синхронизации Project ↔ GitHub | При старте каждого чата |
| — | `README.md` | Правила репо (для GitHub) | Онбординг в repo |

## Артефакты

Живут в `master-context/` **на одном уровне с .md** (плоский layout). Исключение — одна подпапка `legacy_migrations/` со старыми одноразовыми скриптами.

**Грузятся в Project knowledge вместе со всеми .md:**

| Файл | Что это |
|---|---|
| `calculate_in_shop_action.py` | Odoo server action id=1150 |
| `migrate_variant_action.py` | Odoo server action id=1145 (UI trigger v2, короткий wrapper) |
| `migrate_variant_v2.2.py` | Odoo server action id=1176 (execute v2.2, вся миграционная логика) |
| `review_status_automation.py` | Odoo server action id=1146 |
| `prompt_ocr_v1.txt` | OpenAI OCR extractor (модуль 3) |
| `prompt_reconciliation_v3.5.txt` | OpenAI reconciliation engine (модуль 149) |
| `prompt_diagnostics_v3.1.txt` | OpenAI diagnostics (модуль 167) |
| `make_line_log_pack.txt` | Make.com шаблон — пачечная ветка |
| `make_line_log_unit.txt` | Make.com шаблон — штучная ветка |
| `commit_worker_delivery.sh` | Коммит-скрипт worker'а; Claude его не использует, но в drag-drop попадает (~3 KB) |

Note: в Project knowledge точки в именах заменяются на `_` (`prompt_reconciliation_v3_5.txt` vs `v3.5.txt` в репо). См. [02_makecom_bot.md § Промпты](02_makecom_bot.md).

**В Project knowledge не грузятся (есть в репо, достаются по запросу):**

| Файл / папка | Что это |
|---|---|
| `legacy_migrations/` | Одноразовые Holded-миграции: `image_import_*`, `split_big_csv.py` |

---

## Глоссарий

| Термин | Значение |
|---|---|
| **Pedido** | Purchase order в Odoo (= заказ поставщику) |
| **Albarán** | Товарная накладная поставщика (испанский документ) |
| **Factura** | Счёт-фактура (испанский документ) |
| **Receipt / Transfer** | stock.picking приёмки в Odoo |
| **Paper qty** | Количество по бумаге поставщика (`purchase.order.line.product_qty`) |
| **Logist qty** | Ожидаемое реальное количество по оценке логиста (`x_studio_expected_qty`) |
| **Actual qty** | Фактически принятое количество флористом (`stock.move.quantity`) |
| **Learned vendor code** | Выученный ботом маппинг supplier_sku → product variant (`product.supplierinfo.product_code`) |
| **Operator hit** | Ручная подсказка оператора для LLM-reconciliation (`x_studio_operator_hit`) |
| **Карантин Holded** | Категория `⛔ Карантин Holded` (id=207) — все импортированные карточки |
| **Target variant** | Новая карточка-вариант, в которую мигрирует карантинная (`x_studio_target_variant`) |
| **OLD_ SKU** | Префикс на `default_code`/`barcode` архивированной source-карточки после миграции v2.2. Освобождает unique constraint для target и помечает «это legacy-карточка» (см. [99 §20/§23](99_invariants.md), [06](06_catalog_migration_toolkit.md)) |
| **Skeleton** | Пустой target `product.template` с правильной категорией + `list_price=0.0` явно, готовый принять данные с source через migration script v2.2 (см. [06 § SOP](06_catalog_migration_toolkit.md), [99 §38](99_invariants.md)) |
| **Flat / multivariant target** | Форма target для миграции: flat = 1 template ↔ 1 variant (доставки, моно-розы); multivariant = 1 template ↔ N variants с attributes (напр. Rosa 40/50/60 cm). Определяет куда пишется картинка — template vs variant (см. [99 §39](99_invariants.md)) |
| **`pos_hr` / advanced employee** | Odoo 19 тиринг прав кассира: minimal (только чеки), basic (+ Cash In/Out), advanced (+ закрытие смены + create product). Задаётся через `pos.config.advanced_employee_ids` (см. [08 § B](08_current_state_snapshot.md)) |
| **POS Category** | `pos.category` (m2m через `pos_categ_ids`) — UX-группировка на экране кассира. Отличается от `product.category` (categ_id, m2o, бухгалтерская). См. [99 §40](99_invariants.md) |
| **POS Terminal user** | Dedicated non-admin `res.users` (id=5, login `pos_terminal@espafloria.local`, groups [1, 87]) — один на все 3 планшета касс. Чеки через PIN прилипают к `hr.employee`, не к этому user (см. [08 § C](08_current_state_snapshot.md)) |
| **Efectivo per-POS** | Каждая касса имеет свой `pos.payment.method` типа cash (EFPL/EFGL/EFBL) — требование Odoo. Одинаковый GL `570001`, разные journal codes для per-POS tracking бухгалтером |
| **Anon (клиент букета)** | Технический `res.partner` id=53 (`TECH_PARTNER_ID`), на котором висят все `sale.order BP-*` как владелец. До продажи букета покупатель ещё неизвестен → партнёр общий. См. [99 §32/§46](99_invariants.md) |
| **BP-YYYY-NNNN** | Имя `sale.order` для букета, per-warehouse sequence (`espafloria.bouquet.plaza/.gloria/.blau`). Создаётся action 1203 при оплате POS методом «Собрать букет». См. [05 §1.2.1](05_florists_logistics_accountant.md) |
| **Маркер разборки / 🗑 Разборка букета** | `product.product` id=7865 (`BQ-DISMANTLE`), service, price=0. Добавленный в POS cart вместе с Settle букета + оплата «Собрать букет» → триггерит dismantle-ветку action 1203. Без маркера — reassemble-ветка. См. [05 §1.2.3](05_florists_logistics_accountant.md), [99 §46](99_invariants.md) |
| **Reassemble vs Dismantle** | Две ветки action 1203 (оба через Settle). **Reassemble**: нет маркера → старый SO cancel + **новый SO создаётся** из текущих линий (модификация букета). **Dismantle**: есть маркер → старый SO cancel, **нового SO нет** (разборка на компоненты). См. [05 §1.2.2–1.2.3](05_florists_logistics_accountant.md) |
| **Sentinel -1** | Значение `quantity = -1` = «штуки не пересчитаны флористом», отличать от `0` (реально ничего не приехало) |
| **VERSIONS.md** | Сводная таблица «файл → v → updated». Версия в header этого файла = маркер состояния всей базы (version-based sync, см. `SYNC_STATE.md`) |
| **`v` в header** | `<!-- v: N | updated: ... -->` в первой строке каждого `.md`. Bump'ается при каждой значимой правке |
| **Sync** | База в Claude Project совпадает по `v` у `VERSIONS.md` с GitHub. Если нет — Owner перезаливает |

---

## Статусы компонентов

- 🟢 **PROD** — работает в проде, источник правды
- 🟡 **READY** — инфраструктура готова, данных пока нет
- 🔴 **CONCEPT** — только в планах/брифах, не реализовано
- ⚠️ **CLEANUP** — техдолг, надо зачистить
- ⬜ **TODO** — открытая работа

---

## Внешние ссылки-артефакты

| Артефакт | Где | Что |
|---|---|---|
| Make.com blueprint | через Make MCP (в репо не храним) | 55 модулей, 4 Route. ~230 KB. Достаём live через `mcp:make` когда нужен |
| Google Sheets: products | https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE | ETL справочник Holded→Odoo |
| Google Sheets: albaran | https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58 | ETL для albaran→pedido |
| Регламент сотрудников | Google Doc (29 MB, Holded-based) | Ждёт переработки под Odoo |
| PDF: ChatGPT про испанский план счетов | `FLOR-gov_-_Odoo_и_испанскии__план_счетов__1_.pdf` (внешний, по запросу) | 226 стр, raw research — не в Project knowledge, загружается точечно |

---

## Решения, принятые сегодня (2026-04-18)

- Запуск MVP **20 апреля 2026** — параллельно Odoo + Holded, постепенный переход
- Исторические данные 2026 года — импорт до 31 декабря, финальный cutover 1 янв 2027
- Цветы/горшечка → `On ordered quantities`, вазы/декор/упаковка → `On received quantities`
- Миграция каталога — параллельно с работой, карточка уходит в архив при переносе в новый variant
- Инвентаризация: цветы+горшечка = физический пересчёт, вазы = Holded + rolling correction при продаже

---

**Подробности по каждому блоку — в файлах 01-12.**
