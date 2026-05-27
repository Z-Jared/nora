#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== git status =="
git status --short --branch

echo
echo "== Codex PM inbox =="
sed -n '1,260p' agent_tasks/PM_INBOX.md

echo
echo "== Claude A =="
sed -n '1,220p' agent_tasks/A_DONE.md

echo
echo "== Claude B =="
sed -n '1,220p' agent_tasks/B_DONE.md

echo
echo "== diff stat =="
git diff --stat
