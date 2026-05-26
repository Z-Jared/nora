import tempfile
import unittest
from pathlib import Path

from mini_agent.tools import WorkspaceFiles


class WorkspaceFilesTests(unittest.TestCase):
    def test_reads_text_file_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs").mkdir()
            (root / "docs" / "note.txt").write_text("hello", encoding="utf-8")

            files = WorkspaceFiles(root)

            self.assertEqual(files.read("docs/note.txt"), "hello")

    def test_rejects_paths_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir))

            self.assertIn("拒绝读取", files.read("../secret.txt"))

    def test_rejects_env_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env").write_text("LLM_API_KEY=secret", encoding="utf-8")

            files = WorkspaceFiles(root)

            self.assertIn("拒绝读取", files.read(".env"))

    def test_lists_workspace_files_without_sensitive_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / ".env").write_text("secret", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "notes.txt").write_text("private note", encoding="utf-8")

            files = WorkspaceFiles(root)

            listing = files.list(max_files=10)

        self.assertIn("README.md", listing)
        self.assertNotIn(".env", listing)
        self.assertNotIn("data/notes.txt", listing)

    def test_write_file_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root, confirm_action=lambda prompt: False)

            result = files.write("docs/new.md", "hello", reason="test")

        self.assertIn("已取消", result)
        self.assertFalse((root / "docs" / "new.md").exists())

    def test_writes_file_inside_workspace_when_confirmed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)

            result = files.write("docs/new.md", "hello", reason="test")

            self.assertIn("已写入文件", result)
            self.assertEqual((root / "docs" / "new.md").read_text(encoding="utf-8"), "hello")

    def test_write_rejects_sensitive_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda prompt: True)

            result = files.write(".env", "LLM_API_KEY=secret", reason="test")

        self.assertIn("拒绝写入", result)

    def test_replace_file_text_when_confirmed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "README.md"
            target.write_text("hello old", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)

            result = files.replace("README.md", "old", "new", reason="test")

            self.assertIn("已修改文件", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello new")

    def test_replace_file_text_requires_existing_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "README.md"
            target.write_text("hello", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)

            result = files.replace("README.md", "missing", "new", reason="test")

            self.assertIn("没有找到要替换的文本", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello")

    def test_preview_write_new_file_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root)

            result = files.preview_write("docs/new.md", "hello\n")

            self.assertIn("--- a/docs/new.md", result)
            self.assertIn("+++ b/docs/new.md", result)
            self.assertIn("+hello", result)
            self.assertFalse((root / "docs" / "new.md").exists())

    def test_preview_replace_does_not_modify_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "README.md"
            target.write_text("hello old\n", encoding="utf-8")
            files = WorkspaceFiles(root)

            result = files.preview_replace("README.md", "old", "new")

            self.assertIn("-hello old", result)
            self.assertIn("+hello new", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello old\n")

    def test_preview_replace_requires_existing_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("hello", encoding="utf-8")
            files = WorkspaceFiles(root)

            result = files.preview_replace("README.md", "missing", "new")

            self.assertIn("没有找到要替换的文本", result)

    def test_preview_rejects_sensitive_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir))

            result = files.preview_write(".env", "secret")

        self.assertIn("拒绝预览", result)

    def test_apply_unified_diff_updates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "README.md"
            target.write_text("hello old\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
            patch = "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-hello old\n+hello new\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("已应用 patch", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello new\n")

    def test_apply_unified_diff_rejects_context_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "README.md"
            target.write_text("hello current\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
            patch = "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-hello old\n+hello new\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("不匹配", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello current\n")

    def test_apply_unified_diff_rejects_sensitive_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda prompt: True)
            patch = "--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-old\n+new\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("拒绝应用 patch", result)

    def test_preview_multi_file_patch_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("old a\n", encoding="utf-8")
            (root / "b.txt").write_text("old b\n", encoding="utf-8")
            files = WorkspaceFiles(root)
            patch = (
                "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old a\n+new a\n"
                "--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-old b\n+new b\n"
            )

            result = files.preview_multi_file_patch(patch)

            self.assertIn("- a.txt", result)
            self.assertIn("- b.txt", result)
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "old a\n")
            self.assertEqual((root / "b.txt").read_text(encoding="utf-8"), "old b\n")

    def test_apply_multi_file_patch_updates_all_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("old a\n", encoding="utf-8")
            (root / "b.txt").write_text("old b\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
            patch = (
                "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old a\n+new a\n"
                "--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-old b\n+new b\n"
            )

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("已应用多文件 patch", result)
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "new a\n")
            self.assertEqual((root / "b.txt").read_text(encoding="utf-8"), "new b\n")

    def test_multi_file_patch_rejects_partial_failure_without_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("old a\n", encoding="utf-8")
            (root / "b.txt").write_text("old b\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
            patch = (
                "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old a\n+new a\n"
                "--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-missing\n+new b\n"
            )

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("上下文不匹配", result)
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "old a\n")
            self.assertEqual((root / "b.txt").read_text(encoding="utf-8"), "old b\n")

    def test_multi_file_patch_rejects_sensitive_duplicate_and_dev_null(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("old\n", encoding="utf-8")
            (root / "logs").mkdir()
            (root / "logs" / "a.txt").write_text("old\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
            sensitive = "--- a/logs/a.txt\n+++ b/logs/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
            duplicate = (
                "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
                "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
            )
            dev_null = "--- a/dev.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n"

            self.assertIn("拒绝应用", files.apply_multi_file_patch(sensitive, reason="test"))
            self.assertIn("同一个文件", files.apply_multi_file_patch(duplicate, reason="test"))
            self.assertIn("不支持创建或删除", files.apply_multi_file_patch(dev_null, reason="test"))
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_multi_file_patch_cancel_confirmation_does_not_modify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("old\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: False)
            patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("已取消", result)
            self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_replace_in_file_replaces_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "code.py").write_text("def foo():\n    pass\n", encoding="utf-8")
            files = WorkspaceFiles(root, require_confirmation=False)

            result = files.replace("code.py", "pass", "return 42")

            self.assertIn("已修改文件", result)
            self.assertEqual((root / "code.py").read_text(encoding="utf-8"), "def foo():\n    return 42\n")

    def test_replace_rejects_missing_old_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "code.py").write_text("hello", encoding="utf-8")
            files = WorkspaceFiles(root, require_confirmation=False)

            result = files.replace("code.py", "nonexistent", "world")

            self.assertIn("没有找到要替换的文本", result)

    def test_list_excludes_sensitive_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("x = 1", encoding="utf-8")
            (root / ".env").write_text("SECRET=1", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "state.json").write_text("{}", encoding="utf-8")
            (root / ".git").mkdir()
            (root / "logs").mkdir()
            files = WorkspaceFiles(root)

            result = files.list()

            self.assertIn("src/main.py", result)
            self.assertNotIn(".env", result)
            self.assertNotIn("data/", result)
            self.assertNotIn(".git/", result)
            self.assertNotIn("logs/", result)

    def test_preview_write_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root, require_confirmation=False)

            result = files.preview_write("new.txt", "content")

            self.assertIn("new.txt", result)
            self.assertFalse((root / "new.txt").exists())


if __name__ == "__main__":
    unittest.main()
