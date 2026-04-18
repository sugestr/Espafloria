<!-- v: 5 | updated: 2026-04-18T23:00Z -->
# Espafloria — Master Context

База знаний проекта автоматизации цветочной сети **Espafloria SL** (Barcelona, Spain) на Odoo.sh Custom + Make.com.

**Rep:** `sugestr/Espafloria`
**Ветка:** `main`
**Owner:** Andriy

---

## 🎯 Конечная цель

**Умная сеть цветочных магазинов**, где база и роботы делают основную работу по контролю сотрудников и структурной целостности бизнеса. Это позволяет экономить на управляющем персонале и направлять деньги на мотивацию полевых сотрудников.

Подробно: [`master-context/10_vision_and_roadmap.md`](master-context/10_vision_and_roadmap.md)

---

## 📚 Структура репо

Плоская. Всё живёт в `master-context/` на одном уровне — кроме одной подпапки `legacy_migrations/` со старыми одноразовыми скриптами.

```
Espafloria/                                      (repo root, local clone:
├── README.md                                      ~/Documents/master-context/)
└── master-context/
    ├── VERSIONS.md                                (sync-маркер)
    ├── SYNC_STATE.md                              (правило синхронизации)
    ├── CHANGELOG.md                               (rolling лог сессий)
    ├── 00_master_index.md                         (навигация + глоссарий)
    ├── 00_source_files_index.md                   (карта исходников)
    ├── 01_business_context.md … 12_ai_workflow.md
    ├── 99_invariants.md                           (железные правила)
    ├── calculate_in_shop_action.py                ┐
    ├── migrate_variant_action.py                  │ Odoo server actions
    ├── review_status_automation.py                ┘
    ├── prompt_ocr_v1.txt                          ┐
    ├── prompt_reconciliation_v3.5.txt             │ OpenAI system prompts
    ├── prompt_diagnostics_v3.1.txt                ┘
    ├── make_line_log_pack.txt                     ┐ Make.com line-log
    ├── make_line_log_unit.txt                     ┘ шаблоны
    ├── commit_worker_delivery.sh                  (worker tooling)
    └── legacy_migrations/                         ← единственная подпапка
        ├── image_import_from_holded_api.py
        ├── image_import_from_urls.py
        └── split_big_csv.py
```

### Как Owner'у обновлять Project knowledge

После каждого worker-коммита:

1. **Очисти** Project knowledge полностью
2. В Finder открой `~/Documents/master-context/master-context/`
3. **⌘A** по всему содержимому
4. **⌘-клик по папке `legacy_migrations/`** — сними с неё выделение
5. Drag-drop в Project knowledge

Одно действие. Всё нужное залито, старые migrations/скрипты оставлены в git.

Финальный sync-check: `v` у `VERSIONS.md` в Project = `v` в GitHub. См. [`master-context/SYNC_STATE.md`](master-context/SYNC_STATE.md).

---

## 📋 Протокол ведения

### Версионирование файлов

**Каждый `.md` начинается с:**
```markdown
<!-- v: N | updated: YYYY-MM-DDTHH:MMZ -->
```

`v` — integer, инкрементится при каждом значимом изменении. При правке: обновить header → обновить строку в `VERSIONS.md` → bump сам `VERSIONS.md`.

Полный worker-протокол (стадии, sandbox-delivery, commit-скрипт) — в [`master-context/12_ai_workflow.md`](master-context/12_ai_workflow.md).

---

## 🤖 Использование в AI-чатах

Новая сессия:
1. Убедиться, что Project knowledge свежий (sync-check по `VERSIONS.md`)
2. В первом сообщении worker пишет Self-ID (role / task / local_repo / reads VERSIONS v)
3. Читает `00_master_index.md` → `99_invariants.md` → файлы по задаче

Подробности — в `master-context/12_ai_workflow.md`.

---

## 🔗 Внешние ресурсы

- **Odoo прод:** https://espafloriasl.odoo.com
- **Make.com:** сценарий «Integration Telegram Bot» (55 модулей, достаём через Make MCP)
- **Google Sheets (ETL products):** [link](https://docs.google.com/spreadsheets/d/1ep4WA5ciu2R1-mVx9Ish2dGH1s9kdjVECGkkGBCsBaE)
- **Google Sheets (ETL albaran):** [link](https://docs.google.com/spreadsheets/d/1apNcpf7-44OGQVb39wNfZBU7INv3iyTGEFsZVOvH_58)
- **Регламент сотрудников:** Google Doc (legacy, Holded-based)

---

## 📅 Ключевые даты

- **2026-04-18** — Master Context v1.0 создан
- **2026-04-20** — MVP запуск (параллельно с Holded)
- **2027-01-01** — целевой полный cutover с Holded

---

## 🔒 Приватность

Приватный репозиторий. Не добавлять в файлы: реальные API keys / tokens / passwords, персональные данные клиентов, полные дампы БД.
