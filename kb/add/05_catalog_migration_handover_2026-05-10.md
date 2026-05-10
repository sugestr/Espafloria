<!-- v: 1 | updated: 2026-05-10T00:00Z -->
# 05 — Catalog migration handover (2026-05-10)

**Status:** 🟡 IN-PROGRESS — block A1 (audit) начат, прерван AUP-сбоем в предыдущей сессии. Этот файл — handoff для продолжения с того же места.

**Что в файле:**
- 14-блочный план миграции каталога A1→A14
- Зафиксированные дизайн-решения (settled — не пере-обсуждаем)
- Прогресс блока A1 (что сделано / что осталось)
- Открытые вопросы owner'у (5 штук, ждут ответа)
- Notes для resume в новой сессии

**Триггер для следующего чата:** «продолжить с блока A1». Этот файл — единственная точка входа.

---

## 1. Контекст

В системе под категорией `categ_id child_of 207 ⛔ Карантин Holded` лежит ~2152 нормированных Holded-карточек после re-import. Цель — за 14 шагов вытащить их в новую структуру каталога (атрибуты + варианты + категории + POS + цены), не сломав работающий pedido-pipeline и не остановив магазин.

**Ключевой принцип** — не trust того что уже есть на карточках (`x_studio_*`, supplierinfo, attributes) сверх минимума. Заново собирать признаки из source pricelist'ов поставщиков.

---

## 2. Карта блоков A1→A14

