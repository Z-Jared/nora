import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mini_agent.code_quality import CodeQualityTools
from mini_agent.shell import ShellRunner


class CodeQualityToolsTests(unittest.TestCase):
    def test_lint_no_ruff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            with patch("mini_agent.code_quality.shutil.which", return_value=None):
                result = tools.lint()
            self.assertEqual(result, "")

    def test_format_no_ruff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            with patch("mini_agent.code_quality.shutil.which", return_value=None):
                result = tools.format_code()
            self.assertEqual(result, "")

    def test_lint_and_fix_no_ruff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            with patch("mini_agent.code_quality.shutil.which", return_value=None):
                result = tools.lint_and_fix()
            self.assertEqual(result, "")

    def test_lint_with_issues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "test.py:1:1: F401 'os' imported but unused"
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.lint()
            self.assertIn("F401", result)

    def test_lint_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.lint()
            self.assertIn("未发现", result)

    def test_format_check_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.format_code(check_only=True)
            self.assertIn("符合规范", result)

    def test_format_with_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "Would reformat test.py"
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.format_code(check_only=True)
            self.assertIn("差异", result)

    def test_format_apply(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "1 file reformatted"
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.format_code(check_only=False)
            self.assertIn("格式化完成", result)

    def test_lint_and_fix_with_issues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Fixed 3 errors"
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.lint_and_fix()
            self.assertIn("已修复", result)

    def test_lint_and_fix_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.lint_and_fix()
            self.assertIn("没有需要修复", result)

    def test_lint_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import subprocess
            tools = CodeQualityTools(Path(tmpdir))
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", side_effect=subprocess.TimeoutExpired("ruff", 30)):
                    result = tools.lint()
            self.assertEqual(result, "")

    def test_lint_truncates_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = CodeQualityTools(Path(tmpdir))
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "x" * 20000
            mock_result.stderr = ""
            with patch("mini_agent.code_quality.shutil.which", return_value="/usr/bin/ruff"):
                with patch("mini_agent.code_quality.subprocess.run", return_value=mock_result):
                    result = tools.lint(max_output_chars=500)
            self.assertLessEqual(len(result), 600)


class ShellRuffTests(unittest.TestCase):
    def test_ruff_check_allowed(self):
        runner = ShellRunner(Path("/tmp"))
        result = runner._parse_allowed_command("ruff check .")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "ruff")

    def test_ruff_format_allowed(self):
        runner = ShellRunner(Path("/tmp"))
        result = runner._parse_allowed_command("ruff format --check .")
        self.assertIsNotNone(result)

    def test_ruff_version_allowed(self):
        runner = ShellRunner(Path("/tmp"))
        result = runner._parse_allowed_command("ruff --version")
        self.assertIsNotNone(result)

    def test_ruff_help_allowed(self):
        runner = ShellRunner(Path("/tmp"))
        result = runner._parse_allowed_command("ruff --help")
        self.assertIsNotNone(result)

    def test_ruff_unknown_subcommand_rejected(self):
        runner = ShellRunner(Path("/tmp"))
        result = runner._parse_allowed_command("ruff server")
        self.assertIsNone(result)

    def test_ruff_clean_rejected(self):
        runner = ShellRunner(Path("/tmp"))
        result = runner._parse_allowed_command("ruff clean")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
