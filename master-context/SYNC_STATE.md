<!-- v: 9 | updated: 2026-04-19T12:30Z -->
# SYNC_STATE

**Один вопрос:** актуальна ли база знаний в Claude Project по сравнению с GitHub?

**Один ответ:** сравни `v` у `VERSIONS.md` в Project с `v` у `VERSIONS.md` в GitHub.

- **Равны** → работай.
- **Project < GitHub** → Owner перезаливает Project из локального клона (см. § Upload ниже).
- **Project > GitHub** → процессный баг, зови Owner.

---

## Upload в Project knowledge

**Это единственное место, где описан процесс.** README и `commit_worker_delivery.sh` только ссылаются сюда.

1. В Claude Project knowledge **удали все старые файлы** (иначе получишь дубликаты).
2. Finder → `~/Documents/master-context/master-context/`.
3. **⌘A** по всему содержимому папки.
4. **⌘-клик по `legacy_migrations/`** → снимает выделение с этой подпапки (одноразовые старые скрипты, в Project не нужны).
5. Drag-drop всё выделенное в Claude Project knowledge.

Одно движение. Всё остальное (`.md` + артефакты + `commit_worker_delivery.sh`) грузится вместе — так и задумано. Stub `README.md` в корне репо вне папки `master-context/` — не попадёт в drag-drop.

**Recovery:** если после drag-drop в Project заехала `legacy_migrations/` — удали эти 3 файла (`image_import_*.py`, `split_big_csv.py`) в UI Project. Не критично, только лишние токены.

---

## Текущее состояние

```yaml
versions_md_current: 10
last_session: "Meta cleanup: stale paths, --reset + zip-match in commit script, upload SoT in SYNC_STATE"
last_session_date: 2026-04-19
github_repo: sugestr/Espafloria
github_path: master-context/
local_clone: /Users/andriy/Documents/master-context
```

---

Протокол работы worker'а — в [12_ai_workflow.md](12_ai_workflow.md).
Правила версионирования — в [VERSIONS.md](VERSIONS.md).
