import re
import subprocess
from pathlib import Path
from typing import Optional

from mini_agent.durable_events import (
    TEST_RUN_BLOCKED,
    TEST_RUN_ERROR,
    TEST_RUN_FINISHED,
    TEST_RUN_STARTED,
)


ALLOWED_TEST_COMMAND = "python3 -m unittest discover -s tests"


class Diagnostics:
    def __init__(self, root: Path, timeout_seconds: int = 60, event_store=None):
        self.root = root.resolve()
        self.timeout_seconds = timeout_seconds
        self.event_store = event_store

    def _record_test_run_event(
        self,
        event_type: str,
        status: str = "",
        exit_code: Optional[int] = None,
        stdout_bytes: int = 0,
        stderr_bytes: int = 0,
        timeout: bool = False,
        error: str = "",
        max_output_chars: Optional[int] = None,
    ) -> None:
        if not self.event_store:
            return
        payload = {
            "command_kind": "unittest_discover",
            "status": status,
            "exit_code": exit_code,
            "timeout": timeout,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "error": error,
        }
        if max_output_chars is not None:
            payload["max_output_chars"] = max_output_chars
        try:
            self.event_store.record(
                event_type=event_type,
                task_id=None,
                source="diagnostics",
                summary=f"{event_type}: unittest_discover",
                severity="info" if event_type in (TEST_RUN_STARTED, TEST_RUN_FINISHED) else "warning",
                payload=payload,
            )
        except Exception:
            pass

    def _byte_len(self, value) -> int:
        if value is None:
            return 0
        if isinstance(value, bytes):
            return len(value)
        return len(str(value).encode("utf-8"))

    def _text(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    def run_tests(self, command: str = ALLOWED_TEST_COMMAND, max_output_chars: int = 12000, reason: str = "") -> str:
        command = command.strip() or ALLOWED_TEST_COMMAND
        if command != ALLOWED_TEST_COMMAND:
            self._record_test_run_event(TEST_RUN_BLOCKED, status="blocked", error="disallowed_command")
            return "拒绝执行测试: 命令不在测试白名单内。"

        max_output_chars = max(500, min(max_output_chars, 50000))
        self._record_test_run_event(TEST_RUN_STARTED, status="started", max_output_chars=max_output_chars)

        try:
            completed = subprocess.run(
                command.split(),
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            stdout = self._text(error.stdout)
            stderr = self._text(error.stderr)
            self._record_test_run_event(
                TEST_RUN_ERROR, status="timeout", timeout=True,
                stdout_bytes=self._byte_len(error.stdout),
                stderr_bytes=self._byte_len(error.stderr),
                error="timeout",
                max_output_chars=max_output_chars,
            )
            output = "\n".join(part for part in (stdout, stderr) if part)
            return f"exit_code: timeout\nsummary: 测试超时\n{output[:max_output_chars]}".strip()
        except OSError:
            self._record_test_run_event(
                TEST_RUN_ERROR,
                status="error",
                error="os_error",
                max_output_chars=max_output_chars,
            )
            return f"测试执行失败: OSError"

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        self._record_test_run_event(
            TEST_RUN_FINISHED, status="finished",
            exit_code=completed.returncode,
            stdout_bytes=self._byte_len(stdout),
            stderr_bytes=self._byte_len(stderr),
            max_output_chars=max_output_chars,
        )

        output = "\n".join(part for part in (stdout, stderr) if part)
        summary = _summary(output, completed.returncode)
        diagnosis = self.diagnose_test_failure(output) if completed.returncode else ""
        sections = [f"exit_code: {completed.returncode}", f"summary: {summary}"]
        if diagnosis:
            sections.append(diagnosis)
        sections.append(output[:max_output_chars].strip())
        return "\n".join(section for section in sections if section).strip()

    def diagnose_test_failure(self, output: str, max_chars: int = 4000) -> str:
        output = output.strip()
        if not output:
            return "没有可诊断的测试输出。"

        max_chars = max(500, min(max_chars, 20000))
        interesting = []
        patterns = (
            r"FAIL: .*",
            r"ERROR: .*",
            r"Traceback \(most recent call last\):",
            r'File "[^"]+", line \d+.*',
            r"AssertionError: .*",
        )
        for line in output.splitlines():
            if any(re.search(pattern, line) for pattern in patterns):
                interesting.append(line)

        if not interesting:
            return "未发现明确的 FAIL、ERROR 或 traceback。"

        return "\n".join(
            [
                "测试失败诊断:",
                *interesting[:40],
                "下一步建议: 先打开上面提到的文件和行号，确认失败断言与最近改动的关系。",
            ]
        )[:max_chars]


def _summary(output: str, exit_code: int) -> str:
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if stripped.startswith("FAILED") or stripped.startswith("OK") or "failed" in stripped.lower():
            return stripped
    return "测试通过" if exit_code == 0 else "测试失败"
