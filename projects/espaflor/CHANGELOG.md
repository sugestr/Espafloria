<!-- v: 4 | updated: 2026-04-18T18:15Z -->
# CHANGELOG

Журнал всех изменений в системе Espafloria Odoo + Make.com автоматизации.

**Правила:**
- После **любого** изменения — запись сюда
- Формат: дата + автор + сущность + что изменили + связанная задача/документ
- Сверху — самые свежие

---

## 2026-04-18 — Master Context session 4 (финальная подготовка к multi-chat)

### Done (Claude — этот чат закрывается)

**Новые файлы:**
- `12_ai_workflow.md` (v1) — протокол multi-chat архитектуры: Orchestrator / Worker / Reviewer. Содержит 3 готовых briefing для новых чатов.
- `SYNC_STATE.md` (v1) — механизм синхронизации Project knowledge ↔ GitHub с alert-логикой для новых чатов.

**Обновлено:**
- `00_master_index.md` (v4) — добавлены 12_ai_workflow, SYNC_STATE в навигацию.
- `VERSIONS.md` (v2) — актуализирован индекс всех 17 файлов.

### Принятые решения

**Архитектура работы с базой знаний:**
- Один длинный chat = проблема контекста → переход на **multi-chat** модель
- **3 роли чатов:** Orchestrator (координатор), Worker (задача), Reviewer (QA)
- **GitHub как source of truth** (`sugestr/espafloria`)
- **Project knowledge как working copy** — обновляется Owner'ом вручную после коммита
- **SYNC_STATE.md** — координирует «актуальна ли база в Project?»

**Следующие шаги (делает Owner):**
1. Запустить **setup-чат** по briefing'у из `12_ai_workflow.md` → initial commit в GitHub
2. После commit — загрузить ZIP в Project knowledge
3. Обновить SYNC_STATE.md с актуальным commit SHA
4. Запустить **Reviewer-чат** для проверки консистентности всей базы
5. Закрыть этот (текущий) chat — он свою роль выполнил

### Этот чат — финал

Дальнейшая работа над проектом — через специализированные чаты по паттерну из `12_ai_workflow.md`.

---

## 2026-04-18 — Master Context session 3 (правки по замечаниям + CRM)

### Done (Claude)

**Новые файлы:**
- `11_crm_and_customers.md` (v1) — scope CRM: клиентская карточка, лояльность, рассылки, интеграции
- `README.md` (v1) — правила GitHub repo + version protocol
- `VERSIONS.md` (v1) — индекс версий всех файлов

**Полностью переписан:**
- `05_florists_logistics_accountant.md` (v2):
  - Флорист: 7-блочный функциональный spec (POS, букет как сущность, приёмка, списание с фото-согласованием, типовые задания от системы, геймификация, PIN-авторизация)
  - Логист: 5-блочный spec (закупка, связь с приёмкой, контроль поставщиков, оплата, open questions)
  - Бухгалтер: 3 задачи с open questions
  - Salary model: 900€ базовая + 1400€ минимум гарантии + личные бонусы (не коллективные), калибровка коэффициентов после 2-3 месяцев данных
  - Роль главного флориста = жена + нанятый директор

**Существенно дополнены:**
- `02_makecom_bot.md` (v2): Platform Dependencies section с 4 активными коннекторами (CloudConvert, Odoo, OpenAI, Telegram). Google **не используется** сценарием. Промпты = source of truth в Project knowledge + копии в `prompts/`.
- `99_invariants.md` (v2): добавлены инварианты 31-37 (списание, букет life-cycle, личные бонусы, аналитика только после миграции, платформенные зависимости, **продажа в минус = индикатор проблемы**). Уточнены 19 (backorder + финансовая сторона), 24 (План A/B запуска).
- `09_open_work.md` (v2): P0 checklist (re-auth done ✅, Google не нужен ✅), P2 новые секции (смены+PIN, бонусная калибровка, списание с фото, задания магазину, букет-сущность, мониторинг коннекторов), P3 CRM.
- `10_vision_and_roadmap.md` (v2): шаг 3 переписан — **продажи в минус убраны как норма**, вместо — инвентаризация ДО запуска. Шаг 11.5 CRM добавлен как параллельный workstream.
- `00_master_index.md` (v3): добавлен 11_crm, README, VERSIONS в карту файлов.

**Зафиксированные бизнес-решения:**
- Продажа в минус = **плохо**, не режим работы MVP (исправление моей предыдущей записи в шаге 3)
- Запуск каталога: План A (новый каталог из 2026-закупок) предпочтительнее, План B (разблокировать карантин) — резерв
- Бонусы = **личные**, не коллективные. Калибровка по реальным данным.
- Списание товара = процесс с фото-согласованием главного флориста, НЕ мгновенная операция
- Букет = живая сущность с жизненным циклом

**Статус коннекторов Make.com (18 апреля):**
- ✅ CloudConvert — re-authorized
- ✅ OpenAI — активен
- ✅ Odoo — активен
- ✅ Telegram — активен
- ⚠️ Google — висит в списке, **не используется** сценарием (можно отвязать)

### Done manually (Andriy)
- Re-authorized CloudConvert в Make.com
- Подключен GitHub коннектор (в другой сессии Claude)

### Pending (вручную в Studio UI / Odoo)
- [ ] Добавить `qty_received` + `qty_invoiced` на форму `purchase.order.line` (Studio, 2 минуты)
- [ ] Удалить физически `x_studio_many2many_field_4qh_1jkvk330u` через Studio UI
- [ ] Тестовая миграция 1 карточки + проверка копирования supplierinfo

---

## 2026-04-18 — Master Context session 2 (добавления)

