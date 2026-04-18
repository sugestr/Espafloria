<!-- v: 5 | updated: 2026-04-18T22:00Z -->
# SYNC_STATE

**Один вопрос:** актуальна ли база знаний в Claude Project по сравнению с GitHub?

**Один ответ:** сравни `v` у `VERSIONS.md` в Project с `v` у `VERSIONS.md` в GitHub.

- **Равны** → работай.
- **Project < GitHub** → перезалей Project из `~/Documents/master-context/master-context/` (без папки `artifacts/`).
- **Project > GitHub** → процессный баг, зови Owner.

---

## Текущее состояние

```yaml
versions_md_current: 6
last_session: "Flat layout + sandbox-delivery protocol"
last_session_date: 2026-04-18
github_repo: sugestr/Espafloria
github_path: master-context/
local_clone: /Users/andriy/Documents/master-context
```

---

Протокол работы worker'а (стадии, sandbox-delivery, commit-скрипт) — в [12_ai_workflow.md](12_ai_workflow.md).
Правила версионирования — в [VERSIONS.md](VERSIONS.md).
