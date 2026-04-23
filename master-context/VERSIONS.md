<!-- v: 16 | updated: 2026-04-23T01:30Z -->
# VERSIONS

Индекс версий всех `.md` в базе. **`v` в header этого файла — маркер синка всей базы** (см. [SYNC_STATE.md](SYNC_STATE.md)).

Все `.md` и почти все артефакты живут в `master-context/` на одном уровне. Только `legacy_migrations/` — в подпапке. В корне репо — короткий stub `README.md` (только для GitHub-лендинга, в Project не грузится, не версионируется).

---

## Файлы .md

| Файл | v | Updated (UTC) |
|---|---|---|
| `README.md` | 8 | 2026-04-19T22:15Z |
| `VERSIONS.md` | 16 | 2026-04-23T01:30Z |
| `SYNC_STATE.md` | 10 | 2026-04-19T22:15Z |
| `CHANGELOG.md` | 16 | 2026-04-23T01:30Z |
| `00_master_index.md` | 11 | 2026-04-19T23:45Z |
| `00_source_files_index.md` | 6 | 2026-04-19T12:30Z |
| `01_business_context.md` | 4 | 2026-04-23T01:20Z |
| `02_makecom_bot.md` | 6 | 2026-04-19T23:30Z |
| `03_odoo_receipt_review.md` | 2 | 2026-04-19T15:00Z |
| `04_holded_migration.md` | 3 | 2026-04-19T15:00Z |
| `05_florists_logistics_accountant.md` | 4 | 2026-04-23T01:20Z |
| `06_catalog_migration_toolkit.md` | 4 | 2026-04-19T23:45Z |
| `07_infrastructure_devops.md` | 3 | 2026-04-19T15:00Z |
| `08_current_state_snapshot.md` | 7 | 2026-04-23T01:30Z |
| `09_open_work.md` | 7 | 2026-04-23T01:30Z |
| `10_vision_and_roadmap.md` | 4 | 2026-04-19T15:00Z |
| `11_crm_and_customers.md` | 1 | 2026-04-18T16:35Z |
| `12_ai_workflow.md` | 9 | 2026-04-19T22:15Z |
| `99_invariants.md` | 6 | 2026-04-23T01:30Z |

---

## Артефакты (в `master-context/` на одном уровне с .md, не версионируются через `v`)

**Грузятся в Project knowledge** вместе со всеми .md (одним drag-drop):

- `calculate_in_shop_action.py` — Odoo server action id=1150
- `migrate_variant_action.py` — Odoo server action id=1145 (UI trigger v2, короткий wrapper)
- `migrate_variant_v2.2.py` — Odoo server action id=1176 (execute v2.2, вся логика миграции)
- `review_status_automation.py` — Odoo server action id=1146
- `bouquet_on_payment_action.py` — Odoo server action id=1203 (POS→SO bouquet assemble + dismantle)
- `bouquet_on_picking_action.py` — Odoo server action id=1205 (stock.picking reverse for dismantle)
- `bouquet_on_order_paid_action.py` — Odoo server action id=1207 (pos.order paid safety net)
- `prompt_ocr_v1.txt` — OpenAI OCR prompt (модуль 3)
- `prompt_reconciliation_v3.5.txt` — OpenAI reconciliation engine (модуль 149)
- `prompt_diagnostics_v3.1.txt` — OpenAI diagnostics (модуль 167)
- `make_line_log_pack.txt` — Make.com template (пачечная ветка)
- `make_line_log_unit.txt` — Make.com template (штучная ветка)
- `commit_worker_delivery.sh` — коммит-скрипт worker'а (Claude им не пользуется, ~3 KB в drag-drop не мешают)

Note: в Project knowledge точки заменяются на `_` (`prompt_reconciliation_v3.5.txt` в репо → `prompt_reconciliation_v3_5.txt` в Project). См. [`02_makecom_bot.md § Промпты`](02_makecom_bot.md).

**Не грузятся в Project knowledge:**

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
