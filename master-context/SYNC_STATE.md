<!-- v: 6 | updated: 2026-04-18T22:30Z -->
# SYNC_STATE

**Один вопрос:** актуальна ли база знаний в Claude Project по сравнению с GitHub?

**Один ответ:** сравни `v` у `VERSIONS.md` в Project с `v` у `VERSIONS.md` в GitHub.

- **Равны** → работай.
- **Project < GitHub** → перезалей Project из локального клона (см. правила ниже).
- **Project > GitHub** → процессный баг, зови Owner.

---

## Что заливать в Project knowledge

Из `~/Documents/master-context/master-context/`:

- ✅ Все `.md` в корне (`00_*`, `01_*` … `12_*`, `99_*`, `CHANGELOG`, `SYNC_STATE`, `VERSIONS`)
- ✅ `artifacts/prompts/` (OpenAI system prompts — мелкие, нужны для обсуждения бота)
- ✅ `artifacts/templates/` (Make.com line-log шаблоны)
- ✅ `artifacts/code/odoo_actions/` (живые Odoo server actions, обсуждаются часто)

Не заливаем:
- ❌ `artifacts/code/migrations/` (одноразовые Holded-миграции, лежат в git, достаём вручную если понадобится)
- ❌ `artifacts/scripts/` (shell-скрипты протокола, Claude они не нужны в Project)
- ❌ `artifacts/makecom/` (если там окажется blueprint JSON — он ~230 KB, слишком тяжёлый; достаём через Make MCP)

---

## Текущее состояние

```yaml
versions_md_current: 7
last_session: "Split artifacts/code into odoo_actions + migrations"
last_session_date: 2026-04-18
github_repo: sugestr/Espafloria
github_path: master-context/
local_clone: /Users/andriy/Documents/master-context
```

---

Протокол работы worker'а — в [12_ai_workflow.md](12_ai_workflow.md).
Правила версионирования — в [VERSIONS.md](VERSIONS.md).
