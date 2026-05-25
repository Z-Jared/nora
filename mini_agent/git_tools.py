import re
import subprocess
from pathlib import Path
from typing import Union


DENIED_FILE_NAMES = {".env", ".env.local", ".env.production"}
DENIED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "data", "logs"}
MAX_COMMIT_MESSAGE_CHARS = 500
BRANCH_DENIED_PATTERN = re.compile(r"[\s\x00-\x1f~^:?*\[\\]")


class GitTools:
    def __init__(self, root: Path, timeout_seconds: int = 10):
        self.root = root.resolve()
        self.timeout_seconds = timeout_seconds

    def status(self) -> str:
        return self._run(["git", "status", "--short"])

    def diff(self, path: str = "", max_chars: int = 12000) -> str:
        max_chars = max(200, min(max_chars, 50000))
        command = ["git", "diff", "--"]
        if path.strip():
            target = self._safe_workspace_path(path)
            if not target:
                return "拒绝查看 diff: 路径必须位于项目目录内的非敏感路径。"
            command.append(target)
        else:
            sensitive = self._changed_sensitive_paths(cached=False)
            if sensitive:
                return f"拒绝查看 diff: 包含敏感路径 {sensitive}。请指定非敏感路径查看。"
        return self._run(command, max_chars=max_chars)

    def log(self, max_count: int = 5) -> str:
        max_count = max(1, min(max_count, 50))
        return self._run(["git", "log", "--oneline", "-n", str(max_count)])

    def current_branch(self) -> str:
        return self._run(["git", "branch", "--show-current"])

    def branches(self) -> str:
        return self._run(["git", "branch", "--list"])

    def staged_diff(self, max_chars: int = 12000) -> str:
        max_chars = max(200, min(max_chars, 50000))
        sensitive = self._changed_sensitive_paths(cached=True)
        if sensitive:
            return f"拒绝查看 staged diff: 包含敏感路径 {sensitive}。"
        return self._run(["git", "diff", "--cached", "--"], max_chars=max_chars)

    def summarize_changes(self, max_chars: int = 12000) -> str:
        max_chars = max(500, min(max_chars, 50000))
        sections = [
            ("branch", self.current_branch()),
            ("status", self.status()),
            ("staged stat", self._run(["git", "diff", "--cached", "--stat", "--"])),
            ("unstaged stat", self._run(["git", "diff", "--stat", "--"])),
            ("recent commits", self.log(max_count=5)),
        ]
        output = "\n\n".join(f"## {title}\n{content}" for title, content in sections)
        return output[:max_chars]

    def review_staged_diff(self, max_chars: int = 12000) -> str:
        max_chars = max(500, min(max_chars, 50000))
        names = self._run(["git", "diff", "--cached", "--name-status", "--"])
        if names == "没有 Git 输出。":
            return "没有 staged diff。"
        stat = self._run(["git", "diff", "--cached", "--stat", "--"])
        sensitive = _sensitive_path_warnings(names)
        lines = [
            "staged diff 审查:",
            "## files",
            names,
            "## stat",
            stat,
            "## checks",
            "- staged diff: present",
            f"- sensitive paths: {sensitive or '未发现明显敏感路径'}",
        ]
        return "\n".join(lines)[:max_chars]

    def check_before_commit(self, max_chars: int = 12000) -> str:
        max_chars = max(500, min(max_chars, 50000))
        staged = self._run(["git", "diff", "--cached", "--name-status", "--"])
        unstaged = self._run(["git", "diff", "--name-status", "--"])
        untracked = self._run(["git", "ls-files", "--others", "--exclude-standard"])
        staged_present = staged != "没有 Git 输出。"
        unstaged_present = unstaged != "没有 Git 输出。" or untracked != "没有 Git 输出。"
        sensitive = _sensitive_path_warnings("\n".join([staged, unstaged, untracked]))
        lines = [
            "提交前检查:",
            f"- staged changes: {'有' if staged_present else '无'}",
            f"- unstaged/untracked changes: {'有' if unstaged_present else '无'}",
            f"- sensitive paths: {sensitive or '未发现明显敏感路径'}",
        ]
        if not staged_present:
            lines.append("建议: 先显式暂存需要提交的路径。")
        elif unstaged_present:
            lines.append("建议: 检查未暂存/未跟踪文件，确认是否需要一起提交或保留。")
        else:
            lines.append("建议: 可查看 staged diff，确认后再提交。")
        return "\n".join(lines)[:max_chars]

    def create_branch(self, name: str, reason: str = "") -> str:
        name = name.strip()
        validation = self._validate_branch_name(name)
        if validation:
            return validation
        return self._run(["git", "branch", name])

    def stage_paths(self, paths: list[str], reason: str = "") -> str:
        safe_paths = self._safe_paths(paths, "暂存")
        if isinstance(safe_paths, str):
            return safe_paths
        result = self._run(["git", "add", "--", *safe_paths])
        if result.startswith("Git 命令失败"):
            return result
        status = self.status()
        return "已暂存路径。\n" + status

    def unstage_paths(self, paths: list[str], reason: str = "") -> str:
        safe_paths = self._safe_paths(paths, "取消暂存")
        if isinstance(safe_paths, str):
            return safe_paths
        result = self._run(["git", "restore", "--staged", "--", *safe_paths])
        if result.startswith("Git 命令失败"):
            return result
        status = self.status()
        return "已取消暂存路径。\n" + status

    def commit_staged(self, message: str, reason: str = "") -> str:
        message = message.strip()
        if not message:
            return "拒绝提交: commit message 不能为空。"
        if len(message) > MAX_COMMIT_MESSAGE_CHARS:
            return f"拒绝提交: commit message 最多 {MAX_COMMIT_MESSAGE_CHARS} 字符。"

        staged = self._run_raw(["git", "diff", "--cached", "--quiet"])
        if isinstance(staged, str):
            return staged
        if staged.returncode == 0:
            return "拒绝提交: 没有已暂存的改动。"
        if staged.returncode != 1:
            return self._format_completed(staged)

        sensitive = self._changed_sensitive_paths(cached=True)
        if sensitive:
            return f"拒绝提交: staged changes 包含敏感路径 {sensitive}。请先取消暂存。"

        result = self._run(["git", "commit", "-m", message])
        if result.startswith("Git 命令失败"):
            return result
        latest = self._run(["git", "log", "--oneline", "-n", "1"])
        return "已创建本地提交。\n" + latest

    def _safe_relative_path(self, path: str) -> str:
        try:
            target = (self.root / path).resolve()
            relative = target.relative_to(self.root)
        except (OSError, ValueError):
            return ""
        return relative.as_posix()

    def _changed_sensitive_paths(self, cached: bool) -> str:
        command = ["git", "diff"]
        if cached:
            command.append("--cached")
        command.extend(["--name-status", "--"])
        changed = self._run(command)
        if changed == "没有 Git 输出。" or changed.startswith("Git 命令"):
            return ""
        return _sensitive_path_warnings(changed)

    def _safe_paths(self, paths: list[str], action: str) -> Union[list[str], str]:
        if not isinstance(paths, list) or not paths:
            return f"拒绝{action}: paths 不能为空。"
        safe_paths = []
        for path in paths:
            if not isinstance(path, str) or not path.strip():
                return f"拒绝{action}: path 不能为空。"
            if path.strip() in {".", "*"}:
                return f"拒绝{action}: 必须显式指定文件路径，不能使用 {path.strip()}。"
            safe_path = self._safe_workspace_path(path)
            if not safe_path:
                return f"拒绝{action}: 只能操作项目目录内的非敏感路径。"
            safe_paths.append(safe_path)
        return safe_paths

    def _safe_workspace_path(self, path: str) -> str:
        raw = path.strip()
        if Path(raw).is_absolute():
            return ""
        try:
            target = (self.root / raw).resolve()
            relative = target.relative_to(self.root)
        except (OSError, ValueError):
            return ""
        if not relative.parts:
            return ""
        if any(part in DENIED_DIR_NAMES for part in relative.parts):
            return ""
        if relative.name in DENIED_FILE_NAMES:
            return ""
        return relative.as_posix()

    def _validate_branch_name(self, name: str) -> str:
        if not name:
            return "拒绝创建分支: 分支名不能为空。"
        if name.startswith("-"):
            return "拒绝创建分支: 分支名不能以 - 开头。"
        if ".." in name or "@{" in name:
            return "拒绝创建分支: 分支名包含非法片段。"
        if name.endswith(".") or name.endswith(".lock"):
            return "拒绝创建分支: 分支名结尾非法。"
        if BRANCH_DENIED_PATTERN.search(name):
            return "拒绝创建分支: 分支名包含非法字符。"
        completed = self._run_raw(["git", "check-ref-format", "--branch", name])
        if isinstance(completed, str):
            return completed
        if completed.returncode != 0:
            return self._format_completed(completed) or "拒绝创建分支: 分支名不符合 Git 规范。"
        return ""

    def _run(self, command: list[str], max_chars: int = 12000) -> str:
        completed = self._run_raw(command)
        if isinstance(completed, str):
            return completed
        output = self._format_completed(completed)[:max_chars]
        if completed.returncode != 0:
            return output or f"Git 命令失败，exit_code={completed.returncode}。"
        return output or "没有 Git 输出。"

    def _run_raw(self, command: list[str]) -> Union[subprocess.CompletedProcess, str]:
        try:
            return subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return "Git 命令超时。"
        except OSError as error:
            return f"Git 命令失败: {error}"

    def _format_completed(self, completed: subprocess.CompletedProcess) -> str:
        return "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        )


def _sensitive_path_warnings(text: str) -> str:
    warnings = []
    for raw_line in text.splitlines():
        parts = raw_line.split()
        if not parts:
            continue
        path = parts[-1]
        path_parts = Path(path).parts
        if Path(path).name in DENIED_FILE_NAMES or any(part in DENIED_DIR_NAMES for part in path_parts):
            warnings.append(path)
    return ", ".join(sorted(set(warnings)))
