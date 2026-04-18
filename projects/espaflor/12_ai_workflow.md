<!-- v: 1 | updated: 2026-04-18T18:00Z -->
# 12. AI Workflow — Multi-Chat Architecture

**Статус:** 🟢 **PROD** (протокол) / 🟡 **READY** (файлы базы готовы, worker-чаты нужно запустить)

Этот файл описывает, **как несколько чатов Claude работают вместе** над одной базой знаний без хаоса и конфликтов версий.

---

## 🎯 Цель архитектуры

**Проблема:** один длинный чат накапливает гигантский контекст → каждый новый ответ становится дорогим и медленным → AI «тяжелеет» и начинает ошибаться на деталях.

**Решение:** **разделение ролей** между специализированными чатами + **единый источник правды** в GitHub.

```
┌─────────────────────────────────────────────────────────┐
│                      OWNER (Andriy)                      │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
               ▼                      ▼
    ┌──────────────────┐    ┌──────────────────┐
    │   Orchestrator   │    │  Worker chats    │
    │   (координатор)  │───▶│  (1 task = 1 chat)│
    └──────────────────┘    └────────┬─────────┘
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
- Выполняет задачу (код, правки в Odoo, документация)
- Коммитит результат в GitHub (через `github:*` коннектор)
- Обновляет `VERSIONS.md` и `CHANGELOG.md` синхронно
- В конце сессии — **напоминает Owner** перезалить в Project knowledge

**Что НЕ делает:**
- Не выходит за рамки своего брифа
- Не обновляет файлы вне своей темы (если надо — отдельный worker)

### 3. Reviewer / QA

**Роль:** проверка консистентности базы знаний, поиск противоречий.

**Что делает:**
- Читает **всю** базу знаний
- Ищет противоречия между файлами (например, что-то сказано в 05 vs 99)
- Проверяет актуальность `VERSIONS.md`
- Находит устаревшие ссылки, обещанные-но-не-сделанные TODO
- Выдаёт **отчёт** Owner'у со списком проблем
- **Не правит сам** — только репортит

**Briefing:** см. [Briefing: Reviewer](#briefing-reviewer)

---

## 🔄 Протокол синхронизации

### Три места хранения базы знаний

| Место | Роль | Кто обновляет |
|---|---|---|
| **GitHub repo** `sugestr/espafloria` | **Source of truth** | Worker chats (через `github:*` коннектор) |
| **Claude Project knowledge** (этот проект) | Working copy для всех chats | **Owner вручную** (UI → Project settings → Knowledge) |
| **Worker's sandbox** (`/home/claude/...`) | Эфемерный scratchpad | Эфемерный, исчезает в конце сессии |

### Цикл обновления

```
1. Owner → Worker: "нужно X"
2. Worker читает базу из Project knowledge
3. Worker делает правки
4. Worker → GitHub: commit с новыми версиями
5. Worker → Owner: "⚠️ Обновил GitHub, commit {SHA}. Перезалей в Project."
6. Owner → Project knowledge: upload обновлённых файлов
7. Owner → SYNC_STATE.md: обновляет last_synced_commit
8. Следующий чат начинает с актуальной версии
```

### Sync check (как новый чат понимает, что знания устарели)

**В файле `SYNC_STATE.md`** хранится:
- `project_knowledge_last_updated: YYYY-MM-DDTHH:MM:SSZ`
- `project_knowledge_last_synced_commit: <git_sha_short>`

**Каждый worker/orchestrator в начале сессии:**
1. Читает `SYNC_STATE.md` из Project knowledge
2. Через `github:get_file_contents` читает последний коммит на `main`
3. Сравнивает SHA

**Если коммиты не совпадают → alert Owner'у:**
> ⚠️ **Внимание:** в GitHub есть коммит `abc1234` новее того, что загружен в Project (`def5678` от YYYY-MM-DD).
>
> Варианты:
> - Залить обновление в Project knowledge сейчас (рекомендую, 30 секунд)
> - Работать со старой версией (быстро, но рискуем конфликтами)
>
> Что выбираете?

---

## 📝 Шаблон briefing для worker'а

**Структура, которую Owner или Orchestrator передаёт новому worker-чату:**

```markdown
## 🎯 Task
[Одно предложение — что именно нужно сделать]

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
- GitHub: `sugestr/espafloria` (читай/пиши `projects/espaflor/`)
- Odoo MCP (если нужно трогать прод)
- Make.com MCP (если нужен бот)

## 📤 Output
- Коммит в GitHub с обновлёнными файлами
- Ответ мне с кратким резюме + commit SHA + "перезалей в Project"
- Обновление `VERSIONS.md` и `CHANGELOG.md`

## ⚠️ Boundaries
- НЕ трогай файлы вне темы задачи
- НЕ меняй инварианты без явного approval Owner'а
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
3. Проверить sync state (SYNC_STATE.md vs GitHub latest commit)
4. Разбить задачу на шаги
5. Для каждого шага — сформулировать briefing для worker-чата
6. Выдать Owner список briefings (copy-paste ready)
7. Ничего не менять сам, только координировать

Правила:
- Читать файлы ТОЛЬКО по необходимости
- Начинать с 00_master_index.md + 99_invariants.md + 12_ai_workflow.md
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
1. Прочитай все файлы в projects/espaflor/ (14 md + CHANGELOG + VERSIONS + README + SYNC_STATE)
2. Найди противоречия между файлами (например, одно в 05, другое в 99)
3. Найди устаревшие / циклические ссылки
4. Найди обещанные-но-не-созданные вещи (упомянуто «см. раздел X», а раздела нет)
5. Найди дубликаты (одно и то же описано в 2+ местах по-разному)
6. Проверь актуальность VERSIONS.md (версии в файлах совпадают с индексом?)
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

Copy-paste в новый чат (запустить ОДИН РАЗ):

<details>
<summary>Показать briefing</summary>

```
Роль: setup-чат для первоначального коммита базы знаний в GitHub.

Задача: залить всю базу знаний проекта Espafloria в GitHub repo sugestr/espafloria,
ветка main, путь projects/espaflor/.

Шаги:
1. Убедись, что GitHub коннектор подключен (проверь через tool_search)
2. Попроси у Owner ZIP с базой знаний (17 md + 3 subfolders: prompts, code, templates)
3. Создай структуру в repo:
   - README.md и VERSIONS.md в корне
   - Всё остальное в projects/espaflor/
4. Первоначальный commit: "Initial Master Context v1.0 (2026-04-18)"
5. Создай SYNC_STATE.md файл в projects/espaflor/ с текущим commit SHA
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
3. **Бампай версии.** После правки — `v` и `updated` в header + строка в `VERSIONS.md`.
4. **Коммить с описанием.** Commit message должен говорить ЧТО изменилось.
5. **Напоминай про sync.** В конце сессии — «перезалей в Project knowledge».
6. **Не меняй инварианты.** Только Owner может менять `99_invariants.md` (или эскалированный worker с явным approval).
7. **Sync check в начале.** Прочитай `SYNC_STATE.md` перед работой.

---

## См. также

- [README.md](README.md) — правила репо
- [VERSIONS.md](VERSIONS.md) — индекс версий файлов
- [SYNC_STATE.md](SYNC_STATE.md) — состояние синхронизации
- [CHANGELOG.md](CHANGELOG.md) — журнал изменений
