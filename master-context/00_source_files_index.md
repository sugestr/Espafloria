<!-- v: 4 | updated: 2026-04-18T22:30Z -->
# 00. Source Files Index

Карта всех **исходных файлов** проекта — откуда берётся информация в Master Context.

Полезно при:
- Переносе знаний в другой AI-чат — можно сказать «вот исходники, вот обработанный Master Context»
- Аудите: если что-то в MD кажется неверным — идём к исходнику
- Восстановлении: исходники + Master Context = полная реконструкция проекта

---

## 📁 Артефакты в репо — что где лежит и что грузится в Project

Разделены на **три группы** по частоте использования.

### Группа 1 — грузим в Project knowledge (оперативный доступ)

#### `artifacts/prompts/` — OpenAI system prompts для бота

| Файл | Назначение | Модуль в Make.com |
|---|---|---|
| `prompt_ocr_v1.txt` | OCR extractor — парсит фото/PDF бумаги поставщика в STRICT JSON | модуль 3 (`gpt-5.4-mini`, T=0.2, max_tokens=4048) |
| `prompt_reconciliation_v3.5.txt` | Reconciliation engine — сопоставляет бумагу с pedido, выбирает action | модуль 149 (`gpt-5.4`, T=0, max_tokens=4500) |
| `prompt_diagnostics_v3.1.txt` | Diagnostics — формирует русский отчёт по pedido в Telegram + chatter | модуль 167 (`gpt-5.4-mini`, T=0.2, max_tokens=1200) |

**Source of truth:** Production Make.com scenario. Копии в `artifacts/prompts/` — снапшот для diff'а между версиями и для ссылки из Project knowledge. При изменении промпта в Make — обновить и снапшот в репо.

Переработано в [02_makecom_bot.md § OCR / Reconciliation / Diagnostics](02_makecom_bot.md).

#### `artifacts/templates/` — Make.com line-log шаблоны

- `make_line_log_pack.txt` — пачечная ветка
- `make_line_log_unit.txt` — штучная ветка

Переработаны в [02_makecom_bot.md § Templates](02_makecom_bot.md).

#### `artifacts/code/odoo_actions/` — живые Odoo server actions

- `calculate_in_shop_action.py` — server action id=1150, кнопка «Посчитать в магазине» (stock.picking)
- `migrate_variant_action.py` — server action id=1145, миграция карантинных карточек в variants (с patch supplierinfo от 2026-04-18)
- `review_status_automation.py` — server action id=1146, review-status automation (stock.move)

**Source of truth:** Odoo production (accessible via Odoo MCP). Копии в репо — снапшот для review и diff'а.

### Группа 2 — только в git (по запросу, не в Project)

#### `artifacts/code/migrations/` — одноразовые Holded-миграции

- `image_import_from_holded_api.py` — импорт изображений из Holded API
- `image_import_from_urls.py` — импорт по списку URL
- `split_big_csv.py` — сплит больших CSV для chunk'ованного импорта

Переработано в [04_holded_migration.md](04_holded_migration.md). Для новой работы скорее всего не нужны — если понадобится, worker читает локально:
```
cat ~/Documents/master-context/master-context/artifacts/code/migrations/<file>.py
```

#### `artifacts/scripts/commit_worker_delivery.sh`

Стандартный коммит-скрипт worker'а. См. [12_ai_workflow.md § Три стадии работы](12_ai_workflow.md).

#### `artifacts/makecom/` — резерв для Make.com blueprint

На данный момент пусто. Если появится `Integration_Telegram_Bot_blueprint.json` — он ~230 KB и **в Project knowledge не грузится** (достаём live через Make MCP при необходимости).

### Группа 3 — не в git вообще

#### Make.com blueprint (Integration Telegram Bot)

**Где живёт:** только в Make.com (prod scenario).
**Как достать:** через Make MCP (`mcp:make`) — `scenarios_get` или `scenarios_interface`.
**Зачем нужно:** обычно не нужно — все ключевые фрагменты уже переработаны в [02_makecom_bot.md](02_makecom_bot.md). Достаём если надо посмотреть точный JSON mapper'а, module option, или разобраться в edge case.

