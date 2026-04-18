<!-- v: 6 | updated: 2026-04-18T22:00Z -->
# VERSIONS

Индекс версий всех `.md` в базе. **`v` в header этого файла — маркер синка всей базы** (см. [SYNC_STATE.md](SYNC_STATE.md)).

Все файлы ниже живут в `master-context/` (flat layout). `README.md` — в корне репо.

---

## Файлы

| Файл | v | Updated (UTC) |
|---|---|---|
| `README.md` *(repo root)* | 3 | 2026-04-18T21:00Z |
| `VERSIONS.md` | 6 | 2026-04-18T22:00Z |
| `SYNC_STATE.md` | 5 | 2026-04-18T22:00Z |
| `CHANGELOG.md` | 7 | 2026-04-18T22:00Z |
| `00_master_index.md` | 6 | 2026-04-18T21:00Z |
| `00_source_files_index.md` | 3 | 2026-04-18T21:00Z |
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
| `12_ai_workflow.md` | 4 | 2026-04-18T22:00Z |
| `99_invariants.md` | 2 | 2026-04-18T16:45Z |

---

## Артефакты

Живут в `master-context/artifacts/` и в Project knowledge **не загружаются** — worker читает локально через `cat ~/Documents/master-context/master-context/artifacts/...`. Обновляются синхронно с prod-системами, отслеживаются через git history, не через `v`.

- `artifacts/code/` — Python + Odoo server actions
- `artifacts/prompts/` — OpenAI system prompts (OCR, reconciliation, diagnostics)
- `artifacts/templates/` — Make.com line-log шаблоны
- `artifacts/makecom/Integration_Telegram_Bot_blueprint.json` — экспорт production Make scenario (~230 KB)
- `artifacts/scripts/commit_worker_delivery.sh` — стандартный коммит-скрипт worker'а

---

## Правила bump'а `v`

При правке любого `.md`:
1. `v` и `updated` в header файла → обновить
2. Строку файла в этой таблице → обновить
3. `v` и `updated` у **самого** `VERSIONS.md` → обновить

**Что бампаем:** новая информация, перестройка раздела, изменение факта. **Что нет:** опечатки / чистая пунктуация (только `updated`, без изменения `v`).
