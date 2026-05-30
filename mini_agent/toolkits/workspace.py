import difflib
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from mini_agent.durable_events import (
    FILE_EDIT_BLOCKED,
    FILE_EDIT_ERROR,
    FILE_EDIT_FINISHED,
    FILE_EDIT_STARTED,
)
from mini_agent.tools_common import confirm_in_terminal


MAX_FILE_BYTES = 64 * 1024
DENIED_FILE_NAMES = {".env", ".env.local", ".env.production"}
DENIED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "data", "logs"}


class WorkspaceFiles:
    def __init__(
        self,
        root: Path,
        max_file_bytes: int = MAX_FILE_BYTES,
        confirm_action: Optional[Callable[[str], bool]] = None,
        require_confirmation: bool = True,
        event_store=None,
    ):
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes
        self.confirm_action = confirm_action or confirm_in_terminal
        self.require_confirmation = require_confirmation
        self.event_store = event_store

    def _record_file_edit_event(
        self,
        event_type: str,
        path: str,
        operation: str,
        file_count: int = 1,
        status: str = "",
        error: str = "",
        bytes_before: Optional[int] = None,
        bytes_after: Optional[int] = None,
    ) -> None:
        if not self.event_store:
            return
        payload = {
            "path": path,
            "paths": [item.strip() for item in path.split(",") if item.strip()],
            "operation": operation,
            "file_count": file_count,
            "status": status,
            "error": error,
        }
        if bytes_before is not None:
            payload["bytes_before"] = bytes_before
        if bytes_after is not None:
            payload["bytes_after"] = bytes_after
        severity = "warning" if event_type in (FILE_EDIT_BLOCKED, FILE_EDIT_ERROR) else "info"
        try:
            self.event_store.record(
                event_type=event_type,
                task_id=None,
                source="workspace",
                summary=f"{event_type}: {path} ({operation})",
                severity=severity,
                payload=payload,
            )
        except Exception:
            pass

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

    def preview_write(self, path: str, content: str, context_lines: int = 3) -> str:
        target = self._resolve_target(path)
        if not target:
            return "拒绝预览: 只能预览项目目录内的非敏感文件。"

        if len(content.encode("utf-8")) > self.max_file_bytes:
            return f"拒绝预览: 最大支持 {self.max_file_bytes} bytes。"

        current = ""
        if target.exists():
            current = self.read(path)
            if current.startswith(("拒绝读取", "读取失败", "不是文件", "文件过大")):
                return current

        return self._diff(path, current, content, context_lines)

    def preview_replace(self, path: str, old_text: str, new_text: str, context_lines: int = 3) -> str:
        target = self._resolve_target(path)
        if not target:
            return "拒绝预览: 只能预览项目目录内的非敏感文件。"

        if not old_text:
            return "拒绝预览: old_text 不能为空。"

        current = self.read(path)
        if current.startswith(("拒绝读取", "读取失败", "文件不存在", "不是文件", "文件过大")):
            return current

        if old_text not in current:
            return "没有找到要替换的文本。"

        updated = current.replace(old_text, new_text, 1)
        if len(updated.encode("utf-8")) > self.max_file_bytes:
            return f"拒绝预览: 最大支持 {self.max_file_bytes} bytes。"

        return self._diff(path, current, updated, context_lines)

    def write(self, path: str, content: str, reason: str = "") -> str:
        target = self._resolve_target(path)
        if not target:
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "write", status="blocked", error="denied_path")
            return "拒绝写入: 只能写入项目目录内的非敏感文件。"

        bytes_after = len(content.encode("utf-8"))
        if bytes_after > self.max_file_bytes:
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "write", status="blocked", error="file_too_large")
            return f"拒绝写入: 最大支持 {self.max_file_bytes} bytes。"

        bytes_before = self._file_size_or_zero(target)
        self._record_file_edit_event(
            FILE_EDIT_STARTED,
            path,
            "write",
            status="started",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )

        if self.require_confirmation:
            prompt = self._confirmation_prompt("写入/覆盖文件", target, reason)
            if not self.confirm_action(prompt):
                self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "write", status="cancelled", error="cancelled")
                return "已取消写入。"

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as error:
            self._record_file_edit_event(FILE_EDIT_ERROR, path, "write", status="error", error="write_failed")
            return f"写入失败: {error}"

        self._record_file_edit_event(
            FILE_EDIT_FINISHED,
            path,
            "write",
            status="finished",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )
        return f"已写入文件: {target.relative_to(self.root).as_posix()}"

    def replace(self, path: str, old_text: str, new_text: str, reason: str = "") -> str:
        target = self._resolve_target(path)
        if not target:
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "replace", status="blocked", error="denied_path")
            return "拒绝修改: 只能修改项目目录内的非敏感文件。"

        if not old_text:
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "replace", status="blocked", error="empty_old_text")
            return "拒绝修改: old_text 不能为空。"

        current = self.read(path)
        if current.startswith(("拒绝读取", "读取失败", "文件不存在", "不是文件", "文件过大")):
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "replace", status="blocked", error="read_failed")
            return current

        if old_text not in current:
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "replace", status="blocked", error="text_not_found")
            return "没有找到要替换的文本。"

        updated = current.replace(old_text, new_text, 1)
        bytes_before = len(current.encode("utf-8"))
        bytes_after = len(updated.encode("utf-8"))
        if bytes_after > self.max_file_bytes:
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "replace", status="blocked", error="file_too_large")
            return f"拒绝修改: 最大支持 {self.max_file_bytes} bytes。"

        self._record_file_edit_event(
            FILE_EDIT_STARTED,
            path,
            "replace",
            status="started",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )

        if self.require_confirmation:
            prompt = self._confirmation_prompt("修改文件", target, reason)
            if not self.confirm_action(prompt):
                self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "replace", status="cancelled", error="cancelled")
                return "已取消修改。"

        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as error:
            self._record_file_edit_event(FILE_EDIT_ERROR, path, "replace", status="error", error="write_failed")
            return f"修改失败: {error}"

        self._record_file_edit_event(
            FILE_EDIT_FINISHED,
            path,
            "replace",
            status="finished",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )
        return f"已修改文件: {target.relative_to(self.root).as_posix()}"

    def apply_unified_diff(self, patch: str, reason: str = "") -> str:
        prepared = self._prepare_patch(patch, "应用 patch", allow_multiple=False)
        if isinstance(prepared, str):
            self._record_file_edit_event(FILE_EDIT_BLOCKED, "", "patch", status="blocked", error="invalid_patch")
            return prepared
        changes = prepared
        path, current, updated = changes[0]
        target = self._resolve_target(path)
        if target is None:
            self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "patch", status="blocked", error="denied_path")
            return "拒绝应用 patch: 只能修改项目目录内的非敏感文件。"

        bytes_before = len(current.encode("utf-8"))
        bytes_after = len(updated.encode("utf-8"))
        self._record_file_edit_event(
            FILE_EDIT_STARTED,
            path,
            "patch",
            status="started",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )

        if self.require_confirmation:
            prompt = self._confirmation_prompt("应用 patch", target, reason)
            if not self.confirm_action(prompt):
                self._record_file_edit_event(FILE_EDIT_BLOCKED, path, "patch", status="cancelled", error="cancelled")
                return "已取消应用 patch。"

        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as error:
            self._record_file_edit_event(FILE_EDIT_ERROR, path, "patch", status="error", error="patch_write_failed")
            return f"应用 patch 失败: {error}"

        self._record_file_edit_event(
            FILE_EDIT_FINISHED,
            path,
            "patch",
            status="finished",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )
        return f"已应用 patch: {target.relative_to(self.root).as_posix()}"

    def preview_multi_file_patch(self, patch: str, context_lines: int = 3) -> str:
        prepared = self._prepare_patch(patch, "预览多文件 patch", allow_multiple=True)
        if isinstance(prepared, str):
            return prepared
        context_lines = max(0, min(context_lines, 20))
        sections = ["将修改文件:"]
        sections.extend(f"- {path}" for path, _current, _updated in prepared)
        sections.append("diff:")
        for path, current, updated in prepared:
            sections.append(self._diff(path, current, updated, context_lines))
        return "\n".join(sections)

    def apply_multi_file_patch(self, patch: str, reason: str = "") -> str:
        prepared = self._prepare_patch(patch, "应用多文件 patch", allow_multiple=True)
        if isinstance(prepared, str):
            self._record_file_edit_event(FILE_EDIT_BLOCKED, "", "multi_patch", status="blocked", error="invalid_patch")
            return prepared
        paths = [path for path, _current, _updated in prepared]
        file_count = len(paths)
        targets = []
        for path in paths:
            target = self._resolve_target(path)
            if target is None:
                self._record_file_edit_event(
                    FILE_EDIT_BLOCKED,
                    path,
                    "multi_patch",
                    file_count=file_count,
                    status="blocked",
                    error="denied_path",
                )
                return "拒绝应用多文件 patch: 只能修改项目目录内的非敏感文件。"
            targets.append(target)

        bytes_before = sum(len(current.encode("utf-8")) for _path, current, _updated in prepared)
        bytes_after = sum(len(updated.encode("utf-8")) for _path, _current, updated in prepared)
        joined_paths = ", ".join(paths)
        self._record_file_edit_event(
            FILE_EDIT_STARTED,
            joined_paths,
            "multi_patch",
            file_count=file_count,
            status="started",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )

        if self.require_confirmation:
            target_text = ", ".join(paths)
            reason_text = reason.strip() or "未提供"
            prompt = f"应用多文件 patch: {target_text}\n原因: {reason_text}\n是否继续? [y/N]: "
            if not self.confirm_action(prompt):
                self._record_file_edit_event(
                    FILE_EDIT_BLOCKED,
                    joined_paths,
                    "multi_patch",
                    file_count=file_count,
                    status="cancelled",
                    error="cancelled",
                )
                return "已取消应用多文件 patch。"

        originals = {target: target.read_text(encoding="utf-8") for target in targets}
        written = []
        try:
            for (_path, _current, updated), target in zip(prepared, targets):
                temp = target.with_name(target.name + ".tmp-mini-agent")
                temp.write_text(updated, encoding="utf-8")
                temp.replace(target)
                written.append(target)
        except OSError as error:
            rollback_errors = []
            for target in written:
                try:
                    target.write_text(originals[target], encoding="utf-8")
                except OSError as rollback_error:
                    rollback_errors.append(f"{target.relative_to(self.root).as_posix()}: {rollback_error}")
            if rollback_errors:
                self._record_file_edit_event(
                    FILE_EDIT_ERROR,
                    joined_paths,
                    "multi_patch",
                    file_count=file_count,
                    status="error",
                    error="rollback_failed",
                )
                return f"应用多文件 patch 失败: {error}；回滚失败: {'; '.join(rollback_errors)}"
            self._record_file_edit_event(
                FILE_EDIT_ERROR,
                joined_paths,
                "multi_patch",
                file_count=file_count,
                status="error",
                error="patch_write_failed_rolled_back",
            )
            return f"应用多文件 patch 失败: {error}；已回滚已写入文件。"

        self._record_file_edit_event(
            FILE_EDIT_FINISHED,
            joined_paths,
            "multi_patch",
            file_count=file_count,
            status="finished",
            bytes_before=bytes_before,
            bytes_after=bytes_after,
        )
        return "已应用多文件 patch:\n" + "\n".join(f"- {path}" for path in paths)

    def _prepare_patch(self, patch: str, action: str, allow_multiple: bool):
        if not patch.strip():
            return f"拒绝{action}: patch 不能为空。"
        if len(patch.encode("utf-8")) > self.max_file_bytes:
            return f"拒绝{action}: 最大支持 {self.max_file_bytes} bytes。"

        parsed = self._parse_multi_file_patch(patch)
        if isinstance(parsed, str):
            return parsed.replace("拒绝应用 patch", f"拒绝{action}")
        if not allow_multiple and len(parsed) != 1:
            return f"拒绝{action}: 只支持单文件 patch。"

        changes = []
        for path, hunks in parsed:
            target = self._resolve_target(path)
            if not target:
                return f"拒绝{action}: 只能修改项目目录内的非敏感文件。"
            if not target.exists():
                return f"文件不存在: {path}"
            current = self.read(path)
            if current.startswith(("拒绝读取", "读取失败", "文件不存在", "不是文件", "文件过大")):
                return current
            ok, applied = self._apply_hunks(current, hunks)
            if not ok:
                return applied.replace("拒绝应用 patch", f"拒绝{action}")
            if len(applied.encode("utf-8")) > self.max_file_bytes:
                return f"拒绝{action}: 最大支持 {self.max_file_bytes} bytes。"
            if applied == current:
                return "没有变化。"
            changes.append((path, current, applied))
        return changes

    def _apply_hunks(self, current: str, hunks: List[Tuple[int, List[Tuple[str, str]]]]):
        lines = current.splitlines(keepends=True)
        updated = []
        cursor = 0
        for old_start, hunk_lines in hunks:
            hunk_index = max(0, old_start - 1)
            if hunk_index < cursor:
                return False, "拒绝应用 patch: hunk 顺序或上下文不合法。"
            updated.extend(lines[cursor:hunk_index])
            cursor = hunk_index
            for marker, content in hunk_lines:
                if marker in {" ", "-"}:
                    if cursor >= len(lines) or lines[cursor] != content:
                        return False, "拒绝应用 patch: 当前文件内容与 patch 上下文不匹配。"
                    if marker == " ":
                        updated.append(lines[cursor])
                    cursor += 1
                elif marker == "+":
                    updated.append(content)
        updated.extend(lines[cursor:])
        return True, "".join(updated)

    def _parse_multi_file_patch(self, patch: str):
        lines = patch.splitlines(keepends=True)
        files = []
        seen_paths = set()
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith(("rename from ", "rename to ", "new file mode ", "deleted file mode ")):
                return "拒绝应用 patch: 不支持创建、删除或重命名文件。"
            if not line.startswith("--- "):
                index += 1
                continue
            old_path = self._clean_patch_path(line[4:].strip())
            index += 1
            if index >= len(lines) or not lines[index].startswith("+++ "):
                return "拒绝应用 patch: 缺少 +++ 文件头。"
            new_path = self._clean_patch_path(lines[index][4:].strip())
            index += 1
            if old_path == "/dev/null" or new_path == "/dev/null":
                return "拒绝应用 patch: 不支持创建或删除文件。"
            if old_path != new_path:
                return "拒绝应用 patch: 不支持重命名文件。"
            if old_path in seen_paths:
                return "拒绝应用 patch: 同一个文件不能出现多个 patch section。"
            seen_paths.add(old_path)
            hunks = []
            while index < len(lines) and not lines[index].startswith("--- "):
                if lines[index].startswith(("rename from ", "rename to ", "new file mode ", "deleted file mode ")):
                    return "拒绝应用 patch: 不支持创建、删除或重命名文件。"
                if not lines[index].startswith("@@ "):
                    index += 1
                    continue
                old_start = self._parse_hunk_start(lines[index])
                if old_start is None:
                    return "拒绝应用 patch: hunk 头无效。"
                index += 1
                hunk_lines = []
                while index < len(lines) and not lines[index].startswith("@@ ") and not lines[index].startswith("--- "):
                    marker = lines[index][:1]
                    if marker in {" ", "+", "-"}:
                        hunk_lines.append((marker, lines[index][1:]))
                    elif lines[index].startswith("\\ No newline at end of file"):
                        pass
                    elif lines[index].startswith(("diff --git ", "index ")):
                        pass
                    else:
                        return "拒绝应用 patch: hunk 行无效。"
                    index += 1
                hunks.append((old_start, hunk_lines))
            if not hunks:
                return "拒绝应用 patch: 没有可应用的 hunk。"
            files.append((old_path, hunks))
        if not files:
            return "拒绝应用 patch: 缺少文件头。"
        return files

    def _resolve_target(self, path: str) -> Optional[Path]:
        try:
            target = (self.root / path).resolve()
        except OSError:
            return None

        if not self._is_allowed_path(target):
            return None

        return target

    def _file_size_or_zero(self, target: Path) -> int:
        try:
            if target.exists() and target.is_file():
                return target.stat().st_size
        except OSError:
            return 0
        return 0

    def _confirmation_prompt(self, action: str, target: Path, reason: str) -> str:
        relative = target.relative_to(self.root).as_posix()
        reason_text = reason.strip() or "未提供"
        return f"{action}: {relative}\n原因: {reason_text}\n是否继续? [y/N]: "

    def _parse_single_file_patch(self, patch: str):
        lines = patch.splitlines(keepends=True)
        old_path = ""
        new_path = ""
        hunks = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith("--- "):
                old_path = self._clean_patch_path(line[4:].strip())
                index += 1
                if index >= len(lines) or not lines[index].startswith("+++ "):
                    return "拒绝应用 patch: 缺少 +++ 文件头。"
                new_path = self._clean_patch_path(lines[index][4:].strip())
                index += 1
                continue
            if line.startswith("@@ "):
                old_start = self._parse_hunk_start(line)
                if old_start is None:
                    return "拒绝应用 patch: hunk 头无效。"
                index += 1
                hunk_lines = []
                while index < len(lines) and not lines[index].startswith("@@ ") and not lines[index].startswith("--- "):
                    marker = lines[index][:1]
                    if marker in {" ", "+", "-"}:
                        hunk_lines.append((marker, lines[index][1:]))
                    elif lines[index].startswith("\\ No newline at end of file"):
                        pass
                    else:
                        return "拒绝应用 patch: hunk 行无效。"
                    index += 1
                hunks.append((old_start, hunk_lines))
                continue
            index += 1

        if not old_path or not new_path:
            return "拒绝应用 patch: 缺少文件头。"
        if old_path == "/dev/null" or new_path == "/dev/null":
            return "拒绝应用 patch: 不支持创建或删除文件。"
        if old_path != new_path:
            return "拒绝应用 patch: 不支持重命名文件。"
        if not hunks:
            return "拒绝应用 patch: 没有可应用的 hunk。"
        return old_path, hunks

    def _clean_patch_path(self, raw_path: str) -> str:
        path = raw_path.split("\t", 1)[0].split(" ", 1)[0]
        if path.startswith(("a/", "b/")):
            path = path[2:]
        return path

    def _parse_hunk_start(self, line: str) -> Optional[int]:
        try:
            old_range = line.split(" ", 2)[1]
            start = old_range.removeprefix("-").split(",", 1)[0]
            return int(start)
        except (IndexError, ValueError):
            return None

    def _diff(self, path: str, old: str, new: str, context_lines: int) -> str:
        if old == new:
            return "没有变化。"

        context_lines = max(0, min(context_lines, 20))
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=context_lines,
        )
        return "".join(diff).strip() or "没有变化。"

    def _is_allowed_path(self, target: Path) -> bool:
        try:
            relative = target.relative_to(self.root)
        except ValueError:
            return False

        if target.name in DENIED_FILE_NAMES:
            return False

        return not any(part in DENIED_DIR_NAMES for part in relative.parts)