| # | Смысл блока |
|---|---|
| **A1** | Снимок: что у нас сейчас в Odoo и чего не хватает по сравнению с Holded |
| **A2** | Дотащить пропущенные Verdnatura-документы из Holded compras в Odoo |
| **A3** | Из данных поставщиков (закупочные pricelist'ы) вытащить структурированные признаки на каждую карту |
| **A4** | Нарисовать новое дерево каталога — вместе со старшим флористом, опираясь на A3 |
| **A5** | Собрать одну группу-вариативку (например розы Red Naomi 40/50/60) полностью end-to-end — как пилот |
| **A6** | Создать пустые целевые карты и пере-везти все остальные через нашу процедуру миграции |
| **A7** | Привести налоги и логику счетов на новых картах |
| **A8** | Настроить POS-вкладки для кассы (зеркало учётного дерева + полезные тематические) |
| **A9** | Пересчитать и утвердить цены продажи + переключение системы на «работа с НДС внутри» |
| **A10** | Флоу «надо переклеить ценник» как живая задача магазину с отметкой о выполнении |
| **A11** | Апрельские поставки садятся на новый каталог — остатки появляются |
| **A12** | Открыть кассы + проверка остатков естественной инвентаризацией при первой продаже |
| **A13** | Твёрдый товар отдельным треком: 1:1 миграция, остатки из Holded, без реструктуризации |
| **A14** | Журнал миграции — старая карта ↔ новая карта — для аудита и для бота |

**Нумерация в чате:** `A1` блок → `A1.1, A1.2, ...` подпункты → `A1.6.1, A1.6.2, ...` вопросы внутри подпункта. Owner отвечает «A1.7.2: ...» или просто «1.8.1: ...».

---

## 3. Зафиксированные дизайн-решения (settled — не пере-обсуждаем)

### 3.1 Цена при миграции — 5 review-status кодов

Новое custom selection поле `x_studio_price_review_status` на product.template:

| Код | Что значит |
|---|---|
| `accept_old_ok` | старая цена, маржа норм, оставляем |
| `review_too_cheap` | старая цена, продаём слишком дёшево, менеджер пересмотрит |
| `review_too_expensive` | старая цена, слишком дорого, менеджер пересмотрит |
| `new_x3_placeholder` | новая карточка, цена ×3 закупки как заглушка до пересмотра |
| `verified` | OK, последняя проверка дата X пользователем Y |

Дополнительно: `x_studio_price_reviewed_by` (m2o → res.users) + `x_studio_price_reviewed_on` (date).

### 3.2 Переключение системы на VAT-included — отложено в A9

Сейчас prices без НДС. Хотим VAT-included для удобства POS + логистики. Открытые подвопросы (для A9):
- Когда щёлкаем рубильник
- Что увидит бухгалтер на следующий день
- Что увидит флорист на ценнике
- Custom margin-поля (вероятно работают на pre-VAT, остаются как есть)

### 3.3 Migration procedure v2.2 — без изменений

Source SKU+barcode → `OLD_` префикс, target наследует. UI: «Replace With Variant: ___» → Save → Actions → Migrate. Source archive через template.write (cascade). Toolkit код в `kb/add/05_migrate_variant_v2.2.py` — уже верифицирован на 10 миграциях до reset'а. Supplierinfo копируется с dedup по `(partner_id, product_code)`.

### 3.4 Атрибуция supplierinfo — re-extract из source

На карточках уже есть два ключа от поставщика: standard `product_code` + custom `x_studio_supplier_identity_key` (composite key для Serviflor). **НЕ доверять** значениям что уже залиты sub-agent'ами — заново извлекать из source pricelist'ов в блоке A3.

### 3.5 MIX-карточки — двух-уровневая полка специально

Дешёвый MIX (~12€) и дорогой MIX (~37€) — разные продукты, не сливаем в один. **Critical:** MIX-карточки **часто не помечены** словом «MIX» в названии — детектим по pattern «карточка получает ≥N разных supplier-имён», не по слову.

Mandatory selection поле `x_studio_mix_tier` (cheap / standard / premium).

### 3.6 Holded compras gap

Verdnatura импортирована **только Q1**. Остальные albaranes/facturas в Holded compras надо подтащить — задача блока A2.

### 3.7 Атрибуты — три поддомена

**Срезка:**
- род, сорт
- length cm (variant)
- color (variant or field)
- grade
- origin
- pack type
- treatment
- vase life

**Горшечка:**
- род, сорт
- pot_size cm (variant)
- plant_height cm
- light, water
- origin
- decor_pot_included

**MIX:**
- mandatory `x_studio_mix_tier` (cheap / standard / premium)

### 3.8 POS-категории — два слоя

База POS-tree = зеркало `product.category` (учётное дерево). Поверх — тематические псевдо-вкладки через `pos.category` m2m (`pos_categ_ids`).

**Скрывать тематические** вкладки когда не сезон (Christmas, 14 Feb, 8 March) — чтобы экран не захламлялся.

**Always-on dynamic** псевдо-категории:
- «текущая поставка» (last delivery flowers)
- «предыдущая поставка» (prev delivery)

### 3.9 Новые карты наследуют старый supplierinfo

При миграции v2.2 supplierinfo копируется из source с dedup по `(partner_id, product_code)`. Должно поддерживать post-migration коррекции типа «о, мы всегда кидали это на Tulipanes MIX по ошибке — давай отколем в свою карту».

### 3.10 Фотографии

- **Серверы поставщиков** — скачивать с структурой URL что owner предоставит. Serviflor иногда даёт несколько фото на товар.
- **Свои фото с приёмки** — уже лежат в `image_1920` старых карантинных карточек, переезжают вместе с миграцией.
- **Новые карты 2026-born** без supplier-фото — фотографируем при приёмке, кладём в `image_1920`.

### 3.11 Holded sales prices при миграции

- Старые карантинные: spot-check `list_price` Odoo vs Holded; если drift → re-pull из Holded.
- Новые карты — уже созданы с x3 placeholder, оставляем под price-review.

---

## 4. Three working rules (приняты в начале A1)

1. **Documentation over memory** — поведение Odoo 19 сверять с [docs.odoo.com/19.0](https://docs.odoo.com/19.0/) и community перед утверждением; не верить памяти про 17/18.
2. **Manual export over slow MCP** — просить owner'а экспортить CSV/XLSX через UI Odoo/Holded, а не дёргать MCP по записи. MCP — точечно.
3. **Sub-agents для тяжёлой работы** — bulk parsing возвращает агрегат, raw data остаётся в sub-agent'е.

---

## 5. Block A1 — что сделано, что осталось

### 5.1 Цель A1 (read-only audit)

Снимок «что у нас и чего не хватает» **до** дизайна нового дерева. Reads:
- **Odoo:** ~2152 quarantine cards (name/SKU/barcode/prices/photo/tags/x_studio_*), все `product.supplierinfo` на них, 188 pedido + lines, уже-мигрированные cards, related stock.picking/stock.move
- **Holded:** все Verdnatura albaranes 2026 (gap analysis vs Odoo), все Verdnatura facturas 2026 (которые с detail-line `documentLines` vs sum-only), current Holded sales prices (spot-check vs Odoo)

### 5.2 Deliverables A1 (запланированы — НЕ созданы в прошлой сессии)

- `kb/add/05_<date>_audit.md` — текстовый snapshot
- `pedido.files/migration/audit_<date>.xlsx` — рабочая таблица для design-pass A4

### 5.3 Что собрано (XLSX в sandbox прошлой сессии)

⚠️ Эти файлы лежат в `Application Support/.../local_d851b7d7-.../uploads/` прошлого чата — при переходе в новую сессию **скорее всего недоступны**. Owner потребуется re-upload или перенос в `pedido.files/migration/`.

| # | Файл | Что | Анализ в чате |
|---|---|---|---|
| 1 | `Product (product.template)-15.xlsx` | 2152 rows × 21 fields, template `chatgpt3` | A1.9 |
| 2 | `Supplier Pricelist (product.supplierinfo)-4.xlsx` | 1029 rows × 20 fields, template `chatgpt2` | A1.10 |
| 3 | `Product (product.template)-16.xlsx` | re-export +3 fields (`purchase_method`, `available_in_pos`, `pos_categ_ids`); 2 поля не добавили (`x_studio_migration_note`, `x_studio_migrate_now`) — потом через MCP | A1.13 |
| 4 | `Purchase Order (purchase.order).xlsx` | pedido headers — **bash отработал, ответ AUP-блокирован** | — |

### 5.4 Findings из уже-сделанного анализа

**5.4.1 product.template (2152 cards):**

| Карт | Категория |
|---|---|
| 675 | ⛔ Карантин Holded **(только корень, без подкатегории)** — сюрприз, нужна триажа |
| 470 | FLORES CORTADAS (Rosa Uniflora 190 + Flores Variadas 132 + Ramas/Palos 124 + Rosa Ramificada 22 + др.) |
| 330 | PLANTAS EN MACETAS (Follaje 222 + Flores 62 + Terraza 23 + Suculentas 21 + ...) |
| 263 | DECORACION Y ADORNOS |
| 91 | EMBALAJE / VBOX(CAJAS) |
| 68 | Consumibles |

**5.4.2 product.supplierinfo (1029 records):**

- VERDNATURA: 711 (3 без `product_code` — likely sub-agent errors, low priority)
- SERVIFLOR: 318, из них **109 без `x_studio_supplier_identity_key`** — большой gap, исправить в A3 заново-extract'ом из `pedido.files/serviflor-бухгатер-chatgpt/_final4/`

**5.4.3 purchase_method state — KB v3 stale:**

KB говорил `purchase` (On ordered) для cut+potted. **Реальность:** все 499 FLORES CORTADAS + все 379 PLANTAS EN MACETAS = `On received`. Где-то в wipe/import циклах сбросилось.

Recommendation для A7 (зафиксирована, ждёт owner OK для bulk-update):
- FLORES CORTADAS → `purchase` (~499)
- PLANTAS EN MACETAS → `purchase` (~379)
- DECORACION + EMBALAJE + Consumibles + EQUIPAMIENTO + ENTREGA → keep `receive`
- 675 root-only Карантин — триажа в A2/A4 первее

Rationale (политика owner'а): «±2-3 стебля не воюем, платим бумажную qty; серьёзные расхождения → бухгалтер правит bill вручную до Validate ИЛИ требуем credit note». Это значит `On ordered` proposal mode = ноль шума в 90% кейсов.

**5.4.4 Pedido headers gap:**

Owner экспорт пропустил: `state`, `amount_total`, `amount_untaxed`, `invoice_status`, `picking_count/picking_ids`, `invoice_count/invoice_ids`. Запросили re-export — owner залил последний файл, но reply на него был AUP-блокирован.

**5.4.5 Сюрприз — Serviflor pedido тоже есть в Odoo:**

KB v3 утверждал «все 188 pedido = Verdnatura», по факту — **Verdnatura + Serviflor**. Есть April Serviflor draft pedido — owner предложил убрать из экспорта, ассистент возразил («если это реальная апрельская закупка — нужна для A11»). Решение не принято.

---

## 6. Открытые вопросы owner'у (нужно для закрытия A1)

| # | Вопрос | Дефолт ассистента | Статус |
|---|---|---|---|
| **A1.6.1** | Рабочая таблица: Google Sheet vs XLSX в репо? | Sheet (для совместного design-pass со старшим флористом) | не отвечен |
| **A1.6.2** | Audit scope: cut+potted (~1000) или все 2152 включая твёрдый товар (одним проходом, два листа)? | All-at-once | не отвечен |
| **A1.6.3** | Какие CSV owner готов выгрузить руками | — | де-факто отвечен (4 файла залиты) |
| **A1.6.4** | Holded compras check внутри A1 или отдельно? | Внутри A1 | не отвечен |
| **A1.6.5** | Read-only confirmation | implicit OK («вручную я могу скачать экспорты») | implicit |
| **A1.14.6.1** | Confirm bulk-update `purchase_method` на cut+potted → `purchase` | да, согласие на recommendation | implicit OK, явного «жми» нет |
| **A1.14.6.2** | 675 root-only Карантин cards → defer на A2/A4 | да | implicit OK |
| **A1.15.4.1** | Re-export pedido headers с `state` + `amount_total` + ... | re-export | owner залил файл, ответ AUP-блокирован |
| **A1.15.4.2** | April Serviflor draft pedido: keep / drop / keep-with-flag | keep (нужно для A11 если реальная закупка) | не отвечен |

---

## 7. Resume notes для новой сессии

### 7.1 Что НЕ переобсуждать

Раздел 3 (locked decisions) и раздел 2 (14-block plan) — **зафиксировано**. Не задавать вопросов про 5 кодов, VAT-switch, MIX-tier, attributes design, POS-структуру. Если owner сам поднимает — обсуждать, но default = settled.

### 7.2 Что нужно от owner'а на старте

1. **Re-upload 4 XLSX** из прошлого sandbox ИЛИ перенос в `pedido.files/migration/` (предпочтительно, чтобы файлы пережили сессию)
2. **Ответы на 3 блокирующих вопроса:**
   - A1.6.1 — Sheet vs XLSX для рабочей таблицы
   - A1.6.2 — scope audit (~1000 vs 2152)
   - A1.15.4.2 — April Serviflor draft pedido (keep / drop)
3. **Re-export pedido headers** с пропущенными полями (см. 5.4.4)

### 7.3 Что делать после ответов

1. Завершить A1 — собрать `kb/add/05_<date>_audit.md` + working sheet (Google Sheet или XLSX в `pedido.files/migration/`)
2. Получить явное OK на bulk-update `purchase_method` (A1.14.6.1) — но НЕ катить до завершения A1
3. Перейти к A2 — Holded compras gap (Verdnatura не-Q1)

### 7.4 AUP-сбой в прошлой сессии

Тригернулся ложно на обычный русский текст «куда заглянуть?». Если повторится — переформулировать на английский / упростить русский, не эскалировать.

### 7.5 Ключевые пути в репо

- `pedido.files/serviflor-бухгатер-chatgpt/_final4/` — Serviflor source файлы для re-extract 109 missing identity keys (15 events Dec'25→May'26)
- `pedido.files/serviflor-бухгатер-chatgpt/__out/_done/` — 12 successful agent imports
- `pedido.files/verdnatura/` — только April 28 (4 файла) — KB про gap
- `pedido.files/reception_paper/` — ~178 Verdnatura paper PDF
- `kb/add/05_migrate_variant_v2.2.py` — verified migration toolkit

### 7.6 Где живут 5 кодов price-review

В Odoo prod ещё **не созданы** custom поля. Создание — задача блока A6 (когда начнём наполнять новые карты), не сейчас.
