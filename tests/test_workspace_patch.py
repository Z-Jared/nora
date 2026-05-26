import tempfile
import unittest
from pathlib import Path

from mini_agent.toolkits.workspace import WorkspaceFiles


class ParseMultiFilePatchEdgeCasesTests(unittest.TestCase):
    def test_rejects_rename_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "rename from old.py\nrename to new.py\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("不支持创建、删除或重命名", result)

    def test_rejects_new_file_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "new file mode 100644\n--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+x\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("不支持创建、删除或重命名", result)

    def test_rejects_deleted_file_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "deleted file mode 100644\n--- a/old.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("不支持创建、删除或重命名", result)

    def test_rejects_missing_plus_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "--- a/file.txt\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("缺少 +++ 文件头", result)

    def test_rejects_rename_different_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "old.txt").write_text("content\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            patch = "--- a/old.txt\n+++ b/new.txt\n@@ -1 +1 @@\n-content\n+new content\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("不支持重命名", result)

    def test_rejects_no_hunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").write_text("content\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            patch = "--- a/file.txt\n+++ b/file.txt\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("没有可应用的 hunk", result)

    def test_rejects_invalid_hunk_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").write_text("content\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            patch = "--- a/file.txt\n+++ b/file.txt\ninvalid hunk header\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("没有可应用的 hunk", result)

    def test_rejects_empty_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)

            result = files.apply_multi_file_patch("", reason="test")

            self.assertIn("patch 不能为空", result)

    def test_rejects_patch_missing_file_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "@@ -1 +1 @@\n-old\n+new\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("缺少文件头", result)

    def test_rejects_single_file_patch_via_multi_apply(self):
        """apply_unified_diff only accepts single file patches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("old\n", encoding="utf-8")
            (root / "b.txt").write_text("old\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            patch = (
                "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new a\n"
                "--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-old\n+new b\n"
            )

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("只支持单文件 patch", result)

    def test_rejects_hunk_ordering_violation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("a\nb\nc\nd\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            # Second hunk starts before first hunk ends
            patch = (
                "--- a/f.txt\n"
                "+++ b/f.txt\n"
                "@@ -3 +3 @@\n"
                " c\n"
                "-d\n"
                "+D\n"
                "@@ -1 +1 @@\n"
                " a\n"
                "-b\n"
                "+B\n"
            )

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("拒绝", result)

    def test_rejects_output_exceeding_size_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("x\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True, max_file_bytes=50)
            big_content = "y" * 100
            patch = f"--- a/f.txt\n+++ b/f.txt\n@@ -1 +1 @@\n-x\n+{big_content}\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("最大支持", result)

    def test_preview_multi_file_patch_with_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("same\n", encoding="utf-8")
            files = WorkspaceFiles(root)
            patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1 +1 @@\n same\n"

            result = files.preview_multi_file_patch(patch)

            self.assertIn("没有变化", result)

    def test_read_resolves_symlink_outside_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            root.mkdir()
            outside = Path(tmpdir) / "secret.txt"
            outside.write_text("secret", encoding="utf-8")
            link = root / "link.txt"
            link.symlink_to(outside)

            files = WorkspaceFiles(root)

            result = files.read("link.txt")

            self.assertIn("拒绝读取", result)

    def test_read_rejects_not_a_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "subdir").mkdir()

            files = WorkspaceFiles(root)

            result = files.read("subdir")

            self.assertIn("不是文件", result)

    def test_write_rejects_oversized_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), require_confirmation=False, max_file_bytes=50)

            result = files.write("big.txt", "x" * 100)

            self.assertIn("拒绝写入", result)


if __name__ == "__main__":
    unittest.main()
