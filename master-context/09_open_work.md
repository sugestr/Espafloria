<!-- v: 8 | updated: 2026-04-23T01:40Z -->
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
- [x] ✅ **Walk-through UI для флориста** — первая POS-сессия прошла end-to-end 2026-04-19 (ROSA RED NAOMI 4€ через Efectivo Plaza, ticket 261-1-000002). Планшет-режим работает.
- [x] ✅ **Тестовая миграция 1 карточки** — мигрировано 10 карточек через v2.2 (6 deliveries + 4 flores). supplierinfo копируется корректно с дедупликацией. См. [06](06_catalog_migration_toolkit.md).
- [x] ✅ **eWallet prepayment chain** (2026-04-21) — программа создана и end-to-end проверена через top-up Tata 100€ + redemption 3€ + close session. JE 19/20/21 verified. См. [08 §E](08_current_state_snapshot.md), [99 §44/45](99_invariants.md).
- [ ] **Добавить `qty_received` + `qty_invoiced` в view `purchase.order.line`** (Studio, 2 минуты)
- [x] ✅ **Config fix POS warehouses:** склады Plaza/Gloria/Blau (id=2/3/4) существовали. POS Gloria и Blau были привязаны к Plaza — починено 2026-04-19. См. [08 §A/§B](08_current_state_snapshot.md).

### Рабочее место флориста (P0-секция, приоритет для следующей сессии)
- [ ] 🔴 **POS Categories setup** — на всех 3 configs `iface_available_categ_ids=[]`. Кассир не может быстро фильтровать Rosas / Ramas / Plantas / Servicios. Создать `pos.category` дерево (~5-8 категорий), bulk-set `pos_categ_ids` на 10 мигрированных карточках + 2 eWallet (служебная категория, чтобы не попадались среди цветов).
- [ ] **POS tile visual test** — открыть POS Plaza, убедиться что 10 мигрированных карточек корректно отображаются как tiles (цена, картинка, имя, VAT).
- [ ] **End-to-end тест продажи с доставкой** — 3 розы + Entrega Barcelona Zona 1 → Validate → проверить Holded invoice через make.com бота.
- [ ] **Bulk tax adjustment post-migration:** `categ_id child_of 287` (Flores Cortadas) → sale tax 82 / purchase tax 68 (10% G); услуги Deliveries → sale 5 / purchase 21% G (найти id). Одним bulk-update.
- [ ] **POS Terminal password change** — смена дефолтного `PosTerminal2026!` на финальный (или убрать login password и положить планшеты в kiosk mode).
- [ ] **Andriy PIN для manager** — `hr.employee.pin` на Andriy сейчас пуст. Поставить 4-значный PIN для manager-override в POS (approval скидок >10%, закрытие смены, Cash In/Out supervision).
- [ ] **Cosmetic fix:** POS payment method `Efectivo Blaus` (id=5) → переименовать в `Efectivo Blau` (лишняя s, journal правильный).
- [ ] **Косметика чека** — загрузить логотип Espafloria, заполнить телефон/адрес компании (сейчас placeholders и false в чеке).

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
1. Расширить domain модуля 108 (search_read purchase.order) на `(supplier_vat, document_number)` — чтобы до входа в Router 110 уже знали про дубль
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
- [ ] **Multivariant target support в скрипте v2.2** — первая цветочная карточка с attributes (напр. Rosa Red Naomi 40/50/60 cm) → тест ветки `image_variant_1920` + `product_id=target.id` на supplierinfo copy.
- [ ] **Dry-run mode** — preview без write (полезно для bulk операций).

### Make.com bot: OLD_ SKU awareness
- [ ] Модуль 94 + prompt reconciliation: при `pedido_date < migration_date(target)` — искать archived OLD_ source карточку. См. [02 § OLD_ SKU awareness](02_makecom_bot.md). Без этой логики старые pedido не найдут свою (уже archived) карточку.

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

### 🆕 POS rights granularity (запрошено owner 2026-04-21)

Сейчас `pos_hr` даёт **только 3 уровня** (`minimal_employee_ids` / `basic_employee_ids` / `advanced_employee_ids`). Все наши флористы в `advanced` — это слишком разрешительно для рядового персонала.

**Цель:** более тонкая гранулярность. Возможные оси:
- Скидки (max %, требует ли подтверждения, manager PIN override порог)
- Возврат / Refund (разрешён? на какую максимум сумму?)
- Open/Close session
- Cash In/Out (фиксированный лимит per shift?)
- Создание product on-the-fly из POS
- Доступ к чужим orders / истории чеков
- Привилегия отменять order (не возврат, а cancel до payment)
- Manager override через свой PIN (для approval action со стороны старшего)

