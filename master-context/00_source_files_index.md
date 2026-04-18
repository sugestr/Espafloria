<!-- v: 5 | updated: 2026-04-18T23:00Z -->
# 00. Source Files Index

Карта **исходных файлов** проекта — откуда берётся информация в Master Context.

Полезно при:
- Переносе знаний в другой AI-чат
- Аудите: если в MD кажется неверным — идём к исходнику
- Восстановлении: исходники + Master Context = полная реконструкция проекта

---

## 📁 Артефакты в репо (живут в `master-context/` вместе с .md)

Плоский layout: всё на одном уровне с `.md`-файлами базы знаний, одна подпапка для старых скриптов.

### OpenAI system prompts для бота

| Файл | Назначение | Модуль в Make.com |
|---|---|---|
| `prompt_ocr_v1.txt` | OCR extractor — парсит фото/PDF бумаги поставщика в STRICT JSON | 3 (`gpt-5.4-mini`, T=0.2, max_tokens=4048) |
| `prompt_reconciliation_v3.5.txt` | Reconciliation engine — сопоставляет бумагу с pedido, выбирает action | 149 (`gpt-5.4`, T=0, max_tokens=4500) |
| `prompt_diagnostics_v3.1.txt` | Diagnostics — формирует русский отчёт в Telegram + chatter | 167 (`gpt-5.4-mini`, T=0.2, max_tokens=1200) |

**Source of truth:** Production Make.com scenario. Копии в репо — снапшот для diff'а между версиями и для inline-ссылки из чатов. При изменении промпта в Make — обновить и снапшот.

Переработано в [02_makecom_bot.md § OCR / Reconciliation / Diagnostics](02_makecom_bot.md).

### Make.com line-log шаблоны

- `make_line_log_pack.txt` — пачечная ветка
- `make_line_log_unit.txt` — штучная ветка

Переработаны в [02_makecom_bot.md § Templates](02_makecom_bot.md).

### Odoo server actions (живой prod-код)

| Файл | id | Что делает |
|---|---|---|
| `calculate_in_shop_action.py` | 1150 | Кнопка «Посчитать в магазине» на stock.picking |
| `migrate_variant_action.py` | 1145 | Миграция карантинной карточки в новый variant (с patch supplierinfo) |
| `review_status_automation.py` | 1146 | Review-status automation на stock.move |

**Source of truth:** Odoo production (доступ через Odoo MCP). Копии в репо — снапшот для review/diff.

### Worker tooling

- `commit_worker_delivery.sh` — стандартный коммит-скрипт worker'а. В Project knowledge не грузится (Claude не нужен). Используется через terminal. См. [12_ai_workflow.md](12_ai_workflow.md).

### `legacy_migrations/` — одноразовые Holded-миграции

| Файл | Что делает |
|---|---|
| `image_import_from_holded_api.py` | Импорт изображений из Holded API |
| `image_import_from_urls.py` | Импорт по списку URL |
| `split_big_csv.py` | Сплит больших CSV для chunk'ованного импорта |

Переработано в [04_holded_migration.md](04_holded_migration.md). В Project knowledge не грузятся (не нужны в оперативе). Достаём локально по запросу:
```
cat ~/Documents/master-context/master-context/legacy_migrations/<file>.py
```

---

## 📄 Не в репо, доступ через MCP / внешние ссылки

### Make.com blueprint (Integration Telegram Bot)

**Где живёт:** только в Make.com (prod scenario).
**Как достать:** через Make MCP (`mcp:make`) — `scenarios_get` или `scenarios_interface`.
**Когда нужно:** обычно не нужно — ключевые фрагменты переработаны в [02_makecom_bot.md](02_makecom_bot.md). Достаём если надо посмотреть точный JSON mapper'а или edge case.

### FLOR-gov — Odoo и испанский план счетов (PDF, 226 стр)

**Что:** Raw research про испанский compliance — план счетов PGCE PYMEs 2008, Modelo 303/347/349, VeriFactu, SII.
**Где:** external upload по запросу.
**Переработано частично в:** [07_infrastructure_devops.md § Испанский compliance](07_infrastructure_devops.md#испанский-compliance-будущее).
**Когда читать:** при настройке VeriFactu / SII / bank connectors / AEAT.

### Регламент сотрудников (Google Doc, ~29 MB)

**Что:** Внутренний регламент флористов / продавцов / логиста / бухгалтера.
**Статус:** 📕 LEGACY (Holded-based), ждёт переработки под Odoo.
**Ссылка:** [Google Doc](https://docs.google.com/document/d/1uKV4Acx1qDezUll7nkAfyrjdBt824WA_k4PsMLNA5K8/edit?usp=sharing).
**Слот:** раздел «Регламент» в [05_florists_logistics_accountant.md](05_florists_logistics_accountant.md) — плейсхолдер.

### Google Sheets: Holded-Odoo products

**URL:** https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE
**Что:** ETL-справочник товаров Holded→Odoo. Переработано в [04_holded_migration.md § Google Sheets артефакты](04_holded_migration.md#google-sheets-артефакты).

### Google Sheets: albaran-holded

**URL:** https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58
**Что:** ETL для albaran→pedido. Переработано в [04_holded_migration.md § Purchase line import](04_holded_migration.md#purchase-line-import-albaran--pedido).

---

## 🗂️ При восстановлении после сбоя

Приоритет:
1. Master Context (эта папка) — 95% информации
2. Make.com prod scenario (через Make MCP) — truth для бота
3. Odoo database (через Odoo MCP) — truth для структуры
4. Prompts / server actions в репо — снапшоты, sync'имые с prod

Остальное — reference, восстановимо из Master Context.

---

## Что хранить где

| Артефакт | Хранение | Почему |
|---|---|---|
| `prompt_*.txt` | git + Project knowledge | Мелкие, часто обсуждаются |
| `make_line_log_*.txt` | git + Project knowledge | Мелкие, нужны при обсуждении бота |
| `*_action.py` / `*_automation.py` (Odoo actions) | git + Project knowledge | Живой prod-код, обсуждается часто |
| `legacy_migrations/*.py` | только git | Одноразовые, Project не засорять |
| `commit_worker_delivery.sh` | только git | Тулинг, Claude не нужно |
| Make blueprint JSON | только Make (через MCP) | ~230 KB, дубликат бесполезен |
| FLOR-gov PDF | внешний upload по запросу | Reference, 226 стр |
| Google Docs / Sheets | Google Drive | Living docs |
