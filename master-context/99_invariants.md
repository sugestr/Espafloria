<!-- v: 4 | updated: 2026-04-19T23:30Z -->
# 99. Invariants — железные правила проекта

**Читать перед любыми изменениями в системе.** Нарушение этих правил создаёт техдолг, ломает бот или теряет данные.

---

## 🏗️ Архитектурные

### 1. Не смешивать reconciliation и receipt review
- `purchase.order.line` = слой «что заказано и согласовано с бумагой»
- `stock.move` = слой «что реально приехало и принято»
- **Один не управляет другим.** Факт приёмки не переписывает бумагу. Бумага не перезаписывает факт.

### 2. Бумага ≠ факт ≠ логист. Odoo — инструмент отражения, а не диктатор
Один товар имеет **три независимых взгляда**, хранящихся отдельно:
- `purchase.order.line.product_qty` — **бумага поставщика** (одно из представлений, не истина)
- `x_studio_expected_qty` — **оценка логиста** (подсказка, не факт)
- `stock.move.quantity` — **факт флориста** (складская правда)

**Ни один не переписывает другой.** Система не должна **автоматически** писать `quantity` или `packs` за флориста на основе расчёта. Только человек решает, сколько реально принято.

Odoo — **инструмент отражения** реальности магазина, а не её диктатор.

### 3. `Receipt = операционная правда`, не PO и не Invoice
Склад отражает то, что принял флорист. Бухгалтерия (bill) может отражать бумагу. Разница — в аналитике, но не в складских остатках.

### 4. UoM = технический label, НЕ business truth
Особенно для пачек. Pack = «штук не ясно сколько», вычисляется в момент приёмки.

### 5. Пустое важнее ложного нуля
Если логист не считал — показывать пусто, не `0`. Отсюда sentinel `-1` для `stock.move.quantity`.

---

## 🤖 Make.com бот / Reconciliation

### 6. Learned Odoo vendor code = сильный положительный сигнал
Если `paper.supplier_sku == data[].product_code` → **confidence растёт**, не падает. Даже если внутреннее имя в Odoo ugly/legacy (`[8400253] 🚫 MARFULL - rama` vs paper «Photinia Red Robin»).

### 7. Operator hit (`x_studio_operator_hit`) ≈ прямая команда
Уважается выше semantic similarity, broad family, line order. Исключение только hard species conflict (`rose ↔ tulip`, `vase ↔ flower`).

### 8. A wrong match is worse than an unmatched line
Не максимизируй coverage за счёт identity safety. Broad category tokens (`bouquet`, `bqt`, `mix`, `tropical`, `greenery`) **не доказывают identity**.

### 9. Good identity match survives quantity/tax/price mismatches
Расхождение количеств / налогов / цен — diagnostic, НЕ disqualifying. Держим match, диагностируем отдельно.

### 10. `manual_review` НЕ dump bucket
Используется только когда остаётся конкретный concrete identity risk. Если identity unsafe — идёт в `unmatched`, не в manual_review.

### 11. Diagnostics смотрит на FINAL state, не pre-update
Diagnostics prompt (`prompt_diagnostics_v3.1`) должен опираться на **FINAL PEDIDO AFTER UPDATES** + COMPARISON RESULT, не только на pre-update mismatch.

### 12. Make.com string-handling опасен
- **Никогда** не передавать boolean в string-функции (`replace(false, ...)` ломается)
- Всегда защищать через `ifempty(...; "")`
- `toString(...)` безопаснее `formatNumber(...)`
- Простой шаблон > красивый хрупкий

---

## 🏭 Odoo приёмка и automations

### 13. Нет каскадных `write()` в automation rules
Line-level automation — только для **текущей** строки. Document-level — только явной кнопкой / server action. Иначе Odoo висит или рекурсивно триггерит сам себя.

### 14. `When updating field` в automation — **узкий список**
Только `quantity` + `x_studio_received_packs` для review-status. Не включать: `picking_id`, `purchase_line_id`, структурные поля, review-статусы (иначе авт-рекурсия).

### 15. `x_studio_paper_unit` — это `uom.uom` record, не string
- ❌ `.strip()` не работает (SafeEval ошибка)
- ✅ Использовать `.display_name` или `.name`

### 16. `hasattr()` недоступен в Odoo safe_eval
- ❌ `hasattr(record, 'field_name')`
- ✅ `'field_name' in record._fields`

### 17. `On create` + `After creation delay` ненадёжны
- Odoo может перезаписать значения своей логикой
- Delayed actions срабатывают недетерминированно (даже после Cancel/state change)
- Для reset-логики — только явная кнопка

