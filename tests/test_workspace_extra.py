import tempfile
import unittest
from pathlib import Path

from mini_agent.toolkits.workspace import WorkspaceFiles


class WorkspaceReadEdgeCasesTests(unittest.TestCase):
    def test_read_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir))

            result = files.read("nonexistent.txt")

            self.assertIn("文件不存在", result)

    def test_read_non_utf8_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "binary.bin").write_bytes(b"\x80\x81\x82\x83")

            files = WorkspaceFiles(root)

            result = files.read("binary.bin")

            self.assertIn("UTF-8", result)

    def test_read_file_exceeding_size_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "big.txt").write_text("x" * 1000, encoding="utf-8")

            files = WorkspaceFiles(root, max_file_bytes=100)

            result = files.read("big.txt")

            self.assertIn("文件过大", result)

    def test_read_resolves_path_safely(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "sub").mkdir()
            (root / "sub" / "file.txt").write_text("hello", encoding="utf-8")

            files = WorkspaceFiles(root)

            result = files.read("sub/file.txt")

            self.assertEqual(result, "hello")


class WorkspaceListEdgeCasesTests(unittest.TestCase):
    def test_list_caps_at_max_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for i in range(10):
                (root / f"file_{i}.txt").write_text(str(i), encoding="utf-8")

            files = WorkspaceFiles(root)

            result = files.list(max_files=3)

            lines = result.strip().split("\n")
            self.assertEqual(len(lines), 3)

    def test_list_max_files_capped_at_200(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for i in range(5):
                (root / f"f{i}.txt").write_text("", encoding="utf-8")

            files = WorkspaceFiles(root)

            result = files.list(max_files=999)

            lines = result.strip().split("\n")
            self.assertLessEqual(len(lines), 200)

    def test_list_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir))

            result = files.list()

            self.assertIn("没有找到", result)


class WorkspaceWriteEdgeCasesTests(unittest.TestCase):
    def test_write_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root, require_confirmation=False)

            result = files.write("deep/nested/dir/file.txt", "content")

            self.assertIn("已写入文件", result)
            self.assertEqual((root / "deep" / "nested" / "dir" / "file.txt").read_text(), "content")

    def test_write_rejects_path_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), require_confirmation=False)

            result = files.write("../escape.txt", "content")

            self.assertIn("拒绝写入", result)

    def test_write_rejects_data_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), require_confirmation=False)

            result = files.write("data/state.json", "{}")

            self.assertIn("拒绝写入", result)

    def test_write_rejects_git_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), require_confirmation=False)

            result = files.write(".git/config", "data")

            self.assertIn("拒绝写入", result)


class WorkspaceReplaceEdgeCasesTests(unittest.TestCase):
    def test_replace_rejects_sensitive_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env.local").write_text("key=val", encoding="utf-8")
            files = WorkspaceFiles(root, require_confirmation=False)

            result = files.replace(".env.local", "key", "newkey")

            self.assertIn("拒绝修改", result)

    def test_replace_rejects_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), require_confirmation=False)

            result = files.replace("missing.txt", "old", "new")

            self.assertIn("文件不存在", result)

    def test_replace_single_occurrence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "code.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
            files = WorkspaceFiles(root, require_confirmation=False)

            result = files.replace("code.py", "a = 1", "a = 42")

            self.assertIn("已修改文件", result)
            self.assertEqual((root / "code.py").read_text(), "a = 42\nb = 2\n")


class WorkspaceDiffEdgeCasesTests(unittest.TestCase):
    def test_preview_write_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").write_text("old content\n", encoding="utf-8")
            files = WorkspaceFiles(root)

            result = files.preview_write("file.txt", "new content\n")

            self.assertIn("-old content", result)
            self.assertIn("+new content", result)

    def test_apply_unified_diff_multi_hunk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            patch = (
                "--- a/file.txt\n"
                "+++ b/file.txt\n"
                "@@ -1 +1 @@\n"
                "-line1\n"
                "+LINE1\n"
                "@@ -3 +3 @@\n"
                "-line3\n"
                "+LINE3\n"
            )

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("已应用 patch", result)
            content = (root / "file.txt").read_text()
            self.assertIn("LINE1", content)
            self.assertIn("LINE3", content)

    def test_apply_unified_diff_rejects_create(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1 @@\n+new\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("不支持创建或删除", result)


if __name__ == "__main__":
    unittest.main()
