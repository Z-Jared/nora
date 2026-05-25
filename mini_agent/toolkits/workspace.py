from pathlib import Path
from typing import Callable, Optional

from mini_agent.tools_common import confirm_in_terminal


MAX_FILE_BYTES = 64 * 1024
DENIED_FILE_NAMES = {".env", ".env.local", ".env.production"}
DENIED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "data"}


class WorkspaceFiles:
    def __init__(
        self,
        root: Path,
        max_file_bytes: int = MAX_FILE_BYTES,
        confirm_action: Optional[Callable[[str], bool]] = None,
    ):
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes
        self.confirm_action = confirm_action or confirm_in_terminal

    def read(self, path: str) -> str:
        try:
            target = (self.root / path).resolve()
        except OSError as error:
            return f"读取失败: {error}"

        if not self._is_allowed_path(target):
            return "拒绝读取: 只能读取项目目录内的非敏感文件。"

        if not target.exists():
            return f"文件不存在: {path}"

        if not target.is_file():
            return f"不是文件: {path}"

        if target.stat().st_size > self.max_file_bytes:
            return f"文件过大: 最大支持 {self.max_file_bytes} bytes。"

        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "读取失败: 只支持 UTF-8 文本文件。"
        except OSError as error:
            return f"读取失败: {error}"

    def list(self, max_files: int = 50) -> str:
        max_files = max(1, min(max_files, 200))
        files = []

        for target in sorted(self.root.rglob("*")):
            if len(files) >= max_files:
                break

            if not target.is_file() or not self._is_allowed_path(target):
                continue

            files.append(target.relative_to(self.root).as_posix())

        if not files:
            return "没有找到可列出的项目文件。"

        return "\n".join(files)

    def write(self, path: str, content: str, reason: str = "") -> str:
        target = self._resolve_target(path)
        if not target:
            return "拒绝写入: 只能写入项目目录内的非敏感文件。"

        if len(content.encode("utf-8")) > self.max_file_bytes:
            return f"拒绝写入: 最大支持 {self.max_file_bytes} bytes。"

        prompt = self._confirmation_prompt("写入/覆盖文件", target, reason)
        if not self.confirm_action(prompt):
            return "已取消写入。"

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as error:
            return f"写入失败: {error}"

        return f"已写入文件: {target.relative_to(self.root).as_posix()}"

    def replace(self, path: str, old_text: str, new_text: str, reason: str = "") -> str:
        target = self._resolve_target(path)
        if not target:
            return "拒绝修改: 只能修改项目目录内的非敏感文件。"

        if not old_text:
            return "拒绝修改: old_text 不能为空。"

        current = self.read(path)
        if current.startswith(("拒绝读取", "读取失败", "文件不存在", "不是文件", "文件过大")):
            return current

        if old_text not in current:
            return "没有找到要替换的文本。"

        updated = current.replace(old_text, new_text, 1)
        if len(updated.encode("utf-8")) > self.max_file_bytes:
            return f"拒绝修改: 最大支持 {self.max_file_bytes} bytes。"

        prompt = self._confirmation_prompt("修改文件", target, reason)
        if not self.confirm_action(prompt):
            return "已取消修改。"

        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as error:
            return f"修改失败: {error}"

        return f"已修改文件: {target.relative_to(self.root).as_posix()}"

    def _resolve_target(self, path: str) -> Optional[Path]:
        try:
            target = (self.root / path).resolve()
        except OSError:
            return None

        if not self._is_allowed_path(target):
            return None

        return target

    def _confirmation_prompt(self, action: str, target: Path, reason: str) -> str:
        relative = target.relative_to(self.root).as_posix()
        reason_text = reason.strip() or "未提供"
        return f"{action}: {relative}\n原因: {reason_text}\n是否继续? [y/N]: "

    def _is_allowed_path(self, target: Path) -> bool:
        try:
            relative = target.relative_to(self.root)
        except ValueError:
            return False

        if target.name in DENIED_FILE_NAMES:
            return False

        return not any(part in DENIED_DIR_NAMES for part in relative.parts)
