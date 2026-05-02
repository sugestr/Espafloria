# Espafloria Master Context — standing instructions

База знаний проекта автоматизации Espafloria SL (Odoo Online Custom + Make.com + Telegram bot).
**Owner:** Andriy
**Prod:** espafloriasl.odoo.com
**Platform:** Odoo Online (SaaS) Custom — НЕ Odoo.sh (см. [06_infra.md](kb/06_infra.md), [99 §3](kb/99_invariants.md)).

---

## 📋 Читай при старте задачи (в таком порядке)

1. `kb/99_invariants.md` — 5 правил + 11 Odoo 19 gotchas. **Всегда** перед любой правкой.
2. `kb/00_index.md` — карта файлов + глоссарий + статусы.
3. `kb/01_project.md` — большая картина (бизнес + архитектура + roadmap + wishlist).
4. Тематический файл по задаче (02-09).

---

## 🚨 Жёсткие правила работы AI/инженера

### CHANGELOG обязателен
После **любого** изменения в системе (своими руками или через API) — запись в `CHANGELOG.md`. Одна строка сверху на сессию: `- YYYY-MM-DD — <subject>`. Больше 15 строк — удалить самую старую.

### Архив custom Python в репо
Любой `ir.actions.server` или `base.automation` с Python-кодом, работающий на prod, обязан иметь зеркало `.py` в `kb/add/` с префиксом блока (`NN_`). **Истина по факту работы — prod Odoo.** Репо — архив/бекап на случай потери БД, плюс git-history и review.

### `kb/` = только база знаний, data — в `pedido.files/`
В `kb/` лежат **главы** (00-09 + 99) + `kb/add/` со всеми служебными артефактами с префиксом блока (`NN_`): mirrors `.py`, prompts `.txt`, INSTR-инструкции, audit reports, sub-specs.

**Data / temp / output** файлы (paper PDF, ETL CSV, backups) — в `pedido.files/` на уровне выше KB. Пример: `pedido.files/reception_paper/` (170 paper PDF), `pedido.files/verdnatura/` (CSV импорта). Backups и прочие dumps — в `резервные копии Odoo базы/` или вне репо.

### Перед массовыми операциями — тест на одной записи
Миграция карточек, bulk-update полей, массовое изменение `purchase_method` — сначала **ОДНА** запись, проверка результата, потом batch.

### Не мигрировать на Odoo.sh без жёсткой нужды
Сейчас Odoo Online Custom. Переход — **one-way**. Сначала всё что можно — штатно на Online. Жёсткие триггеры миграции — когда хотелка физически невозможна на Online.

### Перед утверждением поведения Odoo — свериться с docs 19 / community / live-базой
**Не утверждать из памяти/тренировки.** Odoo 19 ≠ 17/18. Сверять [Odoo 19 docs](https://www.odoo.com/documentation/19.0/), live-базу через MCP, [Odoo Forum](https://www.odoo.com/forum), [OCA repos](https://github.com/OCA).

### Сначала штатное Odoo 19 / Apps Store / OCA — потом custom
Каждый custom field / action / module — осознанная цена поддержки. Прежде чем писать кастом: проверить native Odoo 19 → Apps Store (фильтр «Compatible with Odoo Online») → OCA (если на Odoo.sh) → только потом custom.

### Cowork: git ops через Desktop Commander
File tools (Write/Edit) пишут на реальный диск. Sandbox bash **не** модифицирует `.git/`. Но `mcp__Desktop_Commander__*` работает на реальной macOS user'а с полными правами — через него делаю `git add` / `commit` / `push` / `rm`. Bash sandbox — только read (`git status`, `git diff`, `git log`).

### Перед `git push` — diff на ревью
Большие изменения (несколько файлов / переименования / удаления) — показать diff в чате, дождаться «ок» перед коммитом/пушем.

---

## 🚧 Особые правила

### `99_invariants.md` редактируется только с явным подтверждением в чате
Любое изменение правил — обсуждаем в чате, потом правим.

### Бизнес-файлы (01-08) — факты, не история
Не добавляй записи «мы сделали X». Правь прямо в нужном месте, как будто так и было. История — в `CHANGELOG.md`.

### Snapshot-артефакты — синк с prod
`*.py`, `prompt_*.txt`, `make_line_log_*.txt` синхронизировать с prod при любой правке prod-копии (см. [99 §2](kb/99_invariants.md)).

### Длинные ответы — нумеровать секции
В моих длинных ответах используй иерархическую нумерацию (1, 1.1, 1.2, 2.1...) — owner ссылается номером на конкретный пункт.

---

## 📝 Версионирование .md

Каждый `.md` начинается с `<!-- v: N | updated: YYYY-MM-DDTHH:MMZ -->`.

**При значимой правке:**
1. Bump `v` в header файла.
2. Запись в `CHANGELOG.md`.

**Опечатки/пунктуация** — только `updated` (без bump `v`).

---

## 🗂️ Коммиты

- **CHANGELOG.md:** одна строка сверху на сессию, формат `- YYYY-MM-DD — <subject>`. Больше 15 строк — удали самую старую.
- **Commit message:** subject первой строкой, пустая строка, внятный body.

---

## ❌ Чего не делать

- Не создавай новых `.md` без моего одобрения.
- Не рефактори ради рефакторинга — меньше правок лучше.
- Не клади служебные артефакты в корень `kb/` — только в `kb/add/` с блок-префиксом `NN_`.
- Не утверждай поведение Odoo из памяти / тренировки — всегда сверять с docs 19 / live.

---

## 🎯 Конечная цель

**Умная сеть цветочных магазинов** — база и роботы делают основную работу по контролю сотрудников и структурной целостности бизнеса. Vision и принципы реализации — в [01_project.md](kb/01_project.md).