---

## 💰 Bill control policy

### 18. Цветы / горшечка → `On ordered quantities`
Для `FLORES CORTADAS` и `PLANTAS EN MACETAS`. Vendor bill = `product_qty` (бумага), не `qty_received`. Мелкие недопоставки — в норме.

### 19. Backorder = решение по физической логистике, НЕ финансовое
Create Backorder / No Backorder выбирается по вопросу **«ждём ли реальный довоз товара?»**, не «есть ли расхождение».

**Если поставщик не привезёт никогда** → No Backorder + **отдельная финансовая работа:**
- Претензия поставщику
- Запрос возврата денег / credit note
- Корректирующий vendor bill через бухгалтера

**Backorder ≠ решение финансовой проблемы.** Закрытие backorder'а не означает, что вопрос с деньгами закрыт — это отдельный трек.

---

## 🗂️ Миграция каталога

### 20. История не переносится
Старые pedido / RFQ / продажи остаются на старой (архивной) карточке. Новая — чистый слой, для новых операций.

### 21. При миграции копируем `product.supplierinfo` на target
Patched 2026-04-18 — иначе learned vendor codes теряются и Make.com бот перестаёт матчить supplier_sku.

### 22. Target variant не может быть из карантина
Domain на `x_studio_target_variant` явно исключает `child_of 207`. Плюс защита в коде server action.

### 23. SKU/barcode префикс `OLD_` на архивной
`default_code` / `barcode` старой становятся `OLD_<original>` — чтобы не конфликтовали с новой карточкой, которая получает настоящий код.

---

## 🛒 POS и магазины

### 24. Карантинные карточки не продаются до решения владельца
Сейчас `sale_ok = False` на всех 1983 карточках в карантине.

**План A (предпочтительный):** новый каталог собирается из товаров, закупленных в 2026 → инвентаризация на новых → запуск продаж только через новый каталог. Карантин остаётся закрытым, карточки постепенно мигрируются.

**План B (резервный):** если новый каталог не успеваем к дате запуска → разблокировать карантин массовым `sale_ok = True`, мигрировать постепенно по ходу работы. **Решение владельца перед MVP-датой.**

В любом плане — случайная продажа из карантина без осознанного решения = bug.

### 25. Первая продажа твёрдого товара = триггер пересчёта (rolling inventory)
Для `DECORACION` / `EMBALAJE` / `PRODUCTOS ESPECIALES/DECORACION` при запуске MVP остатки берутся из Holded as-is. При **первой продаже** такой позиции в конкретном магазине — магазин получает задание пересчитать эту SKU.

Это не блокер продажи (продаём по кассе нормально), а **параллельная задача магазину**. Rolling correction вместо сплошной инвентаризации вазодекора.

До реализации задания — держать принцип в голове как правило работы ролей, см. [09](09_open_work.md) P2.

---

## 🏭 Инфраструктура

### 26. Не заглубляться в Odoo.sh Custom без необходимости
Обратной дороги нет: после установки `custom_addons` / добавления Studio-полей возврат на Standard невозможен. **Прежде чем добавлять custom-зависимость — проверь, делается ли это штатно.** Каждый новый custom field / module — осознанный выбор с пониманием, что его придётся поддерживать вечно.

### 27. Каждый новый Odoo-вызов бота = осознанное решение
1 HTTP Worker × ~300ms/call × 19 текущих вызовов на pedido = ~6s. При сезонных пиках любой лишний N+1 превращается в 502.

**Прежде чем добавить новый XML-RPC вызов в сценарий** — проверь:
- нельзя ли получить те же данные из уже сделанного `search_read`;
- нельзя ли объединить с существующим `write`;
- действительно ли он нужен на каждую строку, или можно document-level.

---

## 🔧 Процесс работы

### 28. CHANGELOG обязателен
После **любого** изменения в базе (своими руками или через API) — запись в `CHANGELOG.md` с датой, автором, что изменили.

### 29. Перед массовыми операциями — тест на одной записи
Миграция карточек, bulk-update полей, массовое изменение `purchase_method` — сначала ОДНА запись, проверка результата, потом batch.

### 30. Studio field deletion — часто защищено
Если нельзя удалить через API / UI — переименовать label в `[DEPRECATED] ...` и игнорировать.

---

## 👥 Роли и процессы (добавлено 2026-04-18)

### 31. Списание без фото-согласования главного флориста ≠ списание
Флорист **не может** списать товар самостоятельно. Процесс обязательный:
выбор позиций → фото-доказательство → отправка на утверждение → одобрение главным флористом → списание.
Альтернатива — «забытые» списания и неотслеживаемые потери, что противоречит целям «умной сети».

