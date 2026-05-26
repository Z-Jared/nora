from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from mini_agent.rag import TEXT_EXTENSIONS, TEXT_FILENAMES, DENIED_DIR_NAMES


class FileWatcher:
    """Watches project files for changes using stat-based polling."""

    def __init__(
        self,
        root: Path,
        include_paths: Optional[list[str]] = None,
        exclude_dirs: Optional[set[str]] = None,
        poll_interval: float = 3.0,
        debounce_seconds: float = 5.0,
        callback: Optional[Callable[[list[Path]], None]] = None,
    ):
        self.root = root.resolve()
        self.include_paths = [p.strip().strip("/") for p in (include_paths or []) if p.strip()]
        self.exclude_dirs = DENIED_DIR_NAMES | (exclude_dirs or set())
        self.poll_interval = max(0.5, poll_interval)
        self.debounce_seconds = max(0.0, debounce_seconds)
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._file_mtimes: dict[str, float] = {}
        self._last_callback_time: float = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._file_mtimes = self._scan_mtimes()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.poll_interval + 1)
            self._thread = None
        changed = self._check_changes()
        if changed and self.callback:
            try:
                self.callback(changed)
            except Exception:
                pass

    def scan(self) -> list[Path]:
        changed = self._check_changes()
        return changed

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(self.poll_interval)
            if not self._running:
                break
            changed = self._check_changes()
            if changed and self.callback:
                now = time.monotonic()
                if now - self._last_callback_time >= self.debounce_seconds:
                    self._last_callback_time = now
                    try:
                        self.callback(changed)
                    except Exception:
                        pass

    def _check_changes(self) -> list[Path]:
        current = self._scan_mtimes()
        changed = []
        old_keys = set(self._file_mtimes.keys())
        new_keys = set(current.keys())

        for added in new_keys - old_keys:
            changed.append(Path(added))
        for removed in old_keys - new_keys:
            changed.append(Path(removed))
        for key in old_keys & new_keys:
            if self._file_mtimes[key] != current[key]:
                changed.append(Path(key))

        self._file_mtimes = current
        return changed

    def _scan_mtimes(self) -> dict[str, float]:
        mtimes: dict[str, float] = {}
        try:
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs and not d.startswith(".")]
                rel_dir = os.path.relpath(dirpath, self.root)
                if self.include_paths:
                    top_dir = rel_dir.split(os.sep)[0] if rel_dir != "." else ""
                    if top_dir and top_dir not in self.include_paths:
                        dirnames.clear()
                        continue
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    rel = os.path.relpath(fpath, self.root)
                    if not self._should_watch(fname, rel):
                        continue
                    try:
                        mtimes[fpath] = os.stat(fpath).st_mtime
                    except OSError:
                        pass
        except OSError:
            pass
        return mtimes

    def _should_watch(self, filename: str, rel_path: str) -> bool:
        if filename in DENIED_DIR_NAMES or filename.startswith("."):
            return False
        _, ext = os.path.splitext(filename)
        if ext.lower() in TEXT_EXTENSIONS:
            return True
        if filename in TEXT_FILENAMES:
            return True
        if filename == ".env.example":
            return True
        return False
