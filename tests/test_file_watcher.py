import tempfile
import time
import unittest
from pathlib import Path

from mini_agent.file_watcher import FileWatcher


class FileWatcherTests(unittest.TestCase):
    def test_detects_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            changes = []
            watcher = FileWatcher(root, poll_interval=0.1, debounce_seconds=0.0, callback=lambda fs: changes.extend(fs))
            watcher.start()
            time.sleep(0.15)
            (root / "test.py").write_text("hello", encoding="utf-8")
            time.sleep(0.3)
            watcher.stop()
            self.assertTrue(any("test.py" in str(c) for c in changes))

    def test_detects_modified_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            f = root / "test.py"
            f.write_text("v1", encoding="utf-8")
            changes = []
            watcher = FileWatcher(root, poll_interval=0.1, debounce_seconds=0.0, callback=lambda fs: changes.extend(fs))
            watcher.start()
            time.sleep(0.15)
            f.write_text("v2", encoding="utf-8")
            time.sleep(0.3)
            watcher.stop()
            self.assertTrue(any("test.py" in str(c) for c in changes))

    def test_detects_deleted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            f = root / "test.py"
            f.write_text("v1", encoding="utf-8")
            changes = []
            watcher = FileWatcher(root, poll_interval=0.1, debounce_seconds=0.0, callback=lambda fs: changes.extend(fs))
            watcher.start()
            time.sleep(0.15)
            f.unlink()
            time.sleep(0.3)
            watcher.stop()
            self.assertTrue(any("test.py" in str(c) for c in changes))

    def test_stop_cleanly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(Path(tmpdir), poll_interval=0.1)
            watcher.start()
            time.sleep(0.15)
            watcher.stop()
            self.assertFalse(watcher._running)

    def test_scan_returns_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.py").write_text("a", encoding="utf-8")
            (root / "b.txt").write_text("b", encoding="utf-8")
            watcher = FileWatcher(root, poll_interval=1.0)
            watcher._file_mtimes = watcher._scan_mtimes()
            (root / "c.py").write_text("c", encoding="utf-8")
            changed = watcher.scan()
            self.assertTrue(any("c.py" in str(c) for c in changed))

    def test_excludes_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "mod.py").write_text("x", encoding="utf-8")
            (root / "good.py").write_text("y", encoding="utf-8")
            watcher = FileWatcher(root, poll_interval=1.0)
            mtimes = watcher._scan_mtimes()
            paths = [str(p) for p in mtimes.keys()]
            self.assertFalse(any("__pycache__" in p for p in paths))
            self.assertTrue(any("good.py" in p for p in paths))

    def test_include_paths_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "a.py").write_text("a", encoding="utf-8")
            (root / "tests" / "b.py").write_text("b", encoding="utf-8")
            watcher = FileWatcher(root, include_paths=["src"], poll_interval=1.0)
            mtimes = watcher._scan_mtimes()
            paths = [str(p) for p in mtimes.keys()]
            self.assertTrue(any("src" in p for p in paths))
            self.assertFalse(any("tests" in p for p in paths))

    def test_ignores_non_text_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "image.png").write_bytes(b"\x89PNG")
            (root / "code.py").write_text("x", encoding="utf-8")
            watcher = FileWatcher(root, poll_interval=1.0)
            mtimes = watcher._scan_mtimes()
            paths = [str(p) for p in mtimes.keys()]
            self.assertFalse(any(".png" in p for p in paths))
            self.assertTrue(any(".py" in p for p in paths))

    def test_debounce(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            call_count = [0]
            def callback(files):
                call_count[0] += 1
            watcher = FileWatcher(root, poll_interval=0.05, debounce_seconds=0.5, callback=callback)
            watcher.start()
            # Rapid changes
            for i in range(5):
                (root / f"f{i}.py").write_text(str(i), encoding="utf-8")
                time.sleep(0.08)
            time.sleep(0.6)
            watcher.stop()
            # Should have debounced to fewer calls than 5
            self.assertLessEqual(call_count[0], 3)

    def test_no_callback_no_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            watcher = FileWatcher(root, poll_interval=0.1, debounce_seconds=0.0, callback=None)
            watcher.start()
            (root / "test.py").write_text("x", encoding="utf-8")
            time.sleep(0.3)
            watcher.stop()

    def test_rag_file_snapshot(self):
        from mini_agent.rag import ProjectRAG
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.py").write_text("hello", encoding="utf-8")
            rag = ProjectRAG(root)
            snap = rag.file_snapshot()
            self.assertTrue(any("a.py" in k for k in snap.keys()))

    def test_rag_is_stale(self):
        from mini_agent.rag import ProjectRAG
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.py").write_text("v1", encoding="utf-8")
            rag = ProjectRAG(root)
            snap = rag.file_snapshot()
            self.assertFalse(rag.is_stale(snap))
            time.sleep(0.05)
            (root / "a.py").write_text("v2", encoding="utf-8")
            self.assertTrue(rag.is_stale(snap))


if __name__ == "__main__":
    unittest.main()