### Done (Claude)

**Новые файлы:**
- `00_source_files_index.md` — карта всех исходных файлов проекта (blueprint, prompts, PDFs, Google Sheets)
- `10_vision_and_roadmap.md` — конечная цель «умная сеть» + 15-шаговый стратегический roadmap (от Andriy)

**Обновлено:**
- `00_master_index.md` — добавлена секция «🎯 Конечная цель проекта» и ссылки на новые файлы в навигации

**Зафиксирована конечная цель:**
> Умная сеть цветочных магазинов, где база и роботы берут работу по контролю → экономим на управляющем персонале → деньги идут в мотивацию полевых сотрудников.

**Стратегия запуска формализована как 15 шагов** — от MVP 20 апреля до «умной сети» в 2027+.

### Решено по хранению Master Context
- Рабочая копия: Claude Project (этот проект)
- Бэкап / версионирование: GitHub private repo `sugestr/espafloria`
- Протокол: version headers `<!-- v: N | updated: ... -->` + `VERSIONS.md` + commit per change
- После коммита напоминание перезалить в Project knowledge

---

## 2026-04-18 — Hot-fix session (Claude + Andriy)

### Done via API (Claude)

**Migration action (id=1145)** — добавлен блок copy `product.supplierinfo` на target variant перед архивацией старой карточки.
- Причина: без этого learned vendor codes теряются при миграции, Make.com бот перестаёт находить match по supplier_sku
- Реализация: `si.copy({'product_tmpl_id': target.product_tmpl_id.id, 'product_id': target.id})`
- См. [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md)

**`product.template.purchase_method`** — массовое обновление
- Было: `purchase_method = 'receive'` у всех 1983 карантинных карточек (Odoo default)
- Стало: `purchase_method = 'purchase'` у 900 карточек в категориях `FLORES CORTADAS` (id=212) + `PLANTAS EN MACETAS` (id=213)
- Остальные 1083 карточки (DECORACION, EMBALAJE, ENTREGA, PRODUCTOS ESPECIALES, Consumibles) остались на `receive`
- Причина: для цветов/горшечки платим по бумаге поставщика, не по факту приёмки
- См. [03_odoo_receipt_review.md](03_odoo_receipt_review.md) раздел Bill control policy

**Automation id=1 «Review → generate info conclusion»** — очищены watched fields
- Было: `quantity`, `x_studio_received_packs`, `picking_id`, `purchase_line_id`
- Стало: `quantity`, `x_studio_received_packs`
- Причина: структурные поля (`picking_id`, `purchase_line_id`) вызывали лишние срабатывания automation — нарушение инварианта 14

**Удалены мусорные поля:**
- `x_studio_expected_qty_2` (id=26874) на purchase.order.line — тестовый мусор «expected_qtyыыыы»
- `x_studio_received_units` (id=26902) на stock.move — замещён штатным `quantity`
- `x_studio_expected_quantity` (id=26892) на stock.move — дубль `x_studio_paper_qty`
- `x_studio_supplier_unit` (id=26894) на stock.move — дубль `x_studio_paper_unit`

**Помечено DEPRECATED (Studio защита не даёт удалить):**
- `x_studio_many2many_field_4qh_1jkvk330u` (id=25632) на product.product — label переименован в `[DEPRECATED] New Tags - do not use, replaced by Botanical Tags (x_studio_botanic_name)`

**Temp server action удалён:**
- `TEMP: Bulk set purchase_method purchase for Flores+Plantas` (id=1151) — создавался для bulk update, не понадобился, удалён

### Done manually (Andriy)
- (заполнить: walk-through UI, проверка receipt, и т.д.)

### Pending (вручную в Studio UI)
- [ ] Добавить `qty_received` + `qty_invoiced` на форму `purchase.order.line` (для 3-точечной сверки)
- [ ] Удалить физически `x_studio_many2many_field_4qh_1jkvk330u` через Studio UI (если прорвётся)

---

## 2026-04-18 — Master Context создан

Собран полный набор документации проекта в виде 10 файлов + папки артефактов.

Файлы:
- `00_master_index.md` — навигация + глоссарий
- `01_business_context.md` — бизнес-цели, user stories, принципы
- `02_makecom_bot.md` — Telegram-бот (blueprint 55 модулей)
- `03_odoo_receipt_review.md` — приёмка, review-status, кастомные поля
- `04_holded_migration.md` — импорт категорий / товаров / картинок из Holded
- `05_florists_logistics_accountant.md` — роли и процессы
- `06_catalog_migration_toolkit.md` — migration action + SOP
- `07_infrastructure_devops.md` — Odoo.sh Custom, ограничения
- `08_current_state_snapshot.md` — фото базы данных
- `09_open_work.md` — TODO приоритизированный
- `99_invariants.md` — 30 железных правил
- `CHANGELOG.md` — этот файл

Артефакты:
- `prompts/prompt_ocr_v1.txt` (6213 chars)
- `prompts/prompt_reconciliation_v3.5.txt` (20305 chars)
- `prompts/prompt_diagnostics_v3.1.txt` (6595 chars)
- `code/review_status_automation.py` (production code)
- `code/migrate_variant_action.py` (с патчем copy supplierinfo)
- `code/calculate_in_shop_action.py`
- `code/image_import_from_urls.py`
- `code/image_import_from_holded_api.py`
- `code/split_big_csv.py`
- `templates/make_line_log_unit.txt`
- `templates/make_line_log_pack.txt`

---

## (template для новых записей)

### YYYY-MM-DD — (short title)

**Done via API / manually / Studio:**
- [Кто] что-то сделал
- Причина / влияние
- См. ссылку на файл

---
