<!-- v: 2 | updated: 2026-04-18T16:50Z -->
# 09. Open Work — TODO

Всё, что ещё **не сделано** или сделано частично. Приоритизировано.

---

## P0 — Блокирует запуск 20 апреля

### Проверки и авторизация коннекторов
- [x] ✅ **Re-authorize CloudConvert** в Make.com — сделано 18 апреля
- [x] ✅ Выяснено: **Google connection не используется** в сценарии бота (можно отвязать)
- [ ] Проверить балансы: **Make.com operations**, **OpenAI tokens**, **CloudConvert credits**
- [ ] Протестировать end-to-end: отправить тестовый PDF в Telegram → убедиться, что весь pipeline отработал

### Odoo подготовка
- [ ] **Walk-through UI для флориста** — проверить receipt UI на планшете
- [ ] **Тестовая миграция 1 карточки** через обновлённый action 1145 — убедиться, что supplierinfo реально копируется
- [ ] **Добавить `qty_received` + `qty_invoiced` в view `purchase.order.line`** (Studio, 2 минуты)
- [ ] **Проверить POS warehouse_id** — сейчас все 3 POS на Plaza (id=2), намеренно или ошибка?

### Инвентаризация (критично для shadow-запуска БЕЗ продаж в минус)
- [ ] Физическая инвентаризация срезки + горшечки в 3 магазинах
- [ ] Остатки ваз/декора → из Holded как есть
- [ ] Решить: План A (новый каталог) или План B (разблокировать карантин)

### Массовый импорт albaran
- [ ] В понедельник 21 апреля сажается сотрудник на импорт 180+ albaran

---

## P1 — Нужно до массовой миграции каталога (не блокирует MVP)

### Make.com Route 1 modernization
Сейчас ветка «создать новый pedido» проще ветки «обогатить существующий»:
- ❌ Не проверяет дубль `(supplier_vat, document_number)` перед созданием → два одинаковых PDF = два pedido
- ❌ Не использует learned vendor codes при поиске карточки
- ❌ Не применяет operator hits
- ❌ Не вызывает reconciliation engine
- ❌ Не делает self-check на соответствие totals

**План:**
1. Добавить search по `(supplier_vat, document_number)` в модуль 108 до входа в Router 110
2. Поиск карточки (модуль 94) — добавить evidence priority как в Route 2
3. Опционально: вызвать reconciliation engine даже для нового pedido
4. Telegram progress bar как в Route 2

### Формирование нового каталога
- [ ] Решить структуру нового каталога категорий (не карантин)
- [ ] Решить структуру вариантов для типовых цветов (роза × цвет × длина × производитель?)
- [ ] Создать template-примеры для каждой ветки
- [ ] Twardый товар (вазы) — массовая миграция как есть

### Импорт продаж за 2026
- [ ] Экспорт продаж из Holded
- [ ] Садить **только на старые** карточки (в карантине или архивные)
- [ ] Lookup через SKU / Holded ID

### Массовая миграция
- [ ] Batch wizard для обработки N карточек за раз
- [ ] Queue-механизм, чтобы не вешать UI
- [ ] Migration dashboard — сколько migrated / pending / errors

---

## P2 — Следующие 2-3 недели

### Рабочие места ролей
- [ ] **Флорист planшет view** — увеличенные inputs, упрощённое меню
- [ ] **Логист desktop view** — закупка → приёмка → оплата в одном потоке
- [ ] **Бухгалтер view:**
  - [ ] Sales reconciliation workflow
  - [ ] Expense pipeline с AI-категоризацией
  - [ ] Kanban «закупили → … → продажа» взамен Google Sheets
- [ ] **Аналитик workspace** — продавцы, рентабельность, потери

### 🆕 Авторизация и смены (блокер бонусной модели)
- [ ] Модель смены (`hr.attendance` или custom) с PIN-кодом
- [ ] PIN-авторизация в POS — продажа привязывается к `hr.employee`
- [ ] Personal sales report (кто сколько продал за период)
- [ ] Единая воронка online-заказов (Flowwow / WhatsApp / Glovo / сайт) с идентификацией обработчика
- [ ] Решить формат: PIN / выбор из списка / комбинация — не финализировано
- [ ] Решить: жена + директор — полный Odoo backend или extended PIN?

