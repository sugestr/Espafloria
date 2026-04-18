<!-- v: 1 | updated: 2026-04-18T15:55Z -->
# 00. Source Files Index

Карта всех **исходных файлов** проекта — откуда берётся информация в Master Context.

Полезно при:
- Переносе знаний в другой AI-чат — можно сказать «вот исходники, вот обработанный Master Context»
- Аудите: если что-то в MD кажется неверным — идём к исходнику
- Восстановлении: исходники + Master Context = полная реконструкция проекта

---

## 📁 Файлы в проекте Claude (`/mnt/project/` в container'e)

### `Integration_Telegram_Bot_blueprint__22_.json`

**Что:** Экспорт production Make.com scenario «Integration Telegram Bot» (55 модулей).
**Откуда:** Make.com UI → Scenario → Export Blueprint → `.json`
**Размер:** ~230 KB
**Состояние:** 🟢 **PROD** — это то, что реально работает.
**Переработано в:** [02_makecom_bot.md](02_makecom_bot.md) — архитектура, Router 110, 4 Route, JSON payloads, магические числа
**Когда обновлять:** после любого редакта scenario в Make.com UI
**Как обновлять:** re-export из Make.com → положить поверх старого

### `02_makecom_bot_brief.md`

**Что:** Промежуточный draft брифа по боту (до разбора blueprint).
**Откуда:** Подготовительные заметки до session с полным аудитом.
**Состояние:** ⚠️ **LEGACY** — частично устаревший, не является source of truth.
**Переработано в:** [02_makecom_bot.md](02_makecom_bot.md) (финальная версия с фактическими модулями и IDs)
**Нужен ли?** Можно удалить — содержимое поглощено. Держим на случай аудита истории решений.

### `prompt_3_распознаем_бумагу.txt`

