#!/usr/bin/env bash
set -euo pipefail

worker="${1:-}"
if [[ "$worker" != "A" && "$worker" != "B" ]]; then
  echo "Usage: agent_tasks/notify_codex.sh A|B" >&2
  exit 2
fi

cd "$(dirname "$0")/.."

done_file="agent_tasks/${worker}_DONE.md"
if [[ ! -f "$done_file" ]]; then
  echo "Missing $done_file" >&2
  exit 1
fi

status_line="$(grep -m 1 '^Status:' "$done_file" || true)"
timestamp="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

{
  echo "## ${timestamp} Claude ${worker}"
  echo
  echo "${status_line:-Status: unknown}"
  echo
  echo "Review file: ${done_file}"
  echo
} >> agent_tasks/PM_INBOX.md

echo "Notified Codex PM via agent_tasks/PM_INBOX.md"
