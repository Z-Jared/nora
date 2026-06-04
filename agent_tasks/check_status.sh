#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

CCB_BIN="${CCB_BIN:-/Users/mac/.local/bin/ccb}"

echo "== timestamp =="
date -u +"%Y-%m-%dT%H:%M:%SZ"

echo
echo "== CCB queue =="
if [[ -x "$CCB_BIN" ]]; then
  "$CCB_BIN" queue --detail all
else
  echo "ccb binary not found at $CCB_BIN"
fi

echo
echo "== CCB inbox (pm) =="
if [[ -x "$CCB_BIN" ]]; then
  "$CCB_BIN" pend --inbox --detail pm
else
  echo "ccb binary not found at $CCB_BIN"
fi

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