### 32. Букет — живая сущность с жизненным циклом, пока не разобран/продан

**Жизненный цикл букета:**
```
Создан (фото, номер, ценник) →
  → [существует, может модифицироваться] →
    → Разобран (компоненты возвращаются на склад)  ← уничтожение
    ИЛИ
    → Продан (чек)  ← уничтожение
```

Пока букет **не разобран и не продан** — он отдельная учётная сущность, видимая в системе, с собственной историей изменений, фото, привязкой к флористу-сборщику.

**Следствия:**
- После разборки — сущность закрывается, компоненты доступны снова
- После продажи — сущность закрывается через sale.order.line
- Модификация (добавить розу, убрать 1 как завявшую) — это изменение живой сущности, не создание новой
- Скидка применяется **на уровне букета**, не на уровне строк компонентов. Скидка по строкам «неудобно и недостоверно» — решение владельца.

### 33. Бонусы — личные, не коллективные
Каждая продажа и каждый обработанный онлайн-заказ привязан к конкретному сотруднику через смену.
Коллективное «5% от продаж смены поровну» **отвергнуто** в пользу личной мотивации.
Без привязки к сотруднику бонусная модель не работает → PIN-авторизация в POS = **не UX-удобство, а блокер бизнес-модели**.

### 34. Аналитика точна только для периода после миграции каталога
Гибридный период (старые + новые карточки) даёт смешанные данные.
Отчёты «год к году» врут первый год.
Маркетолога/закупщика предупреждать явно при работе со старыми данными.

### 35. Marketplace = юридически посредник, клиент — наш
**Решено 2026-04-19.** Flowwow, Glovo, Instagram Shop, WhatsApp-заказы, будущий свой сайт — все юридически посредники. В учётной модели:
- **Клиент** — конкретный человек, который получил букет. Его `res.partner` — в нашей CRM.
- **Платформа** — не покупатель, а channel/intermediary. Комиссия платформы = наш расход (снижение маржи), НЕ скидка клиенту.
- **Cash flow:** клиент платит платформе → платформа удерживает комиссию → платформа перечисляет нам остаток. Три независимые проводки, не одна.

**НЕ моделировать** продажу как "клиент = Flowwow" — это ломает LTV клиента, атрибуцию бонусов сотруднику, и комиссия теряется в скидках.

Комиссия **может отличаться по каждому букету** (особенно Flowwow) — учитывать per-line, не per-document.

---

## 🔌 Платформенные зависимости (добавлено 2026-04-18)

### 36. Падение баланса внешнего сервиса = тихий отказ бота
Make.com бот зависит от 3 платных сервисов (Make operations, CloudConvert, OpenAI).
**Ни один не выдаёт явную ошибку когда баланс кончился** — сценарий просто не выполняется / обрывается.
**При любой проблеме бота — первым делом проверять балансы и OAuth-статус коннекторов**, только потом код.

### 37. Продажа в минус = индикатор проблемы, не норма
Продажа товара, которого по системе нет на складе (negative stock) — **всегда плохой сигнал**. Возможные причины:
- Не сделана инвентаризация
- Не проведена приёмка
- Забыто списание порчи
- Ошибка при пробитии (не тот товар в чеке)
- Воровство / потеря

**Правильная позиция системы:** стараться **запрещать** на уровне UX или **явно предупреждать** флориста с требованием подтверждения.

**НЕ допускать как «разрешённая практика на запуске»** — даже если временно допустимо (чтобы не стопать продажи), каждый случай должен фиксироваться и разбираться отдельно. Это **индикатор неучтённой реальности**, а не рабочая фича.

При запуске MVP — **приоритет инвентаризации ДО первых продаж**, а не «давайте запустимся с минусами и разберёмся потом».

---

## 🗂️ Миграция каталога v2.2 (добавлено 2026-04-19)

### 38. `list_price=1.0` default блокирует copy-if-empty
Odoo на `create` ставит `list_price=1.0` по умолчанию. Migration script v2.2 использует правило «copy from source only if target is empty/zero». `1.0` truthy → `not 1.0 = False` → цена с source НЕ переедет.

**Правило:** при создании skeleton template для миграции ВСЕГДА передавать `list_price: 0.0` явно. Проверено на баге ROSA 7834 (list_price застрял 1.0 вместо 3.64 из source) — после фикса MARFULL/EUCALIPTO/CRISANTEMO перенесли цены правильно.

