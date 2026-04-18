<!-- v: 8 | updated: 2026-04-18T23:30Z -->
# SYNC_STATE

**Один вопрос:** актуальна ли база знаний в Claude Project по сравнению с GitHub?

**Один ответ:** сравни `v` у `VERSIONS.md` в Project с `v` у `VERSIONS.md` в GitHub.

- **Равны** → работай.
- **Project < GitHub** → перезалей Project из локального клона (см. правило ниже).
- **Project > GitHub** → процессный баг, зови Owner.

---

## Как Owner заливает Project knowledge

Структура плоская: почти всё — на одном уровне в `master-context/`, только `legacy_migrations/` — в подпапке. В корне репо лежит stub `README.md` (только для GitHub-лендинга, в Project не грузим).

1. Finder → `~/Documents/master-context/master-context/`
2. ⌘A
3. **Сними выделение с папки `legacy_migrations/`** (одноразовые старые скрипты)
4. Drag-drop всё остальное в Claude Project knowledge

Одно движение. Полный `README.md` базы залетает вместе с остальными файлами.

---

## Текущее состояние

```yaml
versions_md_current: 9
last_session: "README moved into master-context/, root stub only"
last_session_date: 2026-04-18
github_repo: sugestr/Espafloria
github_path: master-context/
local_clone: /Users/andriy/Documents/master-context
```

---

Протокол работы worker'а — в [12_ai_workflow.md](12_ai_workflow.md).
Правила версионирования — в [VERSIONS.md](VERSIONS.md).
