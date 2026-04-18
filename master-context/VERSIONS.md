<!-- v: 7 | updated: 2026-04-18T22:30Z -->
# VERSIONS

Индекс версий всех `.md` в базе. **`v` в header этого файла — маркер синка всей базы** (см. [SYNC_STATE.md](SYNC_STATE.md)).

Все файлы ниже живут в `master-context/` (flat layout). `README.md` — в корне репо.

---

## Файлы

| Файл | v | Updated (UTC) |
|---|---|---|
| `README.md` *(repo root)* | 4 | 2026-04-18T22:30Z |
| `VERSIONS.md` | 7 | 2026-04-18T22:30Z |
| `SYNC_STATE.md` | 6 | 2026-04-18T22:30Z |
| `CHANGELOG.md` | 8 | 2026-04-18T22:30Z |
| `00_master_index.md` | 7 | 2026-04-18T22:30Z |
| `00_source_files_index.md` | 4 | 2026-04-18T22:30Z |
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
| `12_ai_workflow.md` | 5 | 2026-04-18T22:30Z |
| `99_invariants.md` | 2 | 2026-04-18T16:45Z |

---

## Артефакты

Живут в `master-context/artifacts/`. Не версионируются через `v` — отслеживаются через git history.

**Грузятся в Project knowledge (нужны для обсуждения бизнеса):**
- `artifacts/prompts/` — OpenAI system prompts (`prompt_ocr_v1.txt`, `prompt_reconciliation_v3.5.txt`, `prompt_diagnostics_v3.1.txt`)
- `artifacts/templates/` — Make.com line-log шаблоны (`make_line_log_pack.txt`, `make_line_log_unit.txt`)
- `artifacts/code/odoo_actions/` — живые Odoo server actions:
  - `calculate_in_shop_action.py` (id=1150)
  - `migrate_variant_action.py` (id=1145, с patch supplierinfo)
  - `review_status_automation.py` (id=1146)

**Только в git (по запросу, в Project не грузятся):**
- `artifacts/code/migrations/` — одноразовые Holded-миграции (`image_import_from_holded_api.py`, `image_import_from_urls.py`, `split_big_csv.py`)
- `artifacts/scripts/commit_worker_delivery.sh` — стандартный коммит-скрипт worker'а
- `artifacts/makecom/` — резерв для blueprint JSON (~230 KB, в Project не грузится даже если появится; достаём через Make MCP)

---

## Правила bump'а `v`

При правке любого `.md`:
1. `v` и `updated` в header файла → обновить
2. Строку файла в этой таблице → обновить
3. `v` и `updated` у **самого** `VERSIONS.md` → обновить

**Что бампаем:** новая информация, перестройка раздела, изменение факта. **Что нет:** опечатки / чистая пунктуация (только `updated`, без изменения `v`).
