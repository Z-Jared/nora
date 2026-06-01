from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from mini_agent.memory_records import MemoryRecordStore
from mini_agent.context_system import _safe_memory_record, _format_memory_record
from mini_agent.rag import ProjectRAG
from mini_agent.symbols import PythonSymbolIndex


MAX_CONTEXT_CHARS = 12000
DENIED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "data", "logs"}
DENIED_FILE_NAMES = {".env"}


@dataclass(frozen=True)
class ContextSection:
    title: str
    content: str
    source: str = ""
    line_range: str = ""


@dataclass
class ContextPack:
    task_description: str
    sections: list[ContextSection] = field(default_factory=list)
    total_chars: int = 0
    omitted_chars: int = 0
    truncated: bool = False

    def to_markdown(self) -> str:
        lines = [f"# Context Pack: {self.task_description}", ""]
        for section in self.sections:
            header = f"## {section.title}"
            if section.source:
                header += f" [{section.source}]"
            if section.line_range:
                header += f" (lines {section.line_range})"
            lines.append(header)
            lines.append("")
            lines.append(section.content)
            lines.append("")
        if self.omitted_chars > 0:
            lines.append(f"---\n*{self.omitted_chars} chars omitted due to budget limit.*")
        elif self.truncated:
            lines.append("---\n*Some content was truncated.*")
        return "\n".join(lines)


