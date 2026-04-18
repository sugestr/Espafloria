<!-- v: 3 | updated: 2026-04-18T19:10Z -->
# VERSIONS

Индекс версий всех файлов Master Context. Обновляется **одновременно** с header'ом в самом файле.

Формат: `file | v | updated (UTC)`

---

## Файлы Master Context

| Файл | v | Updated (UTC) | Описание |
|---|---|---|---|
| `README.md` | 1 | 2026-04-18T17:05Z | Правила репо для GitHub |
| `VERSIONS.md` | 3 | 2026-04-18T19:10Z | Этот файл |
| `SYNC_STATE.md` | 2 | 2026-04-18T19:10Z | Состояние синхронизации Project↔GitHub |
| `00_master_index.md` | 4 | 2026-04-18T18:10Z | Навигация + глоссарий |
| `00_source_files_index.md` | 1 | 2026-04-18T15:55Z | Карта исходников |
| `01_business_context.md` | 1 | 2026-04-18T15:45Z | Бизнес, user stories, принципы |
| `02_makecom_bot.md` | 2 | 2026-04-18T16:40Z | Telegram-бот (+Platform Dependencies) |
| `03_odoo_receipt_review.md` | 1 | 2026-04-18T15:45Z | Приёмка (stock.move, review-status) |
| `04_holded_migration.md` | 1 | 2026-04-18T15:45Z | Импорт из Holded |
| `05_florists_logistics_accountant.md` | 2 | 2026-04-18T16:30Z | Роли: флорист, логист, бухгалтер + salary |
| `06_catalog_migration_toolkit.md` | 1 | 2026-04-18T15:45Z | Migration action + SOP |
| `07_infrastructure_devops.md` | 1 | 2026-04-18T15:45Z | Odoo.sh, compliance |
| `08_current_state_snapshot.md` | 1 | 2026-04-18T15:45Z | Фото базы после hot-fix |
| `09_open_work.md` | 2 | 2026-04-18T16:50Z | TODO приоритизированный |
| `10_vision_and_roadmap.md` | 2 | 2026-04-18T16:55Z | Видение + 15 шагов |
| `11_crm_and_customers.md` | 1 | 2026-04-18T16:35Z | CRM scope |
| `12_ai_workflow.md` | 1 | 2026-04-18T18:00Z | Multi-chat архитектура + briefings |
| `99_invariants.md` | 2 | 2026-04-18T16:45Z | 37 железных правил |
| `CHANGELOG.md` | 4 | 2026-04-18T18:15Z | Журнал изменений |

## Артефакты (не версионируются в VERSIONS.md)

Файлы в `code/`, `prompts/`, `templates/` — **production-код и prompts**. Обновляются синхронно с production-системами (Odoo / Make.com / OpenAI), отслеживаются через commit history, не через version headers.

- `code/review_status_automation.py` — server action id=1146
- `code/migrate_variant_action.py` — server action id=1145 (с patch supplierinfo 2026-04-18)
- `code/calculate_in_shop_action.py` — server action id=1150
- `code/image_import_from_urls.py` — Python script
- `code/image_import_from_holded_api.py` — Python script
- `code/split_big_csv.py` — Python script
- `prompts/prompt_ocr_v1.txt` — OCR extractor prompt (prod)
- `prompts/prompt_reconciliation_v3.5.txt` — Reconciliation engine (prod)
- `prompts/prompt_diagnostics_v3.1.txt` — Diagnostics (prod)
- `templates/make_line_log_pack.txt` — Pack branch template
- `templates/make_line_log_unit.txt` — Unit branch template

---

## Протокол обновления

При правке любого `.md` файла:

1. Изменить `v` (обычно +1) и `updated` в header'е файла
2. Обновить соответствующую строку в этой таблице
3. Сделать коммит с сообщением вида `file.md v2: краткое описание изменения`
4. Напомнить пользователю перезалить в Claude Project knowledge

**Правила бампа версии:**
- Минорные добавления / новые разделы → `v+1`
- Крупные переструктуризации → `v+5` или округление
- Опечатки и формулировки → не менять `v`, только `updated`

См. также: [README.md](README.md)
