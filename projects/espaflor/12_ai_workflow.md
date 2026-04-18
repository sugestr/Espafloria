<!-- v: 2 | updated: 2026-04-18T20:00Z -->
# 12. AI Workflow — Multi-Chat Architecture

**Статус:** 🟢 **PROD** (протокол) / 🟡 **READY** (файлы базы готовы, worker-чаты запускаются по задачам)

Этот файл описывает, **как несколько чатов Claude работают вместе** над одной базой знаний без хаоса и конфликтов версий.

---

## 🎯 Цель архитектуры

**Проблема:** один длинный чат накапливает гигантский контекст → каждый новый ответ становится дорогим и медленным → AI «тяжелеет» и начинает ошибаться на деталях.

**Решение:** **разделение ролей** между специализированными чатами + **единый источник правды** в GitHub + **version-based sync** через `VERSIONS.md`.

```
┌─────────────────────────────────────────────────────────┐
│                      OWNER (Andriy)                      │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
               ▼                      ▼
    ┌──────────────────┐    ┌───────────────────┐
    │   Orchestrator   │    │   Worker chats    │
    │   (координатор)  │───▶│   (1 task = 1 chat)│
    └──────────────────┘    └────────┬──────────┘
               ▲                      │
               │                      ▼
    ┌──────────┴──────────────────────────────┐
    │    GitHub repo: sugestr/espafloria      │
    │    (source of truth)                     │
    └──────────────┬──────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  Claude Project knowledge    │
    │  (working copy, uploaded     │
    │   by Owner after each commit)│
    └──────────────────────────────┘
```

---

## 🧩 Типы чатов

### 1. Orchestrator (координатор)

**Роль:** стратегическое планирование, декомпозиция задач, видит общую картину.

**Что делает:**
- Получает от Owner высокоуровневую задачу («нужно настроить бонусную систему»)
- Разбивает её на шаги
- Определяет, какой **worker** нужен для каждого шага
- Формулирует briefing для worker'а
- Принимает результат от worker'а
- Коммитит **meta-changes** в GitHub (например, новый TODO в `09_open_work.md`)

**Что НЕ делает:**
- Не лезет в код
- Не делает массовых правок
- Не ставит hot-fix в Odoo напрямую

