<!-- v: 9 | updated: 2026-04-18T23:30Z -->
# VERSIONS

Индекс версий всех `.md` в базе. **`v` в header этого файла — маркер синка всей базы** (см. [SYNC_STATE.md](SYNC_STATE.md)).

Все `.md` и почти все артефакты живут в `master-context/` на одном уровне. Только `legacy_migrations/` — в подпапке. В корне репо — короткий stub `README.md` (только для GitHub-лендинга, в Project не грузится, не версионируется).

---

## Файлы .md

| Файл | v | Updated (UTC) |
|---|---|---|
| `README.md` | 6 | 2026-04-18T23:30Z |
| `VERSIONS.md` | 9 | 2026-04-18T23:30Z |
| `SYNC_STATE.md` | 8 | 2026-04-18T23:30Z |
| `CHANGELOG.md` | 10 | 2026-04-18T23:30Z |
| `00_master_index.md` | 8 | 2026-04-18T23:00Z |
| `00_source_files_index.md` | 5 | 2026-04-18T23:00Z |
| `01_business_context.md` | 2 | 2026-04-18T20:00Z |
| `02_makecom_bot.md` | 3 | 2026-04-18T20:00Z |
| `03_odoo_receipt_review.md` | 1 | 2026-04-18T15:45Z |
| `04_holded_migration.md` | 2 | 2026-04-18T20:00Z |
| `05_florists_logistics_accountant.md` | 2 | 2026-04-18T16:30Z |
| `06_catalog_migration_toolkit.md` | 1 | 2026-04-18T15:45Z |
| `07_infrastructure_devops.md` | 2 | 2026-04-18T20:00Z |
| `08_current_state_snapshot.md` | 2 | 2026-04-18T20:00Z |
| `09_open_work.md` | 3 | 2026-04-18T20:00Z |
| `10_vision_and_roadmap.md` | 3 | 2026-04-18T20:00Z |
| `11_crm_and_customers.md` | 1 | 2026-04-18T16:35Z |
| `12_ai_workflow.md` | 7 | 2026-04-18T23:30Z |
| `99_invariants.md` | 2 | 2026-04-18T16:45Z |

---

## Артефакты (в `master-context/` на одном уровне с .md, не версионируются через `v`)

**Грузятся в Project knowledge** вместе со всеми .md (одним drag-drop):

- `calculate_in_shop_action.py` — Odoo server action id=1150
- `migrate_variant_action.py` — Odoo server action id=1145 (c patch supplierinfo)
- `review_status_automation.py` — Odoo server action id=1146
- `prompt_ocr_v1.txt` — OpenAI OCR prompt (модуль 3)
- `prompt_reconciliation_v3.5.txt` — OpenAI reconciliation engine (модуль 149)
- `prompt_diagnostics_v3.1.txt` — OpenAI diagnostics (модуль 167)
- `make_line_log_pack.txt` — Make.com template (пачечная ветка)
- `make_line_log_unit.txt` — Make.com template (штучная ветка)

**Не грузятся в Project knowledge:**

- `commit_worker_delivery.sh` — коммит-скрипт worker'а (тулинг, Claude не нужен)
- `legacy_migrations/` — одноразовые Holded-миграции; читать локально при необходимости
- stub `README.md` в корне репо — только GitHub-лендинг
- Make.com blueprint — не храним в репо вообще, достаём через Make MCP

---

## Правила bump'а `v`

При правке любого `.md`:
1. `v` и `updated` в header файла → обновить
2. Строку файла в этой таблице → обновить
3. `v` и `updated` у **самого** `VERSIONS.md` → обновить

**Что бампаем:** новая информация, перестройка раздела, изменение факта. **Что нет:** опечатки / чистая пунктуация (только `updated`).
