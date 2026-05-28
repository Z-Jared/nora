#!/usr/bin/env python3
"""Create a desktop zip snapshot after importing this project's Codex sessions."""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path.home() / "Desktop"
BACKUP_DIR = DESKTOP / "nora-agent-snapshots"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "nora_local_ai.egg-info",
}

EXCLUDED_PARTS = {
    "evals/.tmp",
    "data",
    "logs",
    "designs",
}

EXCLUDED_FILES = {
    ".env",
    ".coverage",
    ".DS_Store",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".zip",
}


def rel_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def should_exclude(path: Path) -> bool:
    rel = rel_posix(path)
    parts = set(path.relative_to(ROOT).parts)
    if parts & EXCLUDED_DIRS:
        return True
    if any(rel == excluded or rel.startswith(excluded + "/") for excluded in EXCLUDED_PARTS):
        return True
    if path.name in EXCLUDED_FILES:
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    return False


def import_sessions() -> None:
    subprocess.run([sys.executable, "scripts/import_codex_sessions.py"], cwd=ROOT, check=True)


def create_zip() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = BACKUP_DIR / f"nora-agent-{stamp}.zip"
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(ROOT.rglob("*")):
            if should_exclude(path):
                continue
            if path.is_dir():
                continue
            archive.write(path, arcname=f"nora-agent/{rel_posix(path)}")
    return out_path


def prune_old_snapshots(keep: int = 20) -> None:
    snapshots = sorted(BACKUP_DIR.glob("nora-agent-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in snapshots[keep:]:
        path.unlink()


def main() -> int:
    os.chdir(ROOT)
    import_sessions()
    out_path = create_zip()
    prune_old_snapshots()
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
