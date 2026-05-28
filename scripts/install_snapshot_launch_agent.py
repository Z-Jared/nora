#!/usr/bin/env python3
"""Install a macOS launchd job for recurring Nora project snapshots."""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.nora.agent.snapshot"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = ROOT / "logs"


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            str(ROOT / "scripts" / "package_project_snapshot.py"),
        ],
        "WorkingDirectory": str(ROOT),
        "StartInterval": 3600,
        "RunAtLoad": True,
        "StandardOutPath": str(LOG_DIR / "snapshot.out.log"),
        "StandardErrorPath": str(LOG_DIR / "snapshot.err.log"),
    }
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_bytes(plistlib.dumps(payload, sort_keys=False))
    subprocess.run(["launchctl", "unload", str(PLIST_PATH)], check=False, capture_output=True)
    subprocess.run(["launchctl", "load", str(PLIST_PATH)], check=True)
    print(f"installed {PLIST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
