<!-- v: 4 | updated: 2026-04-18T22:00Z -->
# 12. AI Workflow

Как несколько чатов Claude работают вместе над базой знаний.

**Источник правды** — `master-context/` в GitHub `sugestr/Espafloria`.
**Working copy для чтения** — Claude Project knowledge (Owner заливает вручную после каждого коммита).
**Sync-маркер** — `v` у [`VERSIONS.md`](VERSIONS.md), см. [`SYNC_STATE.md`](SYNC_STATE.md).

---

## 🎯 Проблема и решение

Длинный чат накапливает контекст, становится дорогим и начинает ошибаться. Решение: **один чат = одна задача**, общий источник правды в git, и worker готовит правки у себя в sandbox, а на машину Owner'а ходит только за финальным `git push`.

---

## 🧩 Роли

### Orchestrator
Получает от Owner крупную задачу, разбивает на шаги, пишет briefings для worker'ов. Не правит сам, не коммитит.

### Worker
Одна задача = один чат. Решает бизнес-задачу, при необходимости обновляет базу, отдаёт результат одним zip'ом. См. [Три стадии работы](#три-стадии-работы-workerа) ниже.

### Reviewer
Читает всю базу, ищет противоречия и устаревшие ссылки, репортит Owner'у. Не правит.

---

## Три стадии работы worker'а

### Стадия 1. Решить бизнес-задачу

Реальная работа — в проде: Odoo через MCP, Make.com через MCP, Python-скрипты, правка OpenAI prompts. База знаний в этот момент **не трогается**.

### Стадия 2. Решить, нужно ли обновлять базу

> **Обновляй, если следующему AI-чату через 2 недели это нужно было бы знать, чтобы не сломать бизнес.**

Да: новая бизнес-логика, смена инварианта, новая роль/процесс, новое постоянное поле в модели, смена source-of-truth.
Нет: разовый bug-fix, debug-скрипт, откачённый эксперимент, мелкий UI-tweak.

Правишь `.md` **прямо в нужном месте** — как будто так и было. Не добавляешь «запись о том, что мы сделали X»; бизнес-файлы хранят факты, а не историю.

### Стадия 3. Зафиксировать через sandbox-delivery

1. Sync-check — один вызов Desktop Commander:
   ```
   cd ~/Documents/master-context && git pull --ff-only && head -1 master-context/VERSIONS.md
   ```
   Если `v` в Project < `v` в GitHub → alert Owner, попроси перезалить Project, не работай.
2. Все правки — **в sandbox worker'а** (`/home/claude/delivery/master-context/...`), не в локальном клоне Owner'а. Для точечных правок — `str_replace` по копии файла из Project knowledge; полный `write_file` только при осознанном крупном рефакторинге (>50% файла).
3. На каждый изменённый `.md`: bump `v` + `updated` в header, обновить строку в `VERSIONS.md`, bump `v` у `VERSIONS.md`.
4. Одна короткая строка в `CHANGELOG.md` сверху (формат: `- YYYY-MM-DD — <subject>`). Если там стало больше 15 записей — удали самую старую.
5. Развёрнутый commit message — в `master-context/.worker_commitmsg.txt` внутри sandbox. Subject первой строкой, пустая строка, body. Этот файл войдёт в сам коммит и даст будущим читателям детали через `git show`.
6. Пакуешь в zip `master-context/` целиком со всеми изменёнными файлами и `.worker_commitmsg.txt`. Кладёшь в `/mnt/user-data/outputs/<имя>.zip`, вызываешь `present_files`. **Один файл, не два.**
7. Выдаёшь Owner'у [handoff-блок](#handoff-блок) и ждёшь «commit».
8. По команде «commit» — **один DC-вызов**, dry-run:
   ```
   bash ~/Documents/master-context/master-context/artifacts/scripts/commit_worker_delivery.sh /Users/andriy/Documents/<имя>.zip
   ```
   Скрипт проверит чистоту дерева, сделает `git pull --ff-only`, развернёт zip, покажет `git diff --stat` и commit message, остановится.
9. Owner смотрит diff, говорит «ок» → тот же скрипт с `--yes`:
   ```
   bash ~/Documents/master-context/master-context/artifacts/scripts/commit_worker_delivery.sh /Users/andriy/Documents/<имя>.zip --yes
   ```
   Скрипт коммитит (`git commit -F .worker_commitmsg.txt`), пушит, печатает SHA + link + reminder про Project knowledge.
10. Owner перезаливает Project knowledge из `~/Documents/master-context/master-context/` (drag-drop всех `.md`, **без папки `artifacts/`**). Sync закрыт.

**Типичный worker = ~4 DC-вызова:** git pull в начале, dry-run, `--yes`, ничего больше. 

---

## Handoff-блок

Worker выдаёт в чат после стадии 3, шаг 7:

```
📌 HANDOFF — <task>
Status: ready for review (не закоммичено)
Delivery: <имя>.zip (один файл, в нём — все .md + .worker_commitmsg.txt)

Changes:
• VERSIONS.md: v<old> → v<new>
• <file.md>: v<old> → v<new>
• ...

Key decisions (что важно знать следующим чатам):
• <1–3 пункта>

Open questions:
• <если есть>

Awaiting: скачай zip в /Users/andriy/Documents/, потом скажи "commit".
```

Owner копирует этот блок в orchestrator-чат, если задача была через orchestrator.

---

## Self-ID для worker-чата

Первым сообщением worker пишет:

```
role: worker
task: <short-id>
started: <YYYY-MM-DDTHH:MMZ>
local_repo: /Users/andriy/Documents/master-context
reads: VERSIONS.md v<N> из Project
```

---

## 🗂️ Состав базы (19 .md)

**Корень репо:** `README.md`

**`master-context/`:** `VERSIONS.md`, `SYNC_STATE.md`, `CHANGELOG.md`, `00_master_index.md`, `00_source_files_index.md`, `01_business_context.md` … `12_ai_workflow.md`, `99_invariants.md`.

**`master-context/artifacts/`** (в Project knowledge **не грузятся**): `code/`, `prompts/`, `templates/`, `makecom/Integration_Telegram_Bot_blueprint.json`, `scripts/commit_worker_delivery.sh`.

---

## GitHub MCP — только для чтения

Worker'у разрешены: `github:get_file_contents`, `github:list_commits`, `github:get_commit`, `github:search_code`.

Запрещены: `github:push_files`, `github:create_or_update_file`, `github:delete_file`, `github:create_branch`. Всё пишется через `git` в локальном клоне (один канал записи = один источник конфликтов; `push_files` не умеет `git mv` renames).

---

## Briefing: Orchestrator

<details>
<summary>Copy-paste в новый чат</summary>

```
Роль: orchestrator-чат проекта Espafloria (Odoo + Make.com).

Задача:
1. Принять крупную задачу от Owner
2. Прочитать актуальную базу (Project knowledge)
3. Проверить sync: github:get_file_contents master-context/VERSIONS.md, сравни v
4. Разбить задачу на worker-шаги
5. Для каждого — сформулировать briefing (Self-ID с local_repo, три стадии, боундари)
6. Выдать Owner список briefings
7. Ничего сам не правь

Читай только по необходимости: 00_master_index + 99_invariants + 12_ai_workflow + SYNC_STATE.
При конфликте с инвариантом — эскалируй, не придумывай.

Репо: sugestr/Espafloria, путь master-context/
Клон Owner'а: /Users/andriy/Documents/master-context
```

</details>

---

## Briefing: Worker

<details>
<summary>Copy-paste в новый чат</summary>

```
Роль: worker-чат проекта Espafloria.

## 🎯 Task
<одно предложение>

## 🪪 Self-ID (первым сообщением)
role: worker
task: <short-id>
started: <YYYY-MM-DDTHH:MMZ>
local_repo: /Users/andriy/Documents/master-context
reads: VERSIONS.md v<N> из Project

## 📂 Читай только по задаче
1. 00_master_index.md
2. 99_invariants.md
3. <файлы по теме>

## 🔍 Acceptance
- <критерий 1>
- <критерий 2>

## 📤 Output (стадия 3)
sandbox-delivery по протоколу из 12_ai_workflow.md § Три стадии:
- правки в /home/claude/delivery/master-context/, не в клоне
- bump v везде где надо, строка в CHANGELOG
- .worker_commitmsg.txt внутри zip
- один zip в /mnt/user-data/outputs/, present_files
- handoff-блок, ждать "commit"
- по "commit" — bash commit_worker_delivery.sh <zip>, потом --yes

## ⚠️ Boundaries
- не коммить без approve
- не править файлы в локальном клоне (всё в sandbox)
- github:* — только read
- не трогай файлы вне темы
- 99_invariants.md — только с explicit approval Owner'а
```

</details>

---

## Briefing: Reviewer

<details>
<summary>Copy-paste в новый чат</summary>

```
Роль: reviewer-чат базы знаний Espafloria. Ничего не правь — только репорть.

Шаги:
1. Прочти все 19 .md (README + master-context/*.md)
2. Противоречия между файлами
3. Устаревшие/циклические ссылки
4. Обещанные, но не созданные разделы
5. Дубликаты (одно описано в 2+ местах по-разному)
6. v в header каждого файла = v в VERSIONS.md? (spot-check)
7. Сможет ли новый AI быстро въехать?

Отчёт Owner'у:
🔴 CRITICAL   противоречия / breaking
🟡 MINOR      несоответствия / улучшения
🟢 SUGGESTIONS идеи по структуре
✅ GOOD       что работает

Репо: sugestr/Espafloria, путь master-context/
```

</details>

---

## См. также

- [`../README.md`](../README.md) — правила репо, как заливать Project knowledge
- [`VERSIONS.md`](VERSIONS.md) — индекс версий
- [`SYNC_STATE.md`](SYNC_STATE.md) — sync-маркер
- [`CHANGELOG.md`](CHANGELOG.md) — rolling log сессий