**Briefing:** см. [Briefing: Orchestrator](#briefing-orchestrator)

### 2. Worker (исполнитель)

**Роль:** одна задача = один чат = одно решение.

**Что делает:**
- Получает конкретный briefing (от Orchestrator или напрямую от Owner)
- Читает только **нужные** файлы базы знаний
- Выполняет задачу (правит `.md` в sandbox, код, правки в Odoo)
- **Когда считает кусок готовым** — выдаёт Owner'у **handoff-блок** (не коммитит сам)
- По явной команде Owner'а («commit») — push в GitHub, возвращает SHA
- В финальном сообщении — напоминает Owner перезалить в Project knowledge

**Что НЕ делает:**
- Не коммитит без явного approve Owner'а (Owner сам решает, пора ли фиксировать)
- Не выходит за рамки своего брифа
- Не обновляет файлы вне своей темы (если надо — отдельный worker)

**Handoff-формат и полный протокол:** см. [SYNC_STATE.md § Протокол для worker'а](SYNC_STATE.md#протокол-для-workerа-когда-кусок-работы-готов).

### 3. Reviewer / QA

**Роль:** проверка консистентности базы знаний, поиск противоречий.

**Что делает:**
- Читает **всю** базу знаний (19 md-файлов, см. ниже)
- Ищет противоречия между файлами (например, что-то сказано в 05 vs 99)
- Проверяет актуальность `VERSIONS.md`
- Находит устаревшие ссылки, обещанные-но-не-сделанные TODO
- Выдаёт **отчёт** Owner'у со списком проблем
- **Не правит сам** — только репортит

**Briefing:** см. [Briefing: Reviewer](#briefing-reviewer)

---

## 🗂️ Состав базы знаний (19 файлов)

Полный список `.md` в репо:

**Корень `sugestr/espafloria/`:**
- `README.md`
- `VERSIONS.md`

**`projects/espaflor/`:**
- `00_master_index.md`
- `00_source_files_index.md`
- `01_business_context.md`
- `02_makecom_bot.md`
- `03_odoo_receipt_review.md`
- `04_holded_migration.md`
- `05_florists_logistics_accountant.md`
- `06_catalog_migration_toolkit.md`
- `07_infrastructure_devops.md`
- `08_current_state_snapshot.md`
- `09_open_work.md`
- `10_vision_and_roadmap.md`
- `11_crm_and_customers.md`
- `12_ai_workflow.md` ← этот файл
- `99_invariants.md`
- `CHANGELOG.md`
- `SYNC_STATE.md`

Папки с артефактами (не версионируются через VERSIONS.md): `prompts/`, `code/`, `templates/`.

---

## 🔄 Протокол синхронизации (version-based)

### Источник правды для sync

**Один файл — `VERSIONS.md` — содержит таблицу «все `.md` + их `v`».**
Версия самого `VERSIONS.md` в header'е (`<!-- v: N ... -->`) является маркером состояния всей базы.

> **Sync-check = сравнить `v` у `VERSIONS.md` в Project и в GitHub.**

Детали — в [SYNC_STATE.md](SYNC_STATE.md). Здесь только короткая версия.

### Три места хранения базы знаний

| Место | Роль | Кто обновляет |
|---|---|---|
| **GitHub repo** `sugestr/espafloria` | **Source of truth** | Worker chats (через `github:*` коннектор) |
| **Claude Project knowledge** (этот проект) | Working copy для всех chats | **Owner вручную** (UI → Project settings → Knowledge) |
| **Worker's sandbox** (`/home/claude/...`) | Эфемерный scratchpad | Эфемерный, исчезает в конце сессии |

### Цикл работы worker'а

```
1. Owner → Worker: "нужно X"
2. Worker читает базу из Project knowledge
3. (опционально) Worker через github:get_file_contents проверяет VERSIONS.md в main
   — если v в GitHub > v в Project, alert Owner "база устарела, перезалей"
4. Worker делает правки в своей sandbox (/home/claude/...)
5. Для каждого изменённого .md — bump v + updated в header + строка в VERSIONS.md
6. VERSIONS.md сам тоже bump v + updated
7. Строка в CHANGELOG.md + обновить SYNC_STATE.md (versions_md_current + last_session)

   ─── GATE: Worker НЕ коммитит, только готовит ───

8. Worker выдаёт handoff-блок Owner'у:
   • файлы и их новые v
   • key decisions для Orchestrator'а
   • open questions (если есть)
   • статус "ready for review"

9. Owner читает, решает: "commit" / "подправь X" / "подожди, сначала Y".

10. Если commit одобрен:
    • Worker один push'ем в GitHub
    • возвращает SHA + link + список файлов для перезаливки в Project
```

Полная формулировка handoff-блока и правил коммита — в [SYNC_STATE.md § Протокол для worker'а](SYNC_STATE.md#протокол-для-workerа-когда-кусок-работы-готов).

### Sync check — новый чат в начале сессии

```
1. Открой VERSIONS.md в Project knowledge → v = N
2. github:get_file_contents VERSIONS.md main → v = M
3. Если N == M: ОК, работай
   Если N < M: alert Owner, попроси перезалить
   Если N > M: процессная ошибка, эскалируй
```

**Зачем этот check:** если в Project лежит устаревшая база, worker может
пропустить уже принятые решения и случайно откатить изменения коллеги.

---

## 📨 Передача handoff-блока от Worker'а в Orchestrator

Один канал — **синхронный**. Когда worker готов, он выдаёт handoff-блок в чат (формат — [SYNC_STATE.md § Шаг 2](SYNC_STATE.md#шаг-2-handoff-owneru--не-коммитить)). Owner копирует этот блок и вставляет в orchestrator-чат. Всё.

`CHANGELOG.md` — не отдельный канал передачи, а **обязательная часть работы worker'а** в любом случае. Orchestrator, который подключается к проекту через неделю и не получил copy-paste, просто читает свежую запись в CHANGELOG как часть базы знаний. Специальных ритуалов асинхронной передачи не заводим.

Что Orchestrator делает после получения handoff:
- Видит «Key decisions» → обновляет план / брифинги следующих worker'ов
- Видит «Open questions» → решает, нужен ли ещё worker или прямой ответ Owner'а
- Видит «Files touched» → знает, какие части базы теперь свежее

Если задача разбита на нескольких worker'ов, Orchestrator запускает следующих по очереди, учитывая handoff предыдущих.

---

## 📝 Шаблон briefing для worker'а

**Структура, которую Owner или Orchestrator передаёт новому worker-чату:**

```markdown
## 🎯 Task
[Одно предложение — что именно нужно сделать]

## 🪪 Self-ID (worker пишет это первым сообщением)
role: worker
task: <short-id типа "base-polish" / "route1-mod" / "pos-pin-auth">
started: <YYYY-MM-DDTHH:MMZ>
reads: VERSIONS.md v<N> из Project  (чтобы Owner сразу видел, с какой версии базы работаешь)

## 📂 Context files to read (в порядке приоритета)
1. `00_master_index.md` — навигация
2. `99_invariants.md` — правила, которые нельзя нарушать
3. [конкретные файлы по теме, напр. `05_florists_*.md` для темы бонусов]

НЕ читай всю базу — экономь токены, читай только по задаче.

## 🔍 Acceptance criteria
- [Критерий 1]
- [Критерий 2]
- [Критерий 3]

## 🛠️ Tools / integrations available
- GitHub: `sugestr/espafloria` (читай/пиши `projects/espaflor/`, корень для README/VERSIONS)
- Odoo MCP (если нужно трогать прод)
- Make.com MCP (если нужен бот)

## 📤 Output
- Bump v в каждом изменённом .md (header + VERSIONS.md)
- Bump v у VERSIONS.md
- Строка в CHANGELOG.md
- Обновить SYNC_STATE.md (versions_md_current + last_session)
- **Handoff-блок** Owner'у (не коммитить!):
    - список изменённых файлов + новые v
    - key decisions (что важно знать Orchestrator'у)
    - open questions
    - статус "ready for review, awaiting commit approve"
- После явного "commit" от Owner'а — push, SHA, напоминание перезалить

## ⚠️ Boundaries
- НЕ коммить в GitHub без явной команды Owner'а
- НЕ трогай файлы вне темы задачи
- НЕ меняй инварианты (99_invariants.md) без явного approval Owner'а
- При сомнении — спроси, а не угадай
```

---

## Briefing: Orchestrator

Copy-paste в новый чат:

<details>
<summary>Показать briefing</summary>

```
Роль: ты orchestrator-чат проекта Espafloria (цветочный бизнес на Odoo+Make.com).

Твоя задача:
1. Принять высокоуровневую задачу от Owner (Andriy)
2. Прочитать актуальную базу знаний из Project knowledge
3. Проверить sync: v у VERSIONS.md в Project vs в GitHub (github:get_file_contents
   projects/espaflor/VERSIONS.md → сравни первую строку header'а)
4. Разбить задачу на шаги
5. Для каждого шага — сформулировать briefing для worker-чата
6. Выдать Owner список briefings (copy-paste ready)
7. Ничего не менять сам, только координировать

Правила:
- Читать файлы ТОЛЬКО по необходимости
- Начинать с 00_master_index.md + 99_invariants.md + 12_ai_workflow.md + SYNC_STATE.md
- При конфликте с инвариантом — не придумывать, эскалировать Owner'у
- После каждой сессии — sign off "я оркестратор, вот briefings для workers"

База знаний: GitHub sugestr/espafloria/projects/espaflor/
```

</details>

---

## Briefing: Reviewer

Copy-paste в новый чат:

<details>
<summary>Показать briefing</summary>

```
Роль: ты reviewer-чат для базы знаний проекта Espafloria.

Задача: проверить консистентность, логичность и удобство базы знаний.
НИЧЕГО НЕ ПРАВЬ — только репорть.

Шаги:
1. Прочитай все 19 md-файлов:
   - В корне: README.md, VERSIONS.md
   - В projects/espaflor/: 00_master_index, 00_source_files_index, 01..12,
     99_invariants, CHANGELOG, SYNC_STATE
2. Найди противоречия между файлами (например, одно в 05, другое в 99)
3. Найди устаревшие / циклические ссылки
4. Найди обещанные-но-не-созданные вещи (упомянуто «см. раздел X», а раздела нет)
5. Найди дубликаты (одно и то же описано в 2+ местах по-разному)
6. Проверь актуальность VERSIONS.md (v в header каждого файла == v в индексе?)
7. Оцени удобство — сможет ли новый AI-ассистент быстро войти в контекст?

Выдай отчёт формата:
- 🔴 CRITICAL: противоречия / breaking
- 🟡 MINOR: несоответствия / улучшения
- 🟢 SUGGESTIONS: идеи по структуре
- ✅ GOOD: что работает хорошо

Не комитить, не править, не лезть в прод. Только репорт Owner'у.

База знаний: GitHub sugestr/espafloria/projects/espaflor/
```

</details>

---

## Briefing: Initial GitHub commit

**Одноразовый briefing для первой заливки.** Актуально только если базу разворачивают в новом repo с нуля.

<details>
<summary>Показать briefing</summary>

```
Роль: setup-чат для первоначального коммита базы знаний в GitHub.

Задача: залить всю базу знаний проекта Espafloria в GitHub repo sugestr/espafloria,
ветка main.

Шаги:
1. Убедись, что GitHub коннектор подключен (проверь через tool_search)
2. Попроси у Owner ZIP с базой знаний (19 md + 3 subfolders: prompts, code, templates)
3. Создай структуру в repo:
   - README.md и VERSIONS.md в корне
   - Всё остальное в projects/espaflor/
4. Первоначальный commit: "Initial Master Context v1.0 (<date>)"
5. Убедись что SYNC_STATE.md присутствует в projects/espaflor/ с актуальным v у VERSIONS.md
6. Верни Owner ссылку на repo + commit SHA
7. Напомни: "теперь залей в Project knowledge"

ВАЖНО:
- Не меняй содержимое файлов — только заливай как есть
- Если структура в ZIP отличается от ожидаемой — уточни у Owner
- Commit message на английском, содержательные

Repo: sugestr/espafloria
Ветка: main
```

</details>

---

## 🔒 Правила для всех типов чатов

1. **Одна тема — один чат.** Не смешивай задачи.
2. **Читай целенаправленно.** Не качай всю базу, если нужен один файл.
3. **Бампай версии.** После правки — `v` и `updated` в header + строка в `VERSIONS.md` + bump `VERSIONS.md` сам.
4. **Worker не коммитит сам.** Worker готовит handoff-блок. Решение «commit» — за Owner'ом.
5. **Коммить с описанием.** После approve — осмысленный commit message.
6. **Напоминай про sync.** После commit'а — «VERSIONS.md: v<old → new>, перезалей в Project».
7. **Не меняй инварианты.** Только Owner может менять `99_invariants.md` (или эскалированный worker с явным approval).
8. **Sync check в начале.** Сравни `v` у `VERSIONS.md` в Project и GitHub до работы.

---

## См. также

- [README.md](README.md) — правила репо
- [VERSIONS.md](VERSIONS.md) — индекс версий файлов (sync source)
- [SYNC_STATE.md](SYNC_STATE.md) — протокол синхронизации (version-based)
- [CHANGELOG.md](CHANGELOG.md) — журнал изменений
