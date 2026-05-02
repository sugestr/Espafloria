<!-- v: 2 | updated: 2026-05-02T23:30Z -->

# INSTR — KB cleanup pass (компактификация и логичность базы знаний)

Промт для отдельного чата. Самодостаточный — копировать целиком.

**Контекст использования:**
- **Триггер:** база знаний разрослась, либо после крупной reorganization (rename, mass mv, новая глава), либо просто после нескольких циклов работы. Хотим компактнее, понятнее, без противоречий.
- **Когда запускать:** периодически (раз в 2-3 недели интенсивной работы), либо сразу после крупной reorganization (re-audit pass) для проверки что ничего не «потерялось в хвостах».
- **Не для:** добавления нового контента. Только cleanup существующего.

---

## Промт начинается

Ты работаешь над Espafloria SL Odoo 19 SaaS Custom (`espafloriasl.odoo.com`). Цель этой сессии — сделать базу знаний (`kb/`) компактнее, понятнее, без противоречий, **не теряя смысла**.

### Структура которая должна быть

```
kb/
├── 00_index.md … 09_pedido.md, 99_invariants.md   ← главы
├── README.md, CHANGELOG.md
├── add/                                            ← все артефакты с NN_ префиксом блока
└── memory/                                          ← auto-memory Claude
```

В корне `kb/` — **только главы**. В `kb/add/` — артефакты (mirrors, prompts, INSTR-инструкции, audit reports, sub-specs) с префиксом блока к которому относятся (`02_prompt_ocr_v1.txt`, `04_bouquet_on_payment_action.py`, `09_reception_algorithm.md` и т.д.).