Альтернативный фикс (не применён) — правило `target.list_price <= 1.0`. Не выбран: `1.0` может быть осмысленной ценой, не хотим затирать.

### 39. POS tile image source зависит от формы target
POS кассир видит картинку карточки из:
- `product.template.image_1920` — если template flat (1 variant, нет attributes)
- `product.product.image_variant_1920` — если template multivariant (N variants, чтобы отличаться на кассе)

Migration v2.2 автоматически соблюдает это правило: при `target_is_flat` пишет в template, при multivariant — в variant.

### 40. Product Category ≠ POS Category — разные концепции
- `product.template.categ_id` (m2o, required) — бухгалтерская/складская категория. Определяет GL accounts (revenue, expense, stock valuation), правила учёта, inventory filters, reporting group-by. Живёт в `product.category` дереве.
- `product.template.pos_categ_ids` (m2m, optional) — UI-группировка на экране кассира. Определяет под какой кнопкой в POS UI карточка появляется. Одна карточка может быть в нескольких (напр. «Rosas» + «Ramo Regalo»). Живёт в отдельном `pos.category` дереве.

Не смешивать. Product category ~10 штук (стабильная, accounting-driven). POS category ~5-8 (UX-driven, меняется под нужды кассира).

### 41. Scripts: source-of-truth в проекте, Odoo = mirror
Любой server action / automation rule содержащий Python-код должен иметь source-of-truth `.py` файл в `master-context/`. Odoo — mirror, не источник. Любое изменение одного — обязательная синхронизация второго.

**Причина:** потеря БД = потеря всех скриптов. Плюс файл даёт git-history, review, возможность deploy на staging.

Актуальные пары:
- `migrate_variant_action.py` ↔ `ir.actions.server id=1145` (UI trigger v2)
- `migrate_variant_v2.2.py` ↔ `ir.actions.server id=1176` (execute v2.2)
- `calculate_in_shop_action.py` ↔ `ir.actions.server id=1150`
- `review_status_automation.py` ↔ `ir.actions.server id=1146`

### 42. Odoo 19: archive/restore делать через template-level write
При archive-restore операциях писать `active=False` / `active=True` **на template level**, не на variant. Odoo каскадирует template → variants автоматически. Write в `variant.active` может создать desync (template.active=True, variant.active=False).

Проверено на rollback delivery миграции: три template остались `archived=true`, variants `active=true` — исправилось единичным write в template. Правило: `archive source` в v2.2 скрипте пишет в `source_template`, не в `source` (variant).

### 43. Studio-поля на template и variant — писать template-level для UI visibility
Если Studio-поле существует на обоих уровнях (template direct + variant related) — писать на template. Только так значения гарантированно видны на template form и на всех наследующих views. Variant-only значения могут не пробросить наверх в UI.

Проверено на баге «у Entrega Barcelona Zona 2 секция MIGRATION пустая» (v2.1 писал только variant-level `x_studio_variant_legacy_source`, template-level `x_studio_legacy_source` оставался `false` → на форме Migration section показывал пусто). Fix в v2.2: template-level `legacy_source` + `migration_status` пишутся всегда безусловно.

---

## Краткая мнемоника

> **Paper ≠ Truth. Receipt = Truth. Logist = hint. -1 ≠ 0. Odoo = mirror, not dictator.**
> **Learned code boosts confidence. Operator hit is a command. Wrong match > unmatched only for safety.**
> **Diagnostics sees final state. Automation triggers are narrow. Cascades kill Odoo.**
> **Flowers = ordered policy. Backorder = logistics. Quarantine = no sales.**
> **History stays. Migration copies supplierinfo. Target != quarantine.**
> **Marketplace = intermediary. Client is ours. Commission ≠ discount.**
> **Skeleton → list_price=0. POS tile reads template image if flat. Scripts source-of-truth in repo, Odoo mirror.**

---

## Когда нарушать (legitimate exceptions)

- **Инвариант 6 (learned code)** → нарушается только при clear hard species conflict (rose vs tulip)
- **Инвариант 7 (operator hit)** → та же логика
- **Инвариант 13 (cascading writes)** → можно сделать в **явной кнопке** если пользователь понимает риск
- **Инвариант 18 (bill policy = purchase)** → для твёрдого товара (вазы, декор) — `receive` намеренно
- **Инвариант 24 (no quarantine sales)** → после завершения миграции карточки в архив — можно разблокировать (но не в карантине)

---

## См. также

- [00_master_index.md](00_master_index.md) — навигация
- [CHANGELOG.md](CHANGELOG.md) — история изменений
- Все файлы 01-11 — контекст применения инвариантов
