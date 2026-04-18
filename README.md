<!-- v: 4 | updated: 2026-04-18T22:30Z -->
# Espafloria — Master Context

База знаний проекта автоматизации цветочной сети **Espafloria SL** (Barcelona, Spain) на Odoo.sh Custom + Make.com.

**Rep:** `sugestr/Espafloria`
**Ветка:** `main`
**Owner:** Andriy

---

## 🎯 Конечная цель проекта

**Умная сеть цветочных магазинов**, где база данных и роботы делают основную работу по контролю сотрудников и структурной целостности бизнеса. Это позволяет экономить на управляющем персонале и направлять деньги на мотивацию полевых сотрудников.

Подробно: [`master-context/10_vision_and_roadmap.md`](master-context/10_vision_and_roadmap.md)

---

## 📚 Структура репозитория

Flat layout: вся база знаний в `master-context/`, артефакты — в подпапках `master-context/artifacts/`.

```
Espafloria/                                    (repo root, local clone:
├── README.md                                    ~/Documents/master-context/)
└── master-context/                            ← что грузится в Project knowledge
    ├── VERSIONS.md                              (sync-маркер)
    ├── SYNC_STATE.md                            (правило синхронизации)
    ├── CHANGELOG.md                             (rolling лог сессий)
    ├── 00_master_index.md                       (навигация + глоссарий)
    ├── 00_source_files_index.md                 (карта исходников)
    ├── 01_business_context.md ... 12_ai_workflow.md
    ├── 99_invariants.md                         (железные правила)
    └── artifacts/
        ├── prompts/                           ← грузим в Project
        ├── templates/                         ← грузим в Project
        ├── code/
        │   ├── odoo_actions/                  ← грузим в Project (живые server actions)
        │   └── migrations/                    ← НЕ грузим (одноразовые Holded-скрипты)
        ├── scripts/                           ← НЕ грузим (commit_worker_delivery.sh)
        └── makecom/                           ← НЕ грузим (blueprint JSON, если появится)
```

### Как Owner'у обновлять Claude Project knowledge

После каждого коммита worker'а:

1. **Очисти** Project knowledge полностью (удали старые файлы)
2. В Finder открой `~/Documents/master-context/master-context/`
3. Drag-drop в Project knowledge по очереди:
   - Все `.md` из корня `master-context/` (⌘A по содержимому, **сними выделение с папки `artifacts/`**)
   - Содержимое `artifacts/prompts/`
   - Содержимое `artifacts/templates/`
   - Содержимое `artifacts/code/odoo_actions/`
4. **Не заливай** `artifacts/code/migrations/`, `artifacts/scripts/`, `artifacts/makecom/` — слишком узкоспециальные или тяжёлые, worker достанет из локального клона если понадобится

Финальный sync-check: `v` у `VERSIONS.md` в Project должен совпадать с `v` в GitHub. См. [`master-context/SYNC_STATE.md`](master-context/SYNC_STATE.md).

---

## 📋 Протокол ведения

### Версионирование файлов

**Каждый `.md` начинается с:**
```markdown
<!-- v: N | updated: YYYY-MM-DDTHH:MMZ -->
```

- `v` — integer, **инкрементится при каждом значимом изменении** контента
- `updated` — ISO 8601 timestamp в UTC

При правке файла: обновить header → обновить строку в `VERSIONS.md` → bump сам `VERSIONS.md`.

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
- **Make.com:** сценарий «Integration Telegram Bot» (55 модулей)
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

Приватный репозиторий. Не добавлять в `.md`: реальные API keys / tokens / passwords, персональные данные клиентов, полные дампы БД.
