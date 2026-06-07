import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mini_agent.diagnostics import Diagnostics, _summary


class DiagnoseTestFailureTests(unittest.TestCase):
    def test_empty_output(self):
        diag = Diagnostics(Path("/tmp"))

        result = diag.diagnose_test_failure("")

        self.assertIn("没有可诊断", result)

    def test_no_failures_found(self):
        diag = Diagnostics(Path("/tmp"))
        output = "Ran 10 tests OK"

        result = diag.diagnose_test_failure(output)

        self.assertIn("未发现", result)

    def test_extracts_failure_lines(self):
        diag = Diagnostics(Path("/tmp"))
        output = (
            "test_stuff ... FAIL: test_login\n"
            "Traceback (most recent call last):\n"
            '  File "tests/test_login.py", line 42\n'
            "AssertionError: expected True\n"
        )

        result = diag.diagnose_test_failure(output)

        self.assertIn("FAIL:", result)
        self.assertIn("Traceback", result)
        self.assertIn("line 42", result)
        self.assertIn("AssertionError", result)
        self.assertIn("测试失败诊断", result)

    def test_extracts_error_lines(self):
        diag = Diagnostics(Path("/tmp"))
        output = "ERROR: test_import\nImportError: module not found\n"

        result = diag.diagnose_test_failure(output)

        self.assertIn("ERROR:", result)

    def test_limits_output_length(self):
        diag = Diagnostics(Path("/tmp"))
        long_output = "FAIL: test\n" * 1000

        result = diag.diagnose_test_failure(long_output, max_chars=500)

        self.assertLessEqual(len(result), 500)


class SummaryTests(unittest.TestCase):
    def test_ok_summary(self):
        output = "Ran 10 tests in 0.5s\nOK"

        result = _summary(output, 0)

        self.assertEqual(result, "OK")

    def test_failed_summary(self):
        output = "Ran 10 tests in 0.5s\nFAILED (failures=2)"

        result = _summary(output, 1)

        self.assertIn("FAILED", result)

    def test_no_recognized_line(self):
        output = "some random output"

        result = _summary(output, 0)

        self.assertEqual(result, "测试通过")

    def test_no_recognized_line_with_failure(self):
        output = "some random output"

        result = _summary(output, 1)

        self.assertEqual(result, "测试失败")


class RunTestsEdgeCasesTests(unittest.TestCase):
    def test_rejects_non_whitelist_command(self):
        diag = Diagnostics(Path("/tmp"))

        result = diag.run_tests(command="rm -rf /")

        self.assertIn("拒绝执行", result)

    def test_rejects_modified_command(self):
        diag = Diagnostics(Path("/tmp"))

        result = diag.run_tests(command="python3 -m unittest discover -s tests -v")

        self.assertIn("拒绝执行", result)

    @patch("mini_agent.diagnostics.subprocess.run")
    def test_runs_tty_eval_whitelist_command(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["python3", "evals/run_evals.py", "--filter", "tty_"],
            returncode=0,
            stdout="616 passed, 0 failed\n",
            stderr="",
        )
        diag = Diagnostics(Path("/tmp"))

        result = diag.run_tests(command="python3 evals/run_evals.py --filter tty_")

        self.assertIn("exit_code: 0", result)
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp").resolve())
        self.assertEqual(
            mock_run.call_args.args[0],
            ["python3", "evals/run_evals.py", "--filter", "tty_"],
        )

    @patch("mini_agent.diagnostics.subprocess.run")
    def test_runs_diff_check_whitelist_command(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "diff", "--check"],
            returncode=0,
            stdout="",
            stderr="",
        )
        diag = Diagnostics(Path("/tmp"))

        result = diag.run_tests(command="git diff --check")

        self.assertIn("exit_code: 0", result)
        self.assertEqual(mock_run.call_args.args[0], ["git", "diff", "--check"])

    @patch("mini_agent.diagnostics.subprocess.run")
    def test_handles_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=60, output="partial", stderr="err")

        diag = Diagnostics(Path("/tmp"), timeout_seconds=10)

        result = diag.run_tests()

        self.assertIn("timeout", result)

    @patch("mini_agent.diagnostics.subprocess.run")
    def test_handles_os_error(self, mock_run):
        mock_run.side_effect = OSError("no such file")

        diag = Diagnostics(Path("/tmp"))

        result = diag.run_tests()

        self.assertIn("执行失败", result)

    @patch("mini_agent.diagnostics.subprocess.run")
    def test_successful_test_run(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Ran 5 tests in 0.1s\nOK"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        diag = Diagnostics(Path("/tmp"))

        result = diag.run_tests()

        self.assertIn("exit_code: 0", result)
        self.assertIn("OK", result)


if __name__ == "__main__":
    unittest.main()