Data файлы (paper PDF, ETL CSV, backups) — **НЕ в kb/**, на уровне выше в `pedido.files/` или вне репо. Аудит-репорты — внутри kb/add/ (например `04_pos_audit_*.md`, `09_reception_audit_v12_report.md`).

### Что прочитать в самом начале

1. `/Users/andriy/Documents/espafloria.odoo/CLAUDE.md` — правила работы AI/инженера. Особенно секции «`kb/` = только база знаний» и «Архив custom Python в репо».
2. `/Users/andriy/Documents/espafloria.odoo/kb/00_index.md` — карта файлов + глоссарий + статусы. Используй как master-list что есть.
3. `/Users/andriy/Documents/espafloria.odoo/kb/99_invariants.md` — 5 инвариантов + 11 Odoo 19 gotchas. Не нарушать.
4. `/Users/andriy/Documents/espafloria.odoo/kb/CHANGELOG.md` — последние 15 записей. Поможет понять что недавно меняли (особенно крупная reorganization 2026-05-02 — `master-context/` → `kb/`, всё в `add/`).

### Принципы owner (verbatim)

- «Логичность, компактность, непротиворечивость базы знаний»
- «Чтобы оно все не расползалось на кучу непонятных деталей»
- «Бизнес-файлы (01-09) — факты, не история»
- «Не добавляй записи "мы сделали X". Правь прямо в нужном месте, как будто так и было. История — в CHANGELOG.md»
- «Все артефакты должны к чему-то относиться по идее если они лежат в базе знаний» — отсюда блок-префикс на каждый файл в `kb/add/`

### Workflow

#### Шаг 1 — inventory

```bash
cd /Users/andriy/Documents/espafloria.odoo
ls kb/*.md kb/CHANGELOG.md kb/README.md
ls kb/add/
```

Для каждого файла зафиксируй:
- размер (в строках)
- header version + updated date
- последний commit (`git log --oneline -1 -- <path>`)

#### Шаг 2 — найти проблемы

Пройдись по каждому файлу и найди (без правок пока):

**(a) Противоречия:**
- Один и тот же факт описан в 2+ местах с разными значениями
- Cross-references на удалённые/переименованные файлы
- Status (🟢/🟡/🔴) не совпадает с реальностью (например, файл говорит «PROD», а после reset это уже READY)

**(b) Дубли:**
- Текст-копипаст между файлами (одна формулировка в 2-3 местах)
- Глоссарий-термин определён дважды
- Особо проверь пересечения: 02_makecom_bot (Route 2 reconciliation) vs 09_pedido (reconciliation domain), 03_inventory (приёмка stock-слой) vs 09_pedido (приёмка purchase-слой)

**(c) Stale (устаревшее):**
- Конкретные цифры из прошлой работы (например, «138 pedido закрыто», «id=42 Verdnatura» — после reset они могут быть мертвы)
- Дедлайны прошедшие
- Упоминания удалённых cards/sessions/orders
- Ссылки на закрытые/удалённые ID

**(d) Расползание:**
- Длинная история «мы сделали X» вместо короткого «X есть»
- Лишние meta-комментарии («раньше было Y, теперь Z» — если Z давно стабильно, Y можно удалить)
- Bullet списки которые могли быть таблицей или одной строкой

**(e) Битые ссылки и leftover paths:**
- `[link](file.md)` где file.md удалён/переименован
- Пути типа `master-context/foo` (старая структура — должно быть `kb/foo` или `kb/add/NN_foo`)
- Refs на артефакты без NN-префикса (старая структура: `prompt_ocr_v1.txt` — должно быть `add/02_prompt_ocr_v1.txt`)
- Абсолютные пути `/Users/andriy/Documents/master-context/...` (должно быть `/Users/andriy/Documents/espafloria.odoo/...`)

**(f) Block-префикс consistency** (особенно после reorganization):
- Все файлы в `kb/add/` имеют корректный `NN_` префикс?
- Reception family — все имеют `09_reception_` префикс?
- Cross-block INSTR'ы (если есть) — намеренно без префикса?

#### Шаг 3 — DRY-RUN отчёт

**ДО любых правок** покажи owner:

```
=== KB CLEANUP DRY-RUN REPORT ===

Inventory: X файлов / Y строк / Z артефактов

Проблем найдено:
  Противоречий: N (примеры)
  Дублей: M (примеры)
  Stale facts: K (примеры с цитатами)
  Расползания: P (примеры)
  Битых ссылок / leftover paths: Q

Предлагаемые правки (по файлам):
  kb/01_project.md:
    - Удалить: «...» (stale)
    - Сократить: «...» (расползание)
    - Поправить: «...» → «...» (противоречие с 04_pos)
  ...

Файлы которые НЕ трогаю (стабильные / FROZEN):
  - 99_invariants.md (только инварианты, не cleanup-зона)
  - 02_makecom_bot.md (per owner — вернётся, контентно не трогать)
  - kb/add/09_reception_audit_v12_prompt.md, _v14_prompt.md (исторические audit prompts)
  - kb/add/09_reception_audit_v12_report.md (исторический output)
  - kb/add/09_reception_handover_2026-04-29.md (v1 baseline FROZEN)
  - kb/add/09_reception_algorithm_v1.md (v1 snapshot FROZEN, для сравнения с v19)
  - kb/add/09_reception_algorithm.md — текущий v19 PRE-RESET, контентно ждёт verify → v20; **только** fix refs можно
  - kb/memory/* (auto-memory)

Estimated total строк удалено: ~N
Estimated total строк перефразировано: ~M
```

**ЖДИ owner «ок»** на план. Не приступай к правкам.

#### Шаг 4 — правки batch (после ок)

Применяй правки **по одному файлу за раз**. После каждого:
- Show diff stat (`git diff --stat <file>`)
- Bump `v: N` в header если правка значимая (или только `updated:` если опечатки)
- Move on к следующему

**Не переименовывай файлы и не двигай папки** в этом cleanup проходе — это отдельная reorganization. Только содержимое и refs.

**Не удаляй файлы** без явного «удалить» от owner per-file.

#### Шаг 5 — special checks (что НЕ трогать)

**(a) `02_makecom_bot.md`** — per owner: «конечно вернётся, не трогаем». Можно поправить **только** битые ссылки/cross-references если появились. Контентно — не трогать.

**(b) `kb/add/09_reception_handover_2026-04-29.md`** — v1 baseline алгоритма реконсиляции. FROZEN. Не помечать как устаревший. Можно дополнить статус-маркером в шапке если ещё нет. Refs path fixes разрешены.

**(c) `kb/add/09_reception_algorithm.md`** — current v19, PRE-RESET, требует verify. Trogat **только** если найдено внутреннее противоречие или битый ref после rename. Owner делает v1 vs v19 сравнение в отдельном чате.

**(d) `kb/add/09_reception_algorithm_v1.md`** — snapshot из git history (commit 58ceaf63). FROZEN, для сравнения. Не редактировать.

**(e) `kb/add/09_reception_audit_v12_prompt.md`, `_v14_prompt.md`, `09_reception_audit_v12_report.md`** — исторические audit prompts/output. FROZEN. Refs можно если оборвались, контент — нет.

**(f) `kb/memory/MEMORY.md` и `kb/memory/*.md`** — auto-memory Claude. **Не трогать руками**. Owner сам управляет.

#### Шаг 6 — verify

После всех правок:
- `git diff --stat` (общая картина)
- `grep -rn "master-context/" kb/` — leftover refs на старую структуру (должно быть пусто, кроме CHANGELOG history и FROZEN audit prompts)
- `grep -rn "Documents/master-context" kb/ CLAUDE.md README.md` — leftover absolute paths (должно быть пусто)
- Все cross-references в `kb/00_index.md` ведут на существующие файлы?
- Проверь NN_ префиксы консистентны (например `ls kb/add/ | grep -E "^[0-9]{2}_"`)

#### Шаг 7 — финальный отчёт owner

```
=== KB CLEANUP DONE ===

Файлов изменено: N
Строк удалено: K
Строк перефразировано: M
Файлов без изменений: P

Главные находки:
  - {concrete examples}

Что осталось на потом (не сделал в этой сессии):
  - {если что-то нашёл что требует решения owner}
```

#### Шаг 8 — CHANGELOG + commit

Одна строка в `kb/CHANGELOG.md` сверху (bump v):

```
- 2026-XX-XX — **KB cleanup pass**: N файлов почищено (убрано K строк stale + M противоречий + P дублей). Не тронуты: 02_makecom (will return), 99_invariants, reception_audit_*, reception_handover, reception_algorithm_v1, memory/. Подробности по файлам — git diff коммита.
```

Если CHANGELOG > 15 entries — удали самую старую.

Git commit + push (через `mcp__Desktop_Commander__start_process` для git ops, не bash sandbox).

### Hard rules (CLAUDE.md)

- **Не создавай новых .md** без явного approval owner.
- **Не рефактори ради рефакторинга** — меньше правок лучше. Cleanup, не переписывание.
- **Не клади служебные артефакты в корень `kb/`** — только в `kb/add/` с блок-префиксом `NN_`.
- **Не утверждай поведение Odoo** из памяти — если правишь stale fact, проверь live-базой через MCP.
- **`99_invariants.md` НЕ трогать** без явного chat-разрешения.
- **memory/ НЕ трогать** руками — это auto-memory.

### Запрещено

- НЕ объединять `.md` файлы (если 2 файла можно слить — это отдельное reorganization, не cleanup).
- НЕ переименовывать файлы.
- НЕ перемещать файлы между папками (kb/ ↔ kb/add/).
- НЕ удалять `.md` файлы.
- НЕ менять структуру корня `kb/` (главы 00-09 + 99 + README + CHANGELOG + add/ + memory/).
- НЕ трогать `02_makecom_bot.md` контентно (только если найдена битая ссылка).
- НЕ трогать FROZEN reception файлы (handover, audit prompts, audit report, algorithm_v1) контентно.

### Что МОЖНО

- Удалять stale facts (с подтверждением owner на dry-run).
- Перефразировать длинные параграфы в более короткие без потери смысла.
- Обновлять status-маркеры (🟢/🟡/🔴) если они не совпадают с реальностью.
- Чинить cross-references на переименованные файлы.
- Свернуть bullet-списки в таблицы где это уместно.
- Удалять расползающиеся meta-комментарии («раньше было X, теперь Y» если Y давно стабильно).
- Bump `v:` headers на изменённых файлах.

## Промт заканчивается
