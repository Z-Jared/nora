from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class CodeQualityTools:
    """Formatting and linting tools using ruff."""

    def __init__(self, root: Path, timeout_seconds: int = 30):
        self.root = root.resolve()
        self.timeout_seconds = timeout_seconds

    def lint(self, path: str = "", max_output_chars: int = 8000) -> str:
        args = ["check", "--output-format", "text"]
        if path:
            args.append(path)
        result = self._run_ruff(args)
        if result is None:
            return ""
        output = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if not output and not stderr:
            return "未发现 lint 问题。"
        text = output or stderr
        if len(text) > max_output_chars:
            text = text[:max_output_chars] + "\n...(截断)"
        return text

    def format_code(self, path: str = "", check_only: bool = True) -> str:
        args = ["format"]
        if check_only:
            args.append("--check")
        if path:
            args.append(path)
        result = self._run_ruff(args)
        if result is None:
            return ""
        if result.returncode == 0:
            if check_only:
                return "代码格式已符合规范。"
            return "格式化完成。"
        output = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        text = output or stderr
        if check_only:
            return f"格式差异:\n{text}" if text else "存在格式差异。"
        return f"格式化完成，有变更:\n{text}" if text else "格式化完成。"

    def lint_and_fix(self, path: str = "") -> str:
        args = ["check", "--fix"]
        if path:
            args.append(path)
        result = self._run_ruff(args)
        if result is None:
            return ""
        output = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode == 0:
            if not output:
                return "没有需要修复的 lint 问题。"
            return f"已修复:\n{output}"
        text = output or stderr
        return f"修复结果:\n{text}" if text else "修复完成，部分问题需手动处理。"

    def _run_ruff(self, args: list[str]) -> subprocess.CompletedProcess | None:
        if not shutil.which("ruff"):
            return None
        try:
            return subprocess.run(
                ["ruff"] + args,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return None
        except OSError:
            return None
