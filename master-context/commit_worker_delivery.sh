#!/usr/bin/env bash
# commit_worker_delivery.sh — стандартный финал worker-сессии.
#
# Воркер передаёт Owner'у один zip через present_files. Owner скачивает в
# ~/Documents/. По команде "commit" воркер через Desktop Commander вызывает
# этот скрипт — двумя шагами:
#
#   1) dry-run:  bash <этот скрипт> ~/Documents/<file>.zip
#      → unzip в tree, git status + git diff --stat, останавливается
#   2) finalize: bash <этот скрипт> ~/Documents/<file>.zip --yes
#      → проверяет что working tree совпадает с zip, git add + commit + push
#
#   reset:       bash <этот скрипт> --reset
#      → откатывает working tree (git checkout + git clean) если dry-run был
#        ошибочный или Owner передумал. Безопасно выйти до --yes.
#
# ASSUMPTIONS:
# - Локальный клон лежит в REPO_ROOT (см. ниже)
# - В zip есть master-context/.worker_commitmsg.txt с commit message
# - У Owner'а настроены git credentials для push

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/Documents/master-context}"
COMMITMSG_PATH="master-context/.worker_commitmsg.txt"

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "→ $*"; }

# --- args ---
[ "$#" -ge 1 ] || die "usage: $0 <path_to_zip> [--yes]  |  $0 --reset"
ZIP="$1"
YES="${2:-}"

# --- reset mode ---
if [ "$ZIP" = "--reset" ]; then
    [ -d "$REPO_ROOT/.git" ] || die "not a git repo: $REPO_ROOT"
    cd "$REPO_ROOT"
    say "resetting working tree in $REPO_ROOT"
    git checkout -- .
    git clean -fd
    say "✅ clean. You can now dry-run a different zip."
    exit 0
fi

[ -f "$ZIP" ] || die "zip not found: $ZIP"
[ -d "$REPO_ROOT/.git" ] || die "not a git repo: $REPO_ROOT"

cd "$REPO_ROOT"

# --- DRY-RUN path ---
if [ -z "$YES" ]; then
    say "sync check in $REPO_ROOT"
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        die "working tree is dirty. If from previous dry-run: bash $0 --reset"
    fi
    if [ -n "$(git ls-files --others --exclude-standard)" ]; then
        die "untracked files present. Clean or commit them separately first."
    fi
    git pull --ff-only origin main

    say "unzipping $(basename "$ZIP") into $REPO_ROOT"
    unzip -o -q "$ZIP" -d "$REPO_ROOT"

    [ -f "$COMMITMSG_PATH" ] || die "commit message missing at $COMMITMSG_PATH (zip must include it). Run: bash $0 --reset"

    echo
    say "git status:"
    git status --short
    echo
    say "git diff --stat:"
    git diff --stat
    echo
    say "commit message:"
    echo "---"
    cat "$COMMITMSG_PATH"
    echo "---"
    echo
    say "DRY RUN complete. To finalize, run the SAME command with --yes:"
    echo "  bash $0 $ZIP --yes"
    echo
    say "To abort and roll back: bash $0 --reset"
    exit 0
fi

if [ "$YES" != "--yes" ]; then
    die "unexpected second arg: $YES (expected --yes)"
fi

# --- FINALIZE path: commit + push ---
[ -f "$COMMITMSG_PATH" ] || die "commit message missing at $COMMITMSG_PATH (did you run dry-run first?)"

# Safety: verify --yes is being applied to the SAME zip that was dry-run'd.
# Compare commitmsg in zip vs working tree — if mismatch, user is about to
# commit content from a different zip.
if ! unzip -p "$ZIP" "$COMMITMSG_PATH" 2>/dev/null | cmp -s - "$COMMITMSG_PATH"; then
    die "zip content doesn't match working tree. Either:
  - you passed a different zip than the dry-run (re-run dry-run first), or
  - tree was modified since dry-run (bash $0 --reset, then dry-run again)"
fi

# Bail out if nothing actually changed.
if git diff-index --quiet HEAD -- && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    die "nothing to commit (dry-run wasn't run, or zip had no changes)"
fi

say "git add ."
git add .

say "git commit"
git commit -F "$COMMITMSG_PATH"

say "git push"
# If push fails, the commit is already local — Owner can retry manually:
#   git -C $REPO_ROOT push origin main
git push origin main

SHA_SHORT=$(git rev-parse --short HEAD)
SHA_FULL=$(git rev-parse HEAD)
REMOTE_URL=$(git config --get remote.origin.url | sed -E 's#(git@github\.com:|https://github\.com/)([^/]+)/([^/.]+)(\.git)?#https://github.com/\2/\3#')

echo
echo "✅ Committed + pushed"
echo "   SHA:  $SHA_SHORT  ($SHA_FULL)"
echo "   Link: $REMOTE_URL/commit/$SHA_FULL"
echo
echo "📦 Next: перезалей Project knowledge по процедуре из master-context/SYNC_STATE.md"
echo "   (удали старое → Finder → ⌘A → снять выделение с legacy_migrations/ → drag-drop)"
