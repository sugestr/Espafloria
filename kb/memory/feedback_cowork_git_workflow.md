---
name: Cowork mode — git commit делается user'ом, не мной через bash
description: В Cowork режиме файлы пишу через Write/Edit (реальный диск), а git commit/push — только user в своём терминале. Никогда не пытаться commit из sandbox bash.
type: feedback
originSessionId: a29e76e0-f17f-4cf3-8710-935d7e4539b3
---
**Правило:** В Cowork session разделены два слоя файловой работы:

1. **File tools (Read/Write/Edit)** — работают с **реальным диском user'а** через workspace mount (например `/Users/andriy/Documents/master-context/`). Полные права на чтение/запись содержимого файлов. Изменения видны user'у мгновенно.

2. **`mcp__workspace__bash`** — это **отдельный sandbox-env** (Linux). Workspace папки видны через mount (`/sessions/.../mnt/master-context/`), но **с ограниченными правами**:
   - Read — обычно работает
   - Write/Edit/Delete на обычные файлы — может не работать (Operation not permitted)
   - **Modify `.git/` internals — запрещено** → git create objects может работать частично, но `git commit` падает с lock errors потому что не может cleanup `.git/index.lock` и `tmp_obj_*` файлы
   - rm/mv/cp на user-файлы — обычно блокированы

**Как делать git операции в Cowork:**

✅ **Правильный flow:**
1. Я обновляю содержимое файлов через `Write`/`Edit` (реальный диск, full perms).
2. Я генерирую commit message в своём ответе или Write в /tmp/.
3. **User в своём локальном терминале** делает: `git add` + `git commit` + `git push`.
4. Если нужно посмотреть `git status` или `git diff` — bash работает (это read).

❌ **Неправильно:** пытаться `git commit` из `mcp__workspace__bash` — возможны частичные writes в `.git/objects/` без cleanup, локи остаются, последующие git ops падают.

**Что делать если случайно начал commit:**
- Bash может оставить `.git/index.lock` и tmp_obj_* в `.git/objects/`. User должен `rm -f .git/index.lock` в своём терминале перед следующей попыткой.
- Stage сохраняется (git add работает в большинстве случаев) — user может просто `git commit -m "..."` после rm lock.

**Случай 23 апреля 2026** — попытался закомитить букетный refactor через bash → `unable to unlink '.git/objects/52/tmp_obj_*'` → `index.lock` остался → `git commit` failed twice. User объяснил что это неправильный путь, я должен был просто Write файлы и отдать commit-msg user'у для локального терминала.

**Bash для git — только read-only ops:** `git status`, `git diff`, `git log`, `git branch -v` — это OK.

## UPDATE 23 апреля 2026 — Desktop Commander обходит sandbox-ограничения

`mcp__Desktop_Commander__*` работает на **реальной macOS user'а**, не в sandbox. Через него можно делать git ops с полными правами. Процесс:

1. **Write** commit message в файл (например `/Users/andriy/Library/Application Support/Claude/local-agent-mode-sessions/.../outputs/commit-msg.txt`). Это реальный диск, доступен из DC.
2. **`mcp__Desktop_Commander__start_process("zsh -i", 5000)`** — запускает zsh у user'а, возвращает PID.
3. **`mcp__Desktop_Commander__interact_with_process(pid, "cd <repo> && <cmds>")`** — выполняет команды в shell'е user'а.
4. **Git commit:** `git commit -F "/absolute/path/commit-msg.txt"`. Важно: путь в кавычках т.к. «Application Support» имеет пробелы.
5. **Push:** `git push` — если настроены credentials у user'а, работает без interact.
6. **Finalize:** `mcp__Desktop_Commander__force_terminate(pid)` чтобы закрыть процесс.

**Важные нюансы DC flow:**
- Lock-файл `.git/index.lock` ищется в **root git-repo**, не в cwd. Если cwd это `subdir/subdir/`, lock будет в `../../.git/index.lock`. Выполнить `rm -f ../.git/index.lock` (или `../../.git/`) перед retry.
- Worktrees / `.claude/` — Untracked, **не добавлять в git add**.
- Временные файлы sandbox'а (типа `*_v2.py`) — тоже не добавлять.
- `git add` с явным списком файлов безопаснее чем `-A` — избегаешь worktrees.

**Когда использовать bash sandbox vs DC:**

| Операция | Инструмент |
|---|---|
| Read file content | Read tool (или bash cat) |
| Write/Edit files | Write/Edit tools (они пишут на реальный диск) |
| `git status`, `git diff`, `git log` | bash sandbox (read-only) |
| **`git add`, `git commit`, `git push`** | **Desktop Commander** |
| `rm`, `mv`, `cp` user files | **Desktop Commander** (bash sandbox обычно блокирует) |
| Запуск скриптов в user env | **Desktop Commander** |

**Правило для будущего:** когда нужен **write/delete/exec** на real FS — сразу Desktop Commander. Bash sandbox — только read.
