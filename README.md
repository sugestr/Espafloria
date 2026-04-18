<!-- v: 3 | updated: 2026-04-18T21:00Z -->
# Espafloria — Master Context

База знаний проекта автоматизации цветочной сети **Espafloria SL** (Barcelona, Spain) на Odoo.sh Custom + Make.com.

**Rep:** `sugestr/espafloria`
**Ветка:** `main`
**Owner:** Andriy

---

## 🎯 Конечная цель проекта

**Умная сеть цветочных магазинов**, где база данных и роботы делают основную работу по контролю сотрудников и структурной целостности бизнеса. Это позволяет экономить на управляющем персонале и направлять деньги на мотивацию полевых сотрудников.

Подробно: [`master-context/10_vision_and_roadmap.md`](master-context/10_vision_and_roadmap.md)

---

## 📚 Структура репозитория

Repo использует **flat layout**: вся база знаний лежит в одной папке
`master-context/`, без вложенных проектов. Артефакты (код, prompts,
Make.com blueprint) — рядом в `master-context/artifacts/`, в Claude
Project knowledge они **не загружаются** (читаются локально workers'ами
при необходимости).

```
Espafloria/                              (repo root, local clone:
├── README.md                              ~/Documents/master-context/)
└── master-context/                      ← всё, что грузится в Project knowledge
    ├── VERSIONS.md                        (sync-маркер всей базы)
    ├── SYNC_STATE.md                      (version-based sync протокол)
    ├── CHANGELOG.md                       (журнал изменений)
    ├── 00_master_index.md                 (навигация + глоссарий)
    ├── 00_source_files_index.md           (карта исходников)
    ├── 01_business_context.md             (бизнес, user stories, принципы)
    ├── 02_makecom_bot.md                  (Telegram-бот: OCR + reconciliation)
    ├── 03_odoo_receipt_review.md          (приёмка товара)
    ├── 04_holded_migration.md             (импорт из Holded)
    ├── 05_florists_logistics_accountant.md  (роли, процессы, бонусы)
    ├── 06_catalog_migration_toolkit.md      (миграция карточек)
    ├── 07_infrastructure_devops.md          (Odoo.sh, compliance)
    ├── 08_current_state_snapshot.md         (фото базы)
    ├── 09_open_work.md                      (TODO)
    ├── 10_vision_and_roadmap.md             (стратегия 15 шагов)
    ├── 11_crm_and_customers.md              (CRM)
    ├── 12_ai_workflow.md                    (multi-chat архитектура + протокол worker'ов)
    ├── 99_invariants.md                     (железные правила)
    └── artifacts/                         ← НЕ в Project knowledge
        ├── code/                            (Python + Odoo server actions)
        ├── prompts/                         (OpenAI system prompts: OCR, reconciliation, diagnostics)
        ├── templates/                       (Make.com line-log шаблоны)
        └── makecom/                         (Integration_Telegram_Bot_blueprint.json — ~230 KB)
```

### Как пользоваться Owner'у

**При заливке базы в Claude Project knowledge:**

1. Открой Finder → `~/Documents/master-context/master-context/`
2. Выдели все `.md`-файлы (⌘A) — **исключи папку `artifacts/`**
3. Drag-drop в Claude Project knowledge
4. Файлы из `artifacts/` (включая `Integration_Telegram_Bot_blueprint.json` ~230 KB) **не грузи** — worker прочитает их локально через `cat ~/Documents/master-context/master-context/artifacts/...` при необходимости

**При обновлении после коммита:** очисти Project knowledge полностью и повтори шаги 1-3.

---

## 📋 Протокол ведения

### Версионирование файлов

**Каждый `.md` начинается с:**
```markdown
<!-- v: N | updated: YYYY-MM-DDTHH:MMZ -->
```

- `v` — integer, **инкрементится при каждом значимом изменении** контента
- `updated` — ISO 8601 timestamp в UTC

**При правке файла:**
1. Обновить header (`v` и `updated`)
2. Синхронно обновить строку файла в `VERSIONS.md`
3. Сделать коммит

### Типы изменений

- **Patch** (опечатки, мелкие формулировки) — v не менять, только `updated`
- **Minor** (добавление раздела / информации) — v+1
- **Major** (переструктуризация, breaking изменения) — можно бампнуть +5 или округлить
- В любом случае — запись в `CHANGELOG.md`

### Commit message format

```
<file> v<N>: <краткое описание>

Примеры:
- 05_florists v2: добавлена бонусная модель и spec списания
- 02_makecom v2: platform dependencies section
- 99_invariants v3: +5 новых правил (роли, бонусы, зависимости)
```

### После коммита

⚠️ **НЕ ЗАБЫТЬ** перезалить обновлённые файлы в **Claude Project knowledge** — иначе AI в следующей сессии будет работать со старой версией.

Шаги:
1. Скачать ZIP с GitHub (или обновлённые файлы)
2. Project settings → Knowledge → удалить старые / загрузить новые
3. Или: заменить файлы inplace

**Sync check:** следующий чат сравнит `v` у `VERSIONS.md` в Project и в GitHub. Совпадает — работаем. Не совпадает — Owner перезаливает. См. [`master-context/SYNC_STATE.md`](master-context/SYNC_STATE.md).

---

## 🤖 Использование в AI-чатах

### Новая сессия с Claude (или другим AI)

1. Убедиться, что Project knowledge содержит актуальную версию Master Context
2. В первом сообщении: «Прочитай `00_master_index.md`, потом `99_invariants.md`, потом по задаче»
3. Для крупных задач — указать конкретный файл (например, при работе с ботом → `02_makecom_bot.md`)

### Протокол для AI-ассистента

AI, работающий с этой базой, **обязан**:
- Прочитать инварианты перед любыми архитектурными решениями
- Обновлять `CHANGELOG.md` при каждом изменении системы (в Odoo / в коде / в интеграциях)
- Предупреждать пользователя, если предлагаемое действие нарушает инвариант
- **При новых фактах/решениях** — формировать `.md` в нужной папке, бампать `v`, синхронно обновлять `VERSIONS.md`, напоминать пользователю перезалить в Claude Project

---

## 🔗 Внешние ресурсы

- **Odoo производственная:** https://espafloriasl.odoo.com
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

Это **приватный репозиторий**. Содержит:
- Архитектурные решения бизнеса
- Production code
- System prompts (OpenAI)
- Персональные данные отсутствуют, но бизнес-логика чувствительна

**Не добавлять в `.md`:**
- Реальные API keys / tokens / passwords
- Персональные данные клиентов
- Полные дампы БД

При необходимости секреты — через `.env` / GitHub Secrets.
