<!-- v: 4 | updated: 2026-04-18T20:00Z -->
# VERSIONS

Сводный индекс версий всех файлов Master Context.

Версия самого `VERSIONS.md` (в header'е выше) — **маркер состояния всей базы
для version-based sync**. Если у тебя в Project Knowledge `v` здесь меньше,
чем на GitHub, — база устарела. См. [SYNC_STATE.md](SYNC_STATE.md).

Формат: `file | v | updated (UTC) | описание`.

---

## Файлы Master Context

| Файл | v | Updated (UTC) | Описание |
|---|---|---|---|
| `README.md` | 2 | 2026-04-18T20:00Z | Правила репо для GitHub, sync mention |
| `VERSIONS.md` | 4 | 2026-04-18T20:00Z | Этот файл (sync маркер) |
| `SYNC_STATE.md` | 3 | 2026-04-18T20:00Z | Version-based sync протокол |
| `00_master_index.md` | 5 | 2026-04-18T20:00Z | Навигация + глоссарий (+sync термины) |
| `00_source_files_index.md` | 2 | 2026-04-18T20:00Z | Карта исходников (prompts — реальные имена) |
| `01_business_context.md` | 2 | 2026-04-18T20:00Z | Бизнес (+cross-ref warehouse_id=2 к 05, 08) |
| `02_makecom_bot.md` | 3 | 2026-04-18T20:00Z | Telegram-бот (+переформулирован SoT для prompts) |
| `03_odoo_receipt_review.md` | 1 | 2026-04-18T15:45Z | Приёмка (stock.move, review-status) |
| `04_holded_migration.md` | 2 | 2026-04-18T20:00Z | Импорт из Holded (убрана стрелка в заголовке) |
| `05_florists_logistics_accountant.md` | 2 | 2026-04-18T16:30Z | Роли: флорист, логист, бухгалтер + salary |
| `06_catalog_migration_toolkit.md` | 1 | 2026-04-18T15:45Z | Migration action + SOP |
| `07_infrastructure_devops.md` | 2 | 2026-04-18T20:00Z | Odoo.sh + MCP list (+GitHub, +Odoo) |
| `08_current_state_snapshot.md` | 2 | 2026-04-18T20:00Z | Фото базы (фикс счётов полей) |
| `09_open_work.md` | 3 | 2026-04-18T20:00Z | TODO (P3/P4 переструктурированы в подразделы) |
| `10_vision_and_roadmap.md` | 3 | 2026-04-18T20:00Z | Видение + 15 шагов (+11.5 в roadmap таблице) |
| `11_crm_and_customers.md` | 1 | 2026-04-18T16:35Z | CRM scope |
| `12_ai_workflow.md` | 2 | 2026-04-18T20:00Z | Multi-chat + version-based sync protocol |
| `99_invariants.md` | 2 | 2026-04-18T16:45Z | 37 железных правил |
| `CHANGELOG.md` | 5 | 2026-04-18T20:00Z | Журнал изменений (+Base Polish session) |

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

При правке любого `.md` файла (кроме артефактов):

1. Изменить `v` и `updated` в header'е файла.
2. Обновить соответствующую строку в этой таблице.
3. **Всегда** bump `v` + `updated` у самого `VERSIONS.md` в header выше.
4. Коммит одним пушем в GitHub.
5. В финальном сообщении Owner'у — «VERSIONS.md: v`<old>` → v`<new>`, изменённые файлы: ..., перезалей в Project knowledge».

**Правила бампа версии:**
- Минорные добавления / новые разделы → `v+1`
- Крупные переструктуризации → `v+5` или округление
- Опечатки и чистая пунктуация → только `updated`, `v` не трогать, в эту таблицу не писать

См. [README.md](README.md), [SYNC_STATE.md](SYNC_STATE.md).
