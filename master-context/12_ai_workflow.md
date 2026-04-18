<!-- v: 9 | updated: 2026-04-19T22:15Z -->
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

## 🚚 Два пути доставки правок

База знаний лежит в GitHub (`sugestr/Espafloria`, ветка `main`). Правки физически попадают туда одним из двух способов — **оба валидны**, Owner выбирает по контексту задачи.

### Path A — Claude Code (терминал на Mac)

**Когда:** Owner за своим ноутом; задача подразумевает диалог, итеративные правки, разведку по нескольким файлам.

**Как:**
```
cd ~/Documents/master-context && claude
```

Claude читает файлы напрямую с диска, правит в месте, коммитит и пушит обычным `git`. Standing instructions — в [`../CLAUDE.md`](../CLAUDE.md) в корне репо (Claude Code автоматически читает на старте сессии; это заменяет Self-ID + Worker briefing из Path B).

Новые web-чаты в Claude Project видят правки после нажатия **«Sync now»** на GitHub-коннекторе в Project settings (см. [SYNC_STATE.md § Upload](SYNC_STATE.md#рекомендуемый-путь--github-connector)).

### Path B — Sandbox-delivery (zip через web-чат)

**Когда:** Owner на мобилке / чужом компе; точечная правка с известным diff; orchestrator-чат раскладывает задачу на несколько параллельных worker'ов; задача требует `present_files` / других web-only возможностей.

**Как:** полный протокол — в [§ Три стадии работы worker'а](#три-стадии-работы-workerа) ниже. Worker собирает zip, отдаёт через `present_files`, Owner качает и запускает `commit_worker_delivery.sh` локально.

### Выбор за 10 секунд

| Признак | Путь |
|---|---|
| Знаешь правку заранее, сидишь у Mac | любой (zip чуть быстрее на одной правке) |
| «Разведай и почини что увидишь» | Claude Code |
| Не за ноутом | Path B (zip) |
| Большой аудит + >5 файлов правок | Claude Code |
| Роль reviewer (только репорт, без правок) | любой |

Правила версионирования, bump `v`, CHANGELOG, неприкосновенность `99_invariants.md` — **одинаковы для обоих путей**.

---

## Три стадии работы worker'а

Ниже — детальный протокол Path B (zip через web-чат). Для Path A (Claude Code) большинство шагов автоматизировано самим инструментом; формальные ритуалы Self-ID / handoff не нужны.

### Стадия 1. Решить бизнес-задачу

Реальная работа — в проде: Odoo через MCP, Make.com через MCP, Python-скрипты, правка OpenAI prompts. База знаний в этот момент **не трогается**.

### Стадия 2. Решить, нужно ли обновлять базу

> **Обновляй, если следующему AI-чату через 2 недели это нужно было бы знать, чтобы не сломать бизнес.**

Да: новая бизнес-логика, смена инварианта, новая роль/процесс, новое постоянное поле в модели, смена source-of-truth.
Нет: разовый bug-fix, debug-скрипт, откачённый эксперимент, мелкий UI-tweak.

**Отдельное правило для snapshot-файлов:** если правил prod-артефакт, копия которого лежит в базе (Odoo server action `*.py`, OpenAI prompt `prompt_*.txt`, Make-шаблон `make_line_log_*.txt`) — **всегда** синкни файл в базе с prod. Это источник правды для следующих чатов.

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
   bash ~/Documents/master-context/master-context/commit_worker_delivery.sh /Users/andriy/Documents/<имя>.zip
   ```
   Скрипт проверит чистоту дерева, сделает `git pull --ff-only`, развернёт zip, покажет `git diff --stat` и commit message, остановится.
9. Owner смотрит diff, говорит «ок» → тот же скрипт с `--yes`:
   ```
   bash ~/Documents/master-context/master-context/commit_worker_delivery.sh /Users/andriy/Documents/<имя>.zip --yes
   ```
   Скрипт коммитит (`git commit -F .worker_commitmsg.txt`), пушит, печатает SHA + link + reminder про Project knowledge.
10. Owner перезаливает Project knowledge по процедуре из [`SYNC_STATE.md § Upload`](SYNC_STATE.md#upload-в-project-knowledge). Sync закрыт.

**Recovery, если что-то пошло не так на шаге 8-10:**
- Dry-run распаковал не тот zip / Owner передумал → `bash commit_worker_delivery.sh --reset` (откатывает working tree в чистое состояние).
- `--yes` закоммитил, но `git push` упал (сеть/auth) → Owner просто делает `git -C ~/Documents/master-context push origin main` вручную.

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

**Корень репо:** только короткий stub `README.md` (GitHub-лендинг, в Project не грузим).

**`master-context/`** (всё грузится в Project knowledge):
`README.md` (полный, с правилами репо и layout'ом), `VERSIONS.md`, `SYNC_STATE.md`, `CHANGELOG.md`, `00_master_index.md`, `00_source_files_index.md`, `01_business_context.md` … `12_ai_workflow.md`, `99_invariants.md`.

**`master-context/` на одном уровне с .md** — live-артефакты и тулинг, всё грузится в Project knowledge вместе с .md:
- 3 Odoo server actions (`calculate_in_shop_action.py`, `migrate_variant_action.py`, `review_status_automation.py`)
- 3 OpenAI prompts (`prompt_ocr_v1.txt`, `prompt_reconciliation_v3.5.txt`, `prompt_diagnostics_v3.1.txt`)
- 2 Make.com шаблона (`make_line_log_pack.txt`, `make_line_log_unit.txt`)
- `commit_worker_delivery.sh` — коммит-скрипт worker'а; Claude его не использует, но в drag-drop попадает (~3 KB, пренебрежимо)

Note: в Project knowledge точки в именах заменяются на подчёркивания (`prompt_reconciliation_v3_5.txt` в Project = `prompt_reconciliation_v3.5.txt` в репо) — особенность Project upload, см. [`02_makecom_bot.md § Промпты — source of truth`](02_makecom_bot.md).

**`master-context/legacy_migrations/`** — единственная подпапка. Одноразовые Holded-миграции (`image_import_from_holded_api.py`, `image_import_from_urls.py`, `split_big_csv.py`). В Project не грузятся, worker читает локально при необходимости.

Make.com blueprint JSON в репо не храним — достаём через Make MCP когда нужен.

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

## 📤 Output
sandbox-delivery по [§ Три стадии работы worker'а](#три-стадии-работы-workerа). Один zip в `/mnt/user-data/outputs/` через `present_files`, handoff-блок, ждёшь `commit`, потом dry-run + `--yes` через `commit_worker_delivery.sh`.

## ⚠️ Boundaries
- не коммить без approve
- не править файлы в локальном клоне (всё в sandbox)
- github:* — только read (см. § GitHub MCP)
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
1. Прочти все 19 .md (все в master-context/; stub README в корне не считается)
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

- [`README.md`](README.md) — правила репо, как заливать Project knowledge
- [`VERSIONS.md`](VERSIONS.md) — индекс версий
- [`SYNC_STATE.md`](SYNC_STATE.md) — sync-маркер
- [`CHANGELOG.md`](CHANGELOG.md) — rolling log сессий
