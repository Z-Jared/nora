import re
import subprocess
from pathlib import Path


ALLOWED_TEST_COMMAND = "python3 -m unittest discover -s tests"


class Diagnostics:
    def __init__(self, root: Path, timeout_seconds: int = 60):
        self.root = root.resolve()
        self.timeout_seconds = timeout_seconds

    def run_tests(self, command: str = ALLOWED_TEST_COMMAND, max_output_chars: int = 12000, reason: str = "") -> str:
        command = command.strip() or ALLOWED_TEST_COMMAND
        if command != ALLOWED_TEST_COMMAND:
            return "拒绝执行测试: 命令不在测试白名单内。"

        max_output_chars = max(500, min(max_output_chars, 50000))
        try:
            completed = subprocess.run(
                command.split(),
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            output = "\n".join(part for part in (error.stdout, error.stderr) if part)
            return f"exit_code: timeout\nsummary: 测试超时\n{output[:max_output_chars]}".strip()
        except OSError as error:
            return f"测试执行失败: {error}"

        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
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
