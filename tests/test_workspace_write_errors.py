import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mini_agent.toolkits.workspace import WorkspaceFiles


class WriteOSErrorTests(unittest.TestCase):
    def test_write_handles_os_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root, require_confirmation=False)

            with patch.object(Path, "write_text", side_effect=OSError("disk full")):
                result = files.write("test.txt", "content")

            self.assertIn("写入失败", result)


class ReplaceOSErrorTests(unittest.TestCase):
    def test_replace_handles_read_os_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").write_text("old", encoding="utf-8")
            files = WorkspaceFiles(root, require_confirmation=False)

            with patch.object(Path, "read_text", side_effect=OSError("read fail")):
                result = files.replace("file.txt", "old", "new")

            self.assertIn("读取失败", result)


class PreviewEdgeCasesTests(unittest.TestCase):
    def test_preview_write_rejects_oversized_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), max_file_bytes=50)

            result = files.preview_write("test.txt", "x" * 100)

            self.assertIn("拒绝预览", result)
            self.assertIn("最大支持", result)

    def test_preview_replace_rejects_empty_old_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("content", encoding="utf-8")
            files = WorkspaceFiles(root)

            result = files.preview_replace("f.txt", "", "new")

            self.assertIn("old_text 不能为空", result)

    def test_preview_replace_rejects_oversized_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("old", encoding="utf-8")
            files = WorkspaceFiles(root, max_file_bytes=50)

            result = files.preview_replace("f.txt", "old", "x" * 100)

            self.assertIn("拒绝预览", result)

    def test_preview_replace_rejects_read_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("old", encoding="utf-8")
            files = WorkspaceFiles(root)

            with patch.object(Path, "read_text", side_effect=OSError("fail")):
                result = files.preview_replace("f.txt", "old", "new")

            self.assertIn("读取失败", result)

    def test_preview_write_read_error_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("old", encoding="utf-8")
            files = WorkspaceFiles(root)

            with patch.object(Path, "read_text", side_effect=OSError("fail")):
                result = files.preview_write("f.txt", "new")

            self.assertIn("读取失败", result)


class ApplyUnifiedDiffEdgeCasesTests(unittest.TestCase):
    def test_apply_diff_rejects_empty_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)

            result = files.apply_unified_diff("", reason="test")

            self.assertIn("patch 不能为空", result)

    def test_apply_diff_rejects_missing_file_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("old\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            patch = "@@ -1 +1 @@\n-old\n+new\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("缺少文件头", result)

    def test_apply_diff_rejects_missing_plus_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "--- a/f.txt\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("缺少 +++ 文件头", result)

    def test_apply_diff_rejects_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda p: True)
            patch = "--- a/missing.txt\n+++ b/missing.txt\n@@ -1 +1 @@\n-old\n+new\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("文件不存在", result)

    def test_apply_diff_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("same\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: True)
            patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1 +1 @@\n same\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("没有变化", result)

    def test_apply_diff_cancelled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "f.txt").write_text("old\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: False)
            patch = "--- a/f.txt\n+++ b/f.txt\n@@ -1 +1 @@\n-old\n+new\n"

            result = files.apply_unified_diff(patch, reason="test")

            self.assertIn("已取消", result)


class MultiFilePatchConfirmationTests(unittest.TestCase):
    def test_multi_file_patch_cancelled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("old\n", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda p: False)
            patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"

            result = files.apply_multi_file_patch(patch, reason="test")

            self.assertIn("已取消", result)


class ResolveTargetEdgeCasesTests(unittest.TestCase):
    def test_resolve_target_returns_none_for_denied_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".git").mkdir()
            files = WorkspaceFiles(root)

            result = files._resolve_target(".git/config")

            self.assertIsNone(result)

    def test_resolve_target_returns_path_for_valid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "file.txt").write_text("x", encoding="utf-8")
            files = WorkspaceFiles(root)

            result = files._resolve_target("file.txt")

            self.assertIsNotNone(result)
            self.assertTrue(str(result).endswith("file.txt"))


if __name__ == "__main__":
    unittest.main()
