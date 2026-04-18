#!/usr/bin/env bash
# commit_worker_delivery.sh — стандартный финал worker-сессии.
#
# Воркер передаёт Owner'у один zip через present_files. Owner скачивает в
# ~/Documents/. По команде "commit" воркер через Desktop Commander вызывает
# этот скрипт — двумя шагами:
#
#   1) dry-run:  bash <этот скрипт> ~/Documents/<file>.zip
#      → unzip, git status + git diff --stat, останавливается
#   2) finalize: bash <этот скрипт> ~/Documents/<file>.zip --yes
#      → git add + commit -F .worker_commitmsg.txt + push, печатает SHA
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
[ "$#" -ge 1 ] || die "usage: $0 <path_to_zip> [--yes]"
ZIP="$1"
YES="${2:-}"

[ -f "$ZIP" ] || die "zip not found: $ZIP"
[ -d "$REPO_ROOT/.git" ] || die "not a git repo: $REPO_ROOT"

cd "$REPO_ROOT"

# --- preflight: clean working tree + up-to-date main ---
if [ -z "$YES" ]; then
    say "sync check in $REPO_ROOT"
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        die "working tree is dirty. Run 'git status' and resolve before delivery."
    fi
    if [ -n "$(git ls-files --others --exclude-standard)" ]; then
        die "untracked files present. Clean or commit them separately first."
    fi
    git pull --ff-only origin main

    # --- unzip on top of clone ---
    say "unzipping $(basename "$ZIP") into $REPO_ROOT"
    unzip -o -q "$ZIP" -d "$REPO_ROOT"

    [ -f "$COMMITMSG_PATH" ] || die "commit message missing at $COMMITMSG_PATH (zip must include it)"

    # --- show diff ---
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
    exit 0
fi

if [ "$YES" != "--yes" ]; then
    die "unexpected second arg: $YES (expected --yes)"
fi

# --- finalize path: commit + push ---
[ -f "$COMMITMSG_PATH" ] || die "commit message missing at $COMMITMSG_PATH (did you run dry-run first?)"

# In --yes mode we assume unzip already happened in the dry-run step.
# If nothing is staged/changed at all, bail out.
if git diff-index --quiet HEAD -- && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    die "nothing to commit (dry-run wasn't run, or zip had no changes)"
fi

say "git add ."
git add .

say "git commit"
git commit -F "$COMMITMSG_PATH"

# Remove the commitmsg file from the working tree for the NEXT commit
# (it's already baked into this commit's history via git log, not needed on disk).
# But since it's tracked in this commit, we add a follow-up that removes it.
# Simpler: keep it tracked — it's 10-40 lines of text per session and
# stays as a per-commit artifact in git log anyway. No cleanup.

say "git push"
git push origin main

SHA_SHORT=$(git rev-parse --short HEAD)
SHA_FULL=$(git rev-parse HEAD)
REMOTE_URL=$(git config --get remote.origin.url | sed -E 's#(git@github\.com:|https://github\.com/)([^/]+)/([^/.]+)(\.git)?#https://github.com/\2/\3#')

echo
echo "✅ Committed + pushed"
echo "   SHA:  $SHA_SHORT  ($SHA_FULL)"
echo "   Link: $REMOTE_URL/commit/$SHA_FULL"
echo
echo "📦 Reminder: перезалей Project knowledge"
echo "   1. Очисти старые .md в Claude Project"
echo "   2. Finder → $REPO_ROOT/master-context/"
echo "   3. Выдели все .md (⌘A, БЕЗ папки artifacts/)"
echo "   4. Drag-drop в Project knowledge"
