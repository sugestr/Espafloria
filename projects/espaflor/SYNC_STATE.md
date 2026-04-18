<!-- v: 3 | updated: 2026-04-18T20:00Z -->
# SYNC_STATE

Этот файл отвечает на один вопрос: **актуальна ли база знаний в Claude Project
по сравнению с GitHub?**

---

## Принцип (v3, version-based)

Источник правды — **версия `VERSIONS.md`**. Это сводный индекс всех файлов
базы. Любая правка любого `.md` → bump версии VERSIONS.md. Значит:

> **Если `v` у `VERSIONS.md` в Project = `v` у `VERSIONS.md` в GitHub → синк.
> Если Project `v` < GitHub `v` → Project отстаёт, нужно перезалить.**

Никаких SHA-коммитов, никаких циклических зависимостей, никаких двойных коммитов.

---

## Текущее состояние

```yaml
versions_md_current: 4        # v поля в header VERSIONS.md
last_session: "Base Polish"   # что делала последняя рабочая сессия
last_session_date: 2026-04-18
github_repo: sugestr/espafloria
github_path: projects/espaflor/
```

Если в Project ты видишь `VERSIONS.md` с `v: 4` — ты актуален.
Если меньше — перезалей из GitHub.

---

## Протокол для нового чата (в начале сессии)

1. Открой `VERSIONS.md` в Project knowledge. Прочитай `v` из header'а.
2. Через `github:get_file_contents` прочитай `VERSIONS.md` в `main` branch (первые 2 строки достаточно).
3. Сравни два числа:
   - **Совпадают** → Project синхронизирован, работай.
   - **Project `v` < GitHub `v`** → alert Owner'у:

     > ⚠️ База в Project устарела. `VERSIONS.md` в Project = v`<N>`, в GitHub = v`<M>`.
     > Скачай свежие файлы с GitHub и перезалей в Project knowledge.
     > После этого можно работать.

   - **Project `v` > GitHub `v`** — не должно случаться. Значит worker писал в Project вручную или не закоммитил. Разобраться с Owner.

---

## Протокол для worker'а (когда кусок работы готов)

Когда worker считает, что выполнил свою часть задачи и хочет сохранить результат:

### Шаг 1. Подготовка в sandbox

1. Правки лежат в `/home/claude/...` (или эквивалент), **не в GitHub**.
2. Для **каждого изменённого файла**:
   - Bump `v` в header (`<!-- v: N | updated: YYYY-MM-DDTHH:MMZ -->`)
   - Обновить строку этого файла в `VERSIONS.md` (новый `v` и `updated`)
3. **Всегда** bump `v` + `updated` у самого `VERSIONS.md`.
4. Обновить `SYNC_STATE.md` → `versions_md_current` + `last_session` + `last_session_date`.
5. Добавить запись в `CHANGELOG.md` (содержательное описание что и почему).

### Шаг 2. Handoff Owner'у — не коммитить

**Worker НЕ коммитит автоматически.** Решение «пора фиксировать» принимает Owner.

Worker выдаёт в чат **handoff-блок** строго такого формата (чтобы легко копировался в Orchestrator):

```
📌 HANDOFF — <краткое название задачи>
Status: ready for review (не закоммичено)

Changes prepared:
• VERSIONS.md: v<old> → v<new>
• Files touched: <list с new v, по одному на строку>

Key decisions / what new chats need to know:
• <1–3 пункта, которые важны для Orchestrator'а / следующего worker'а>

Open questions (если есть):
• <вопросы к Owner, если без ответа коммитить рано>

Awaiting: "commit" или правки.
```

Если есть open questions — явно ждём ответ, не push'им.

### Шаг 3. После явного approve Owner'а («commit» / «пушь» / «закрой»)

1. Один commit с осмысленным message, все изменённые файлы одним push'ем.
2. Финальное сообщение Owner'у:

   ```
   ✅ Committed
   • SHA: <short_sha>
   • Message: "<commit message>"
   • Link: https://github.com/sugestr/espafloria/commit/<sha>
   • Перезалей в Project knowledge:
     - <файл 1>
     - <файл 2>
     - ...
   • Sync marker: VERSIONS.md теперь v<new>
   ```

3. Всё. Worker свою роль закрывает, следующий кусок — новый чат.

### Если Owner хочет правки до commit'а

Worker остаётся в том же чате, вносит правки в sandbox, выдаёт **новый** handoff-блок с тем же статусом `ready for review` — снова без push'а. Версии в header'ах не бампаются повторно (правки идут в рамках того же «раунда»).

---

## Handoff для Orchestrator

Owner копирует handoff-блок из worker'а и передаёт Orchestrator'у. Тот:
- Видит «Key decisions» → может обновить свой план
- Видит «Open questions» → решает, нужен ли другой worker или ответ от Owner
- Видит «Files touched» → понимает, какие части базы теперь свежее

Если задача была разбита Orchestrator'ом на несколько worker'ов, он запускает следующих по очереди, учитывая handoff предыдущих.

---

## Почему не SHA

Раньше пробовали. Проблемы:
- Commit, обновляющий `SYNC_STATE.md`, не может знать собственный SHA → всегда отставание на 1.
- Двойной коммит («записать — запушить — обновить SHA — запушить ещё раз») раздувает history и создаёт гонки между параллельными worker'ами.
- Для человека «v3 → v4» читается быстрее, чем «9cd7d56 → a980d40».

`v`-based sync решает это за счёт того, что **версия — свойство контента**,
а не операции push'а.

---

## FAQ

**Q: А если worker забыл bump'нуть `VERSIONS.md`?**
A: Это процессный баг. Следующий чат увидит: в GitHub файл изменился (по diff), но `v` у VERSIONS.md не вырос. Пусть проверит и прокричит Owner'у.

**Q: Что считать «правкой, достойной bump'а»?**
A: Любое изменение, которое Owner хотел бы увидеть при перезаливе. Опечатки и чистая пунктуация — можно без bump'а (только `updated` в файле, строку в VERSIONS.md не трогать). Всё остальное → bump.

**Q: Несколько worker'ов параллельно — что делать?**
A: Не делать. Один worker = одна задача = один commit. Параллельность — через Orchestrator, который сериализует задачи. См. [12_ai_workflow.md](12_ai_workflow.md).

**Q: Нужен ли всё ещё `CHANGELOG.md`?**
A: Да, он нужен отдельно — для **содержательной** истории (что и почему изменилось). `VERSIONS.md` отвечает только на вопрос «какая версия», `CHANGELOG.md` — «что внутри».

---

См. [12_ai_workflow.md](12_ai_workflow.md), [VERSIONS.md](VERSIONS.md), [CHANGELOG.md](CHANGELOG.md).