**Что есть из коробки:**
- `hr.employee.pin` для approval-flow (manager confirms на чужом устройстве)
- `pos.config.amount_authorized_diff` (разрешённое расхождение при close)
- 3 tier'а `*_employee_ids` (built-in)
- `manual_discount` boolean per-config
- Group `point_of_sale.group_pos_user` vs `group_pos_manager` на уровне res.groups

**Что нужно:**
- [ ] Изучить Odoo 19 OCA модули `pos_*_security` если есть
- [ ] Маппинг "роль флориста" → набор разрешений (junior / senior / manager)
- [ ] Решить: Studio/configurator vs custom модуль
- [ ] PIN manager-override на конкретные действия (не глобальный admin доступ)

**Связь с инвариантами:** [99 §33](99_invariants.md) (бонусы личные → нужна точная attribution per employee), [99 §31](99_invariants.md) (списания через approval только manager).

### 🆕 Букеты как сущность (workstream — отдельная сессия)

Это большая тема, требует дизайн-сессии перед реализацией. Контекст: [05 §1.2](05_florists_logistics_accountant.md), [99 §32, §46](99_invariants.md).

**Главные вопросы:**
- [x] Где живёт «букет»? — Решено MVP: `sale.order` с partner=Anon id=53, именем `BP-YYYY-NNNN`. Не MRP BoM, не custom model — просто SO с привязкой строк через `sale_order_origin_id` (Settle).
- [x] Жизненный цикл: Created → [modifications] → Disassembled OR Sold — Created + Modified (reassemble) + Disassembled + Sold все реализованы 2026-04-18/23 через POS. Списание завядшей розы как отдельного событие (не через reassemble) — ещё нет, связано с writeoff-workstream.
- [x] Уникальный номер букета (sequence) — `BP-YYYY-NNNN` через `ir.sequence` per-warehouse (espafloria.bouquet.plaza/.gloria/.blau).
- [ ] Фото при создании (обязательно, не опционально)
- [ ] Две цены: shop vs online (через pricelist rules или поля на букете?)
- [ ] Печать ценника (термопринтер, brand layout)
- [ ] Скидка применяется на уровне букета, не на компонентах (инвариант 32)
- [x] **Make-on-sale** (флорист собирает на месте у клиента) — реализовано через payment method «Собрать букет». **Pre-built** (на витрину утром, продаётся днём) — ещё нет.
- [x] Модификация (добавить розу, удалить строку, изменить цену) — реализовано через reassemble-ветку action 1203: Settle + правка в корзине + «Собрать букет» без маркера → старый SO cancel + новый SO с обновлёнными линиями. См. [05 §1.2.2](05_florists_logistics_accountant.md). *«Удалить как завядшую»* (writeoff с фото) — отдельный workstream.
- [x] Disassembly — компоненты возвращаются на склад (через Settle + marker product 7865 + 3 слоя автоматик, см. [99 §46](99_invariants.md))
- [ ] Связь с eWallet: предоплата за «букет на пятницу» → loyalty.card → к моменту pickup букет готов с этим номером
- [x] POS UX: как флорист собирает букет в POS без line discount (одной кнопкой?) — payment method «Собрать букет» = одно касание.

**Решить ДО начала разработки:**
- [ ] Должен ли букет быть `product.template`/`product.product` (sale-able first-class), или отдельной моделью с привязкой к sale.order.line через relate?
- [ ] Как считается себестоимость (rolling avg компонентов на момент создания, или fix at create time)?
- [ ] Что в чеке у клиента: «Ramo personalizado #B-2026-0001» (одна строка) или развёрнутый список компонентов?
- [ ] Как видит букет бухгалтер (агрегированная sale + COGS, или построчная)?

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
- [ ] Rolling inventory для ваз/декора: задание пересчёта при первой продаже (см. [99 §25](99_invariants.md))
- [ ] Контроль выполнения: статус + напоминания при задержке

### POS
- [x] Быстрая сборка букета на месте без line discount (2026-04-18, через payment method «Собрать букет»). Расширено 2026-04-23: dismantle + modify (reassemble). См. workstream «Букеты как сущность» выше для оставшихся задач.
- [ ] Фото готового букета → sale.order.line

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

---

## P3 — Новые workstreams (каждый требует отдельной сессии)

### P3.1 CRM и клиенты (см. [11_crm_and_customers.md](11_crm_and_customers.md))
- [x] ✅ **MVP базовая клиентская карточка через POS** — работает (тестирована на Tata, Vasilij, Pedro 2026-04-21)
- [x] ✅ **eWallet baseline для loyalty** — программа eWallet активна, можно использовать как фундамент future loyalty (см. [08 §E](08_current_state_snapshot.md))
- [ ] История покупок через `partner_id` (штатно)
- [ ] Этап 2: сегментация (VIP / Regular / Dormant / New)
- [ ] Первые email-рассылки через `mass.mailing`
- [ ] **Loyalty Cards program** (помимо eWallet — отдельная программа `loyalty` type для баллов за покупки)
- [ ] WhatsApp интеграция (Wati / 360dialog / custom — решить)
- [ ] Напоминания о значимых датах клиентов (ДР, годовщины)
- [ ] GDPR compliance (opt-in, right to deletion)