### 🆕 Бонусная модель (калибровка)
Стратегия: собрать 2-3 месяца живых данных → смоделировать коэффициенты → запустить.
- [ ] Этап 1: запуск без бонусов, просто базовая 900 € + гарантия 1400 € (см. [05](05_florists_logistics_accountant.md))
- [ ] Этап 2: personal sales dashboard для каждого флориста
- [ ] Этап 3: моделирование формулы бонусов на реальных данных
- [ ] Этап 4: запуск бонусов во все каналы

### 🆕 Списание товара с фото-согласованием
- [ ] Workflow: флорист → фото → согласование главного → списание
- [ ] Типы списания: завял / сломался / потерян / пересортица / забыт
- [ ] Notification менеджеру (жена / директор) о pending approval
- [ ] Custom model или extended `stock.move` + state

### 🆕 Задания магазину (system tasks)
- [ ] Push-уведомления «к магазину едет товар» (на приёмку готовься)
- [ ] Задания инвентаризации («пересчитай розы до 14:00»)
- [ ] Фото-отчёты (холодильник / ценники наклеены)
- [ ] Напоминание о срочной перепечатке ценников
- [ ] Контроль выполнения: статус + напоминания при задержке

### 🆕 Букет как отдельная сущность
- [ ] Create / Modify / Disassemble workflow
- [ ] Уникальный номер букета
- [ ] Фото при создании (обязательно)
- [ ] Две цены: витрина vs online
- [ ] Печать ценника
- [ ] Решить: внутри POS / отдельный экран / производственная операция

### POS
- [ ] Быстрая сборка букета на месте без line discount
- [ ] Фото готового букета → sale.order.line
- [ ] Rolling inventory для ваз (блок завершения до пересчёта)

### Ценники
- [ ] Термопринтер setup
- [ ] Брендовый layout
- [ ] Автоматическая перепечатка при изменении цены

### 3-точечная сверка в UI
- [ ] `qty_received` + `qty_invoiced` в список колонок (Studio)
- [ ] Визуальная подсветка расхождений: `product_qty != qty_received` → красный

### 🆕 Мониторинг коннекторов Make.com
- [ ] Alerts при низких балансах (Make.com operations, OpenAI tokens, CloudConvert credits)
- [ ] Email / Telegram notification
- [ ] Dashboard «состояние всех интеграций»

## P3 — Marketplace (отдельный workstream)

### 🆕 CRM и клиенты (см. [11_crm_and_customers.md](11_crm_and_customers.md))
- [ ] MVP: базовая клиентская карточка создаётся при продаже (телефон)
- [ ] История покупок через `partner_id` (штатно)
- [ ] Этап 2: сегментация (VIP / Regular / Dormant / New)
- [ ] Первые email-рассылки через `mass.mailing`
- [ ] Loyalty program (штатный `loyalty.program`)
- [ ] WhatsApp интеграция (Wati / 360dialog / custom — решить)
- [ ] Напоминания о значимых датах клиентов (ДР, годовщины)
- [ ] GDPR compliance (opt-in, right to deletion)

### Flowwow integration
🔴 **CONCEPT** — нет брифа, требует отдельной проектной сессии.

**Что нужно разобрать:**
- [ ] Модель учёта комиссии: продажа клиенту + списание комиссии + перевод от площадки
- [ ] Импорт продаж из Flowwow (CSV / API?)
- [ ] Формирование чеков для испанской бухгалтерии (SII требования)
- [ ] Разделение: продажа ≠ комиссия ≠ cash movement

### Glovo integration
🔴 **CONCEPT** — новый workstream.

**Специфика Glovo:**
- Delivery-first (курьерские окна)
- Другая комиссионная модель
- Возможно другой flow подтверждения заказа
- [ ] Учёт курьерских комиссий
- [ ] Время сборки (SLA)
- [ ] Связка с физическим витринным запасом

---

## P3 — Catch-weight / variable pack content

🔴 **CONCEPT** — обсуждался как большая тема, не реализован.

**Суть проблемы:**
- Товар приходит в пачках, пачка не стандартизирована
- Нельзя использовать UoM коэффициенты
- Нужно вычислять эффективную цену единицы по факту приёмки

**Формула:**
```
effective_unit_cost = paper_total_amount / actual_received_units
```

**Что нужно:**
- Кастомный модуль Odoo (не Studio-only!)
- Отдельное хранение commercial qty vs actual inventory qty
- Интеграция с `stock.valuation.layer`
- Правильный момент пересчёта (в receipt validation)
- Корректный Vendor Bill при catch-weight строках

