import shlex
import subprocess
from pathlib import Path
from typing import Callable, Optional

from mini_agent.tools_common import confirm_in_terminal


SHELL_OPERATORS = {"|", ";", "&", "&&", "||", "`", "$", ">", "<"}
DANGEROUS_COMMANDS = {
    "rm",
    "sudo",
    "chmod",
    "chown",
    "mv",
    "cp",
    "git",
    "curl",
    "wget",
    "bash",
    "sh",
    "zsh",
    "pip",
    "pip3",
}


class ShellRunner:
    def __init__(
        self,
        root: Path,
        confirm_action: Optional[Callable[[str], bool]] = None,
        timeout_seconds: int = 20,
        require_confirmation: bool = True,
    ):
        self.root = root.resolve()
        self.confirm_action = confirm_action or confirm_in_terminal
        self.timeout_seconds = timeout_seconds
        self.require_confirmation = require_confirmation

    def run(self, command: str, reason: str = "") -> str:
        parsed = self._parse_allowed_command(command)
        if not parsed:
            return "拒绝执行: 命令不在安全白名单内。"

        if self.require_confirmation:
            prompt = self._confirmation_prompt(command, reason)
            if not self.confirm_action(prompt):
                return "已取消执行。"

        try:
            completed = subprocess.run(
                parsed,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                input="exit\n" if parsed == ["python3", "main.py"] else None,
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout or ""
            stderr = error.stderr or ""
            return self._format_result("timeout", stdout, stderr)
        except OSError as error:
            return f"执行失败: {error}"

        return self._format_result(
            str(completed.returncode),
            completed.stdout,
            completed.stderr,
        )

    def _parse_allowed_command(self, command: str) -> Optional[list[str]]:
        if any(ord(c) < 32 for c in command if c not in ("\t",)):
            return None

        if any(operator in command for operator in SHELL_OPERATORS):
            return None

        try:
            parts = shlex.split(command)
        except ValueError:
            return None

        if not parts or parts[0] in DANGEROUS_COMMANDS:
            return None

        if parts == ["pwd"]:
            return parts

        if parts[0] == "ls":
            return parts if self._paths_are_safe(parts[1:]) else None

        if parts[0] == "find":
            return parts if self._is_safe_find(parts) else None

        if parts[0] == "rg":
            return self._safe_rg(parts)

        if parts[:5] == ["python3", "-m", "unittest", "discover", "-s"]:
            return parts if len(parts) == 6 and self._path_is_safe(parts[5]) else None

        if parts[:3] == ["python3", "-m", "py_compile"]:
            return parts if len(parts) > 3 and self._paths_are_safe(parts[3:]) else None

        if parts[0] == "ruff":
            return self._safe_ruff(parts)

        if parts == ["python3", "main.py"]:
            return parts

        return None

    def _safe_ruff(self, parts: list[str]) -> Optional[list[str]]:
        allowed_subcommands = {"check", "format", "--version", "--help"}
        if len(parts) < 2 or parts[1] not in allowed_subcommands:
            return None
        if not self._paths_are_safe(parts[2:]):
            return None
        return parts

    def _safe_rg(self, parts: list[str]) -> Optional[list[str]]:
        rejected_flags = {"-uu", "--hidden", "--no-ignore", "--files"}
        if any(part in rejected_flags for part in parts):
            return None

        safe_globs = [
            "--glob",
            "!.env",
            "--glob",
            "!data/**",
            "--glob",
            "!.git/**",
            "--glob",
            "!logs/**",
        ]
        return parts + safe_globs

    def _is_safe_find(self, parts: list[str]) -> bool:
        if len(parts) < 2 or not self._path_is_safe(parts[1]):
            return False

        allowed = {"find", ".", "-maxdepth", "-type", "f", "d", "-name", "-not", "-path", "-print"}
        return all(part in allowed or part.isdigit() or "*" in part for part in parts)

    def _paths_are_safe(self, parts: list[str]) -> bool:
        return all(part.startswith("-") or self._path_is_safe(part) for part in parts)

    def _path_is_safe(self, path: str) -> bool:
        try:
            target = (self.root / path).resolve()
            target.relative_to(self.root)
        except (OSError, ValueError):
            return False

        return True

    def _confirmation_prompt(self, command: str, reason: str) -> str:
        reason_text = reason.strip() or "未提供"
        return f"执行命令: {command}\n原因: {reason_text}\n是否继续? [y/N]: "

    def _format_result(self, exit_code: str, stdout: str, stderr: str) -> str:
        return "\n".join(
            [
                f"exit_code: {exit_code}",
                "stdout:",
                (stdout or "").strip(),
                "stderr:",
                (stderr or "").strip(),
            ]
        ).strip()