### P3.2 Flowwow integration
🔴 **CONCEPT** — учётная модель зафиксирована ([99 §35](99_invariants.md): marketplace = посредник, клиент — наш, комиссия = расход). Техническая интеграция остаётся без брифа.

**Что нужно разобрать:**
- [ ] Модель учёта комиссии per-line (комиссия может отличаться по каждому букету)
- [ ] Импорт продаж из Flowwow (CSV / API?)
- [ ] Формирование чеков для испанской бухгалтерии (SII требования)
- [ ] Три независимые проводки: продажа клиенту / комиссия платформы / cash movement от платформы

### P3.3 Glovo integration
🔴 **CONCEPT** — новый workstream. Та же учётная модель что Flowwow ([99 §35](99_invariants.md)).

**Специфика Glovo:**
- Delivery-first (курьерские окна)
- Другая комиссионная модель
- Возможно другой flow подтверждения заказа
- [ ] Учёт курьерских комиссий
- [ ] Время сборки (SLA)
- [ ] Связка с физическим витринным запасом

### P3.4 Catch-weight / variable pack content

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

### P3.5 Бухгалтерская автоматизация (три задачи бухгалтера)

#### Sales reconciliation
🔴 **CONCEPT**

**Пайплайн (идея):**
- Make.com читает Telegram-чаты магазинов (отчёты смены)
- Парсит суммы, время, магазин
- Сверяет с `pos.session.total_cash` + bank statement
- Формирует report: OK / extra cash / missing cash / mismatch
- UI: view «несверенные смены» с прямыми ссылками

#### Expense pipeline + Spanish chart of accounts
🟡 **READY** — `l10n_es` локализация установлена, Modelo 303/347/349 есть.

**Что доделать:**
- [ ] AI-pre-categorization счетов (можно на базе OCR-промпта из бота)
- [ ] `account.online.link` банковский connector
- [ ] Workflow: ожидание счёта → получение → категоризация → оплата → приложение factura
- [ ] Quarterly AEAT reports check

#### End-to-end supervision
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

## P4 — Долгосрочное (compliance, nice-to-have)

### P4.1 Испанский compliance
Из `FLOR-gov_-_Odoo_и_испанскии__план_счетов__1_.pdf` (226 стр):
- [ ] Проверить работу Modelo 303 (VAT monthly/quarterly) — автогенерация
- [ ] Modelo 347 (annual operations > 3005.06€ total)
- [ ] Modelo 349 (EU intra-community)
- [ ] **VeriFactu** (Anti-Fraud Law) — нужны отдельные модули / доработка
- [ ] **SII** (Suministro Inmediato de Información AEAT) — отдельно
- [ ] Electronic invoicing (Factura-E / UBL)

### P4.2 Infrastructure scaling
- [ ] Мониторинг нагрузки Odoo.sh
- [ ] Перед пиками (8 марта, 14 февраля) → апгрейд до 2-3 Workers
- [ ] Storage plan — сжатие/архивация attachments
- [ ] Backup verification — периодически тестировать recovery

### P4.3 Workflow улучшения (nice to have)

- [ ] Multi-warehouse split одного albarán (user story 4.5)
- [ ] Pricelist multi-channel (витрина vs online)
- [ ] Extra images / gallery для товаров
- [ ] Error tracking для аналитики (ошибки флористов)
- [ ] Name_search override для поиска по `x_studio_codigo_fabrica`

---

## ⚠️ Deprecated / не доделанное

- `x_studio_many2many_field_4qh_1jkvk330u` («New Tags») — label переименован, но Studio не даёт удалить физически. Можно попробовать через Studio UI вручную.
- `x_studio_legacy_source` на `product.template` — поле существует, но action 1145 фактически не заполняет его на source-записи (см. [06](06_catalog_migration_toolkit.md) как канон). Для Variant-side информация хранится в `x_studio_variant_legacy_source`. Можно либо скрыть source-side поле из Studio view, либо начать его использовать — решение открыто.
- **pos.order id=2-8 (тестовые от 2026-04-21):** state=done без связанных pos.payment и account.move (после reset тестовых данных). ORM не даёт удалить state=done через API. На production не влияют. Удалить если потребуется — через SQL DELETE на бэкенде Odoo.sh.

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
| **21 апреля — 4 мая** | Массовый импорт albaran (сотрудник), мелкие фиксы, POS rights granularity, букеты-как-сущность дизайн-сессия |
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