class ContextCompiler:
    def __init__(
        self,
        root: Path,
        symbol_index: Optional[PythonSymbolIndex] = None,
        project_rag: Optional[ProjectRAG] = None,
        memory_record_store: Optional[MemoryRecordStore] = None,
        max_chars: int = MAX_CONTEXT_CHARS,
        git_timeout: int = 10,
    ):
        self.root = root.resolve()
        self.symbol_index = symbol_index or PythonSymbolIndex(root)
        self.project_rag = project_rag
        self.memory_record_store = memory_record_store
        self.max_chars = max(200, min(max_chars, 50000))
        self.git_timeout = git_timeout

    def compile(
        self,
        task_description: str,
        include_git_status: bool = True,
        include_changed_files: bool = True,
        include_file_outlines: Optional[list[str]] = None,
        include_knowledge_excerpts: Optional[list[str]] = None,
        rag_query: Optional[str] = None,
        rag_max_results: int = 3,
        include_memory_records: bool = True,
        memory_query: Optional[str] = None,
        memory_max_results: int = 3,
    ) -> ContextPack:
        pack = ContextPack(task_description=task_description)
        budget = self.max_chars

        if include_git_status:
            section = self._git_status_section()
            if section:
                budget = self._append_if_fits(pack, section, budget)

        if include_changed_files:
            section = self._changed_files_section()
            if section:
                budget = self._append_if_fits(pack, section, budget)

        for path in (include_file_outlines or []):
            section = self._file_outline_section(path)
            if section:
                budget = self._append_if_fits(pack, section, budget)

        for path in (include_knowledge_excerpts or []):
            section = self._knowledge_excerpt_section(path)
            if section:
                budget = self._append_if_fits(pack, section, budget)

        if rag_query and self.project_rag:
            section = self._rag_section(rag_query, rag_max_results)
            if section:
                budget = self._append_if_fits(pack, section, budget)

        if include_memory_records and self.memory_record_store:
            section = self._memory_record_section(memory_query or task_description, memory_max_results)
            if section:
                budget = self._append_if_fits(pack, section, budget)

        return pack

    def _append_if_fits(self, pack: ContextPack, section: ContextSection, budget: int) -> int:
        text = section.content
        if len(text) <= budget:
            pack.sections.append(section)
            pack.total_chars += len(text)
            return budget - len(text)
        truncated_text = text[:budget].rstrip() + "\n..."
        truncated_section = ContextSection(
            title=section.title,
            content=truncated_text,
            source=section.source,
            line_range=section.line_range,
        )
        pack.sections.append(truncated_section)
        pack.omitted_chars += len(text) - len(truncated_text)
        pack.truncated = True
        return 0

    def _git_status_section(self) -> Optional[ContextSection]:
        output = self._run_git(["git", "status", "--short"])
        output = self._filter_denied_output(output)
        if not output or output == "没有 Git 输出。":
            return None
        return ContextSection(title="Git Status", content=output, source="git status --short")

    def _changed_files_section(self) -> Optional[ContextSection]:
        unstaged = self._filter_denied_output(self._run_git(["git", "diff", "--name-status", "--"]))
        staged = self._filter_denied_output(self._run_git(["git", "diff", "--cached", "--name-status", "--"]))
        untracked = self._filter_denied_output(self._run_git(["git", "ls-files", "--others", "--exclude-standard"]))

        parts = []
        if staged and staged != "没有 Git 输出。":
            parts.append(f"Staged:\n{staged}")
        if unstaged and unstaged != "没有 Git 输出。":
            parts.append(f"Unstaged:\n{unstaged}")
        if untracked and untracked != "没有 Git 输出。":
            parts.append(f"Untracked:\n{untracked}")

        if not parts:
            return None
        return ContextSection(
            title="Changed Files",
            content="\n\n".join(parts),
            source="git diff --name-status",
        )

    def _file_outline_section(self, path: str) -> Optional[ContextSection]:
        clean_path = path.strip()
        if not clean_path:
            return None
        target = self._resolve_allowed_path(clean_path)
        if target is None:
            return None
        if not target.exists():
            return None
        if target.suffix == ".py":
            outline = self.symbol_index.outline_file(clean_path)
            if not outline or outline.startswith("没有") or outline.startswith("只支持"):
                return None
            return ContextSection(
                title=f"Outline: {clean_path}",
                content=outline,
                source=clean_path,
            )
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        lines = text.splitlines()
        preview = "\n".join(lines[:80])
        if len(lines) > 80:
            preview += f"\n... ({len(lines)} lines total)"
        return ContextSection(
            title=f"File: {clean_path}",
            content=preview,
            source=clean_path,
            line_range=f"1-{min(80, len(lines))}",
        )

    def _knowledge_excerpt_section(self, path: str) -> Optional[ContextSection]:
        clean_path = path.strip()
        if not clean_path:
            return None
        target = self._resolve_allowed_path(clean_path)
        if target is None:
            return None
        if not target.exists():
            return None
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        if not text.strip():
            return None
        return ContextSection(
            title=f"Knowledge: {clean_path}",
            content=text[:3000].rstrip(),
            source=clean_path,
        )

    def _rag_section(self, query: str, max_results: int) -> Optional[ContextSection]:
        results = self.project_rag.search_results(query, max_results=max_results)
        if not results:
            return None
        parts = []
        for i, result in enumerate(results, 1):
            parts.append(
                f"[{i}] {result.path} L{result.line_number}-{result.end_line_number} "
                f"(score={result.score})\n{result.snippet}"
            )
        return ContextSection(
            title="RAG Snippets (auxiliary)",
            content="\n\n".join(parts),
            source=f"rag query: {query}",
        )

    def _memory_record_section(self, query: str, max_results: int) -> Optional[ContextSection]:
        records = self.memory_record_store.search(query, max_results=max_results)
        safe = [r for r in records if _safe_memory_record(r)]
        if not safe:
            return None
        content = "\n".join(_format_memory_record(r) for r in safe)
        return ContextSection(
            title="结构化记忆",
            content=content,
            source="memory records",
        )

    def _run_git(self, command: list[str]) -> str:
        try:
            result = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.git_timeout,
            )
            output = "\n".join(
                part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
            )
            return output or "没有 Git 输出。"
        except (subprocess.TimeoutExpired, OSError):
            return ""

    def _resolve_allowed_path(self, path: str) -> Optional[Path]:
        target = (self.root / path).resolve()
        try:
            relative = target.relative_to(self.root)
        except ValueError:
            return None
        if target.name in DENIED_FILE_NAMES:
            return None
        if any(part in DENIED_DIR_NAMES for part in relative.parts):
            return None
        return target

    def _filter_denied_output(self, output: str) -> str:
        if not output:
            return ""
        kept = []
        for line in output.splitlines():
            if self._line_mentions_denied_path(line):
                continue
            kept.append(line)
        return "\n".join(kept).strip() or "没有 Git 输出。"

    def _line_mentions_denied_path(self, line: str) -> bool:
        for raw_part in line.replace("\t", " ").split():
            part = raw_part.strip()
            if not part:
                continue
            if part in DENIED_FILE_NAMES or part.startswith(".env"):
                return True
            if any(part == denied or part.startswith(denied + "/") for denied in DENIED_DIR_NAMES):
                return True
        return False