**Что:** System prompt для OpenAI модуля 3 (OCR-экстрактор).
**Роль:** Первая LLM-стадия бота — парсит фото/PDF поставщицкого документа в STRICT JSON.
**Модель:** `gpt-5.4-mini`, T=0.2, max_tokens=4048
**Состояние:** 🟢 **PROD**
**Копия:** `prompts/prompt_ocr_v1.txt` (идентична)
**Переработано в:** [02_makecom_bot.md § OCR Extractor](02_makecom_bot.md#ocr-extractor-prompt-3)

### `prompt_149_Сравниваем_бумагу_с_pedido.txt`

**Что:** System prompt для модуля 149 — **Reconciliation engine v3.5**.
**Роль:** LLM-ядро бота — сопоставляет бумагу с существующим pedido, выбирает action (update_price / no_action / manual_review).
**Модель:** `gpt-5.4`, T=0, max_tokens=4500
**Состояние:** 🟢 **PROD**
**Копия:** `prompts/prompt_reconciliation_v3.5.txt`
**Переработано в:** [02_makecom_bot.md § Reconciliation Engine v3.5](02_makecom_bot.md#reconciliation-engine-v35-prompt-149)

### `prompt_167_что_подозрительного_.txt`

**Что:** System prompt для модуля 167 — **Diagnostics v3.1**.
**Роль:** Формирует короткий русскоязычный отчёт по pedido после всех апдейтов → в Telegram и в chatter.
**Модель:** `gpt-5.4-mini`, T=0.2, max_tokens=1200
**Состояние:** 🟢 **PROD**
**Копия:** `prompts/prompt_diagnostics_v3.1.txt`
**Переработано в:** [02_makecom_bot.md § Diagnostics v3.1](02_makecom_bot.md#diagnostics-v31-prompt-167)

---

## 📄 Внешние артефакты (не в Claude Project, но упоминаются)

### FLOR-gov — Odoo и испанский план счетов (PDF, 226 стр)

**Что:** Raw research-чат про испанский compliance — план счетов PGCE PYMEs 2008, Modelo 303/347/349, VeriFactu, SII.
**Состояние:** 📚 **REFERENCE** — не обработан целиком, читается точечно по запросу.
**Откуда брать:** был в upload'е одной из предыдущих сессий.
**Переработано частично в:** [07_infrastructure_devops.md § Испанский compliance](07_infrastructure_devops.md#испанский-compliance-будущее)
**Когда читать:** при настройке VeriFactu / SII / bank connectors / quarterly AEAT reports

### Регламент сотрудников (Google Doc, ~29 MB)

**Что:** Внутренний документ Espafloria — регламент работы флористов, продавцов, логиста, бухгалтера.
**Состояние:** 📕 **LEGACY** — построен на Holded архитектуре, требует переработки под Odoo.
**Ссылка:** [Google Doc](https://docs.google.com/document/d/1uKV4Acx1qDezUll7nkAfyrjdBt824WA_k4PsMLNA5K8/edit?usp=sharing)
**Проблема:** слишком большой, Google Drive не отдаёт export через API.
**Решение:** вручную вычитывать разделами, переносить в [05_florists_logistics_accountant.md](05_florists_logistics_accountant.md).
**Слот в Master Context:** раздел «Регламент» в `05_*.md` — плейсхолдер ждёт контента.

### Google Sheets: Holded-Odoo products

**Что:** ETL-справочник товаров из Holded в Odoo. Lookup по SKU, формулы tax mapping, category paths.
**URL:** https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE
**Состояние:** 🟢 **PROD** — использовался для основного импорта 1983 карточек.
**Переработано в:** [04_holded_migration.md § Google Sheets артефакты](04_holded_migration.md#google-sheets-артефакты) — формулы скопированы
**Когда обновлять:** при добавлении новых товаров / изменении tax mapping.

### Google Sheets: albaran-holded

**Что:** ETL для albaran → pedido. Lookup product.product External ID по SKU, tax mapping для строк заказа.
**URL:** https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58
**Состояние:** 🟢 **PROD**
**Переработано в:** [04_holded_migration.md § Purchase line import](04_holded_migration.md#purchase-line-import-для-albaran-pedido)
**Когда использовать:** при массовом импорте albaran за 2026 (запланировано на 21 апреля).

---

## 📸 Исходники, которых пока нет в файлах

### Скриншоты
- **Route 1 Make.com** — скриншот ветки «создать новый pedido», прислан в чате 18 апреля. 7 модулей: `Создать purchase [8] → Прикрепить фото [49] → Iterator [10] → Поиск карточки [94] → Добавить позицию [11] → Tools [82] → Final msg [52]`.
- **Screenshots Odoo UI** — различные экраны receipt review, ценники, pedido list view (в чате, без файлов).

### Записи из чатов (knowledge accumulated in conversation)
Многое из Master Context построено на обсуждении в чатах, без формального файла-источника:
- Обзор брифов reconciliation engine (эволюция v2.7 → v3.2.7 → v3.3 → v3.5)
- Диагностические бриф (evolution от v2 до v3.1)
- Production audit data (186 pedido, 1983 carantine products, 16 supplierinfo) — через MCP queries
- Business stories (14 user stories) — из переформулированного брифа
- Accountant workflow analysis — из обсуждения Holded habits
- Strategy launch decisions (2026-04-18) — принятые по ходу session

---

## 🗂️ Как пользоваться этим индексом

### При переносе в новый AI-чат
```
1. Загрузить эту папку master-context/
2. Дополнительно: ссылку на 00_source_files_index.md
3. Попросить новый AI прочесть 00_master_index.md → 99_invariants.md → 08_current_state_snapshot.md
4. Если нужны детали по боту — загрузить Integration_Telegram_Bot_blueprint__22_.json
5. Если нужен compliance — загрузить 226-стр PDF
```

### При восстановлении после сбоя
Приоритет:
1. Master Context (эта папка) — 95% информации
2. Blueprint Make.com — production truth для бота
3. Odoo Database — production truth для структуры
4. Исходные текстовые prompts — production truth для LLM

Всё остальное (устаревший бриф, регламент на Holded, Google Sheets с формулами) — **reference**, восстановимо из Master Context.

---

## Что хранить vs выбросить

| Файл | Действие | Почему |
|---|---|---|
| `Integration_Telegram_Bot_blueprint__22_.json` | 🟢 Хранить | Production truth, обновляется при правках scenario |
| `prompt_*.txt` (3 шт) | 🟢 Хранить | Production prompts, копии также в `prompts/` |
| `02_makecom_bot_brief.md` | 🟡 Можно удалить | Устаревший draft, поглощён в 02_makecom_bot.md |
| FLOR-gov PDF | 🟢 Хранить | Reference для compliance, читается точечно |
| Регламент Google Doc | 🟢 Хранить | Исторический документ + основа для переработки |
| Google Sheets (2 шт) | 🟢 Хранить | Living ETL tools, используются при импорте |
