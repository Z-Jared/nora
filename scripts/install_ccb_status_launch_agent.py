#!/usr/bin/env python3
"""Install a macOS launchd job for recurring CCB status checks."""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.nora.agent.ccb.status"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "Nora"
HELPER_PATH = APP_SUPPORT_DIR / "ccb-status-watch.sh"
LOG_DIR = Path.home() / "Library" / "Logs" / "Nora"


def main() -> int:
    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    HELPER_PATH.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail

ROOT="{ROOT}"
CCB_BIN="${{CCB_BIN:-/Users/mac/.local/bin/ccb}}"

cd "$ROOT"

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
""",
        encoding="utf-8",
    )
    HELPER_PATH.chmod(0o755)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [
            "/bin/bash",
            str(HELPER_PATH),
        ],
        "StartInterval": 600,
        "RunAtLoad": True,
        "StandardOutPath": str(LOG_DIR / "ccb-status.out.log"),
        "StandardErrorPath": str(LOG_DIR / "ccb-status.err.log"),
    }
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_bytes(plistlib.dumps(payload, sort_keys=False))
    subprocess.run(["/bin/launchctl", "unload", str(PLIST_PATH)], check=False, capture_output=True)
    subprocess.run(["/bin/launchctl", "load", str(PLIST_PATH)], check=True)
    print(f"installed {PLIST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
