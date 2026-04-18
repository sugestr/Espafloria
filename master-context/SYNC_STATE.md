<!-- v: 10 | updated: 2026-04-19T22:15Z -->
# SYNC_STATE

**Один вопрос:** актуальна ли база знаний в Claude Project по сравнению с GitHub?

**Один ответ:** сравни `v` у `VERSIONS.md` в Project с `v` у `VERSIONS.md` в GitHub.

- **Равны** → работай.
- **Project < GitHub** → Owner перезаливает Project из локального клона (см. § Upload ниже).
- **Project > GitHub** → процессный баг, зови Owner.

---

## Upload в Project knowledge

**Это единственное место, где описан процесс.** README и `commit_worker_delivery.sh` только ссылаются сюда.

### Рекомендуемый путь — GitHub connector

Один раз настраиваешь в Claude Project settings:
1. Project knowledge → **+ Add content** → **GitHub** → выбрать репо `sugestr/Espafloria`.
2. **Configure files** → включить папку `master-context/`, снять галку с `legacy_migrations/`.

После каждого `git push`:
- Открой Project settings → блок GitHub connector → нажми **«Sync now»** (секунды).

Новые чаты в Project после этого видят свежее состояние main.

### Fallback — ручной drag-drop

Если коннектор недоступен (ошибка auth / баг платформы / нужен другой репо в этом Project):

1. В Claude Project knowledge **удали все старые файлы** (иначе получишь дубликаты).
2. Finder → `~/Documents/master-context/master-context/`.
3. **⌘A** по всему содержимому папки.
4. **⌘-клик по `legacy_migrations/`** → снимает выделение с этой подпапки (одноразовые старые скрипты, в Project не нужны).
5. Drag-drop всё выделенное в Claude Project knowledge.

Stub `README.md` в корне репо вне папки `master-context/` — не попадёт в drag-drop.

**Recovery:** если после drag-drop в Project заехала `legacy_migrations/` — удали эти 3 файла (`image_import_*.py`, `split_big_csv.py`) в UI Project. Не критично, только лишние токены.

---

## Текущее состояние

```yaml
versions_md_current: 11
last_session: "Two transport paths documented (Claude Code + zip), GitHub connector in SYNC_STATE"
last_session_date: 2026-04-19
github_repo: sugestr/Espafloria
github_path: master-context/
local_clone: /Users/andriy/Documents/master-context
```

---

Протокол работы worker'а — в [12_ai_workflow.md](12_ai_workflow.md).
Правила версионирования — в [VERSIONS.md](VERSIONS.md).