---

## 📄 Внешние артефакты (не в репо, не в Project, упоминаются)

### FLOR-gov — Odoo и испанский план счетов (PDF, 226 стр)

**Что:** Raw research-чат про испанский compliance — план счетов PGCE PYMEs 2008, Modelo 303/347/349, VeriFactu, SII.
**Состояние:** 📚 **REFERENCE** — не обработан целиком, читается точечно.
**Переработано частично в:** [07_infrastructure_devops.md § Испанский compliance](07_infrastructure_devops.md#испанский-compliance-будущее)
**Когда читать:** при настройке VeriFactu / SII / bank connectors / AEAT.

### Регламент сотрудников (Google Doc, ~29 MB)

**Что:** Внутренний документ Espafloria — регламент работы флористов, продавцов, логиста, бухгалтера.
**Состояние:** 📕 **LEGACY** (Holded-based).
**Ссылка:** [Google Doc](https://docs.google.com/document/d/1uKV4Acx1qDezUll7nkAfyrjdBt824WA_k4PsMLNA5K8/edit?usp=sharing)
**Слот:** раздел «Регламент» в [05_florists_logistics_accountant.md](05_florists_logistics_accountant.md) — плейсхолдер ждёт контента.

### Google Sheets: Holded-Odoo products

**Что:** ETL-справочник товаров Holded→Odoo (SKU lookup, tax mapping, category paths).
**URL:** https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE
**Состояние:** 🟢 **PROD**. Переработано в [04_holded_migration.md § Google Sheets артефакты](04_holded_migration.md#google-sheets-артефакты).

### Google Sheets: albaran-holded

**Что:** ETL для albaran→pedido.
**URL:** https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58
**Состояние:** 🟢 **PROD**. Переработано в [04_holded_migration.md § Purchase line import](04_holded_migration.md#purchase-line-import-albaran--pedido).

---

## 📸 Исходники, которых нет в файлах

### Скриншоты
- **Route 1 Make.com** — скриншот из чата 18 апр, 7 модулей: `Создать purchase [8] → Прикрепить фото [49] → Iterator [10] → Поиск карточки [94] → Добавить позицию [11] → Tools [82] → Final msg [52]`
- **Screenshots Odoo UI** — разные экраны (в чатах, без файлов)

### Записи из чатов
- Эволюция reconciliation brief (v2.7 → v3.5)
- Эволюция diagnostics brief (v2 → v3.1)
- Production audit data — через MCP queries
- Business stories (14 user stories)
- Launch decisions (2026-04-18)

---

## 🗂️ При восстановлении после сбоя

Приоритет:
1. Master Context (эта папка) — 95% информации
2. Make.com prod scenario (через Make MCP) — production truth для бота
3. Odoo database (через Odoo MCP) — production truth для структуры
4. `artifacts/prompts/` — snapshot production prompts (sync'ился с Make)

Всё остальное — reference, восстановимо из Master Context.

---

## Что хранить где

| Артефакт | Хранение | Почему |
|---|---|---|
| `artifacts/prompts/*.txt` | git + Project knowledge | Мелкие, часто обсуждаются |
| `artifacts/templates/*.txt` | git + Project knowledge | Мелкие, нужны при обсуждении бота |
| `artifacts/code/odoo_actions/*.py` | git + Project knowledge | Живой prod-код, обсуждается часто |
| `artifacts/code/migrations/*.py` | только git | Одноразовые, Project не засорять |
| `artifacts/scripts/*.sh` | только git | Служебное, Claude не нужно |
| Make blueprint | только Make (через MCP) | ~230 KB, не имеет смысла дублировать |
| FLOR-gov PDF | внешний upload по запросу | Reference, 226 стр, точечный просмотр |
| Google Docs / Sheets | Google Drive | Living docs |
