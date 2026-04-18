<!-- v: 7 | updated: 2026-04-18T22:30Z -->
# Master Context — Espafloria Odoo Automation

**Last updated:** 2026-04-18
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

Живут в `artifacts/` рядом с этой папкой (`master-context/artifacts/`). Часть грузится в Project knowledge, часть — только в git.

**В Project knowledge (нужны для обсуждения бизнеса):**

| Папка | Что внутри |
|---|---|
| `artifacts/prompts/` | System prompts для OpenAI (OCR v1, Reconciliation v3.5, Diagnostics v3.1) |
| `artifacts/templates/` | Make.com line-log шаблоны (пачечная/штучная ветки) |
| `artifacts/code/odoo_actions/` | Живые Odoo server actions: `calculate_in_shop_action.py` (id=1150), `migrate_variant_action.py` (id=1145), `review_status_automation.py` (id=1146) |

**Только в git (достаём по запросу):**

| Папка | Что внутри |
|---|---|
| `artifacts/code/migrations/` | Одноразовые Holded-миграции: `image_import_*`, `split_big_csv.py` |
| `artifacts/scripts/` | `commit_worker_delivery.sh` — стандартный коммит-скрипт worker'а |
| `artifacts/makecom/` | Резерв для Make.com blueprint JSON (~230 KB, в Project не грузится даже если появится) |

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