**Edge cases:**
- Частичная приёмка
- Недопоставка пачек
- Возврат поставщику
- Дробление приёмки
- Credit note / corrective bill

---

## P3 — Бухгалтерская автоматизация (три задачи бухгалтера)

### 1. Sales reconciliation
🔴 **CONCEPT**

**Пайплайн (идея):**
- Make.com читает Telegram-чаты магазинов (отчёты смены)
- Парсит суммы, время, магазин
- Сверяет с `pos.session.total_cash` + bank statement
- Формирует report: OK / extra cash / missing cash / mismatch
- UI: view «несверенные смены» с прямыми ссылками

### 2. Expense pipeline + Spanish chart of accounts
🟡 **READY** — `l10n_es` локализация установлена, Modelo 303/347/349 есть.

**Что доделать:**
- [ ] AI-pre-categorization счетов (можно на базе OCR-промпта из бота)
- [ ] `account.online.link` банковский connector
- [ ] Workflow: ожидание счёта → получение → категоризация → оплата → приложение factura
- [ ] Quarterly AEAT reports check

### 3. End-to-end supervision
🔴 **CONCEPT**

**Kanban view на pedido с стадиями:**
```
draft → confirmed → received → unpacked → priced → labeled → on_sale
```

Можно реализовать через:
- Extended `stock.picking.state`
- Либо отдельный `x_studio_supervision_stage` selection на purchase.order
- Либо custom model с workflow

---

## P4 — Compliance и инфраструктура

### Испанский compliance
Из `FLOR-gov_-_Odoo_и_испанскии__план_счетов__1_.pdf` (226 стр):
- [ ] Проверить работу Modelo 303 (VAT monthly/quarterly) — автогенерация
- [ ] Modelo 347 (annual operations > 3005.06€ total)
- [ ] Modelo 349 (EU intra-community)
- [ ] **VeriFactu** (Anti-Fraud Law) — нужны отдельные модули / доработка
- [ ] **SII** (Suministro Inmediato de Información AEAT) — отдельно
- [ ] Electronic invoicing (Factura-E / UBL)

### Infrastructure scaling
- [ ] Мониторинг нагрузки Odoo.sh
- [ ] Перед пиками (8 марта, 14 февраля) → апгрейд до 2-3 Workers
- [ ] Storage plan — сжатие/архивация attachments
- [ ] Backup verification — периодически тестировать recovery

---

## P4 — Workflow улучшения (nice to have)

- [ ] Multi-warehouse split одного albarán (user story 4.5)
- [ ] Pricelist multi-channel (витрина vs online)
- [ ] Extra images / gallery для товаров
- [ ] Error tracking для аналитики (ошибки флористов)
- [ ] Name_search override для поиска по `x_studio_codigo_fabrica`

---

## ⚠️ Deprecated / не доделанное

- `x_studio_many2many_field_4qh_1jkvk330u` («New Tags») — label переименован, но Studio не даёт удалить физически. Можно попробовать через Studio UI вручную.
- `x_studio_legacy_source` на source-form — планировался, потом убран (см. [06_catalog_migration_toolkit.md](06_catalog_migration_toolkit.md))

---

## Регламент

Старый **регламент сотрудников** (Google Doc 29 MB):
- Построен на Holded workflows
- После запуска MVP → постепенно переписываем разделы под Odoo
- Актуальная версия будет эволюционировать из [05_florists_logistics_accountant.md](05_florists_logistics_accountant.md)

---

## Короткий roadmap

| Период | Цель |
|---|---|
| **До 20 апреля** | MVP запуск, walk-through UI, P0 items |
| **21 апреля — 4 мая** | Массовый импорт albaran (сотрудник), мелкие фиксы |
| **Май** | Импорт продаж, формирование нового каталога, начало миграции |
| **Июнь-июль** | UX рабочих мест, ролевые views, POS правила |
| **Август-октябрь** | Marketplace integrations (Flowwow, Glovo) |
| **Ноябрь-декабрь** | Финализация compliance, analytics workspace |
| **1 января 2027** | Full cutover с Holded на Odoo |
| **Февраль-март 2027** | Optimization, подготовка к 8 марта (пик) |

---

## См. также

- [CHANGELOG.md](CHANGELOG.md) — что было сделано когда
- [99_invariants.md](99_invariants.md) — правила, нарушение которых создаёт техдолг
