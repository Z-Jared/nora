import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


TEXT_EXTENSIONS = {
    ".py", ".pyi",
    ".md", ".rst", ".txt",
    ".json", ".toml", ".yaml", ".yml",
    ".js", ".jsx", ".ts", ".tsx", ".mjs",
    ".html", ".htm", ".css", ".scss", ".less",
    ".sh", ".bash", ".zsh",
    ".c", ".h", ".cpp", ".hpp",
    ".go", ".rs", ".java", ".kt",
    ".rb", ".php",
    ".sql", ".graphql",
    ".xml", ".svg",
    ".ini", ".cfg", ".conf",
    ".dockerfile", ".makefile",
    ".env.example",
}
MAX_FILE_BYTES = 64 * 1024
DEFAULT_CHUNK_SIZE = 80
DEFAULT_CHUNK_OVERLAP = 20
DENIED_FILE_NAMES = {".env", ".env.local", ".env.production"}
TEXT_FILENAMES = {"Dockerfile", "Makefile", "Justfile", "Procfile"}
DENIED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "data", "logs", ".tmp"}


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: int
    snippet: str
    line_number: int
    end_line_number: int


class ProjectRAG:
    def __init__(
        self,
        root: Path,
        max_file_bytes: int = MAX_FILE_BYTES,
        include_paths: Optional[list[str]] = None,
        exclude_dirs: Optional[list[str]] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        self.root = root.resolve()
        self.max_file_bytes = max(1024, min(max_file_bytes, 1024 * 1024))
        self.include_paths = [path.strip().strip("/") for path in include_paths or [] if path.strip()]
        self.exclude_dirs = set(DENIED_DIR_NAMES) | {item.strip() for item in exclude_dirs or [] if item.strip()}
        self.chunk_size = max(10, min(chunk_size, 400))
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def search(self, query: str, max_results: int = 5) -> str:
        terms = _terms(query)
        if not terms:
            return "请提供要检索的关键词。"

        results = self.search_results(query, max_results)
        if not results:
            return "没有找到相关项目上下文。"

        return "\n\n".join(_format_result(index, result) for index, result in enumerate(results, 1))

    def search_results(self, query: str, max_results: int = 5) -> list[SearchResult]:
        terms = _terms(query)
        if not terms:
            return []

        phrase = query.strip().lower()
        max_results = max(1, min(max_results, 10))
        results = []
        for path in self._iter_text_files():
            text = self._read_text(path)
            if not text:
                continue

            relative_path = path.relative_to(self.root).as_posix()
            for start_line, end_line, chunk in self._chunks(text):
                score = _score(chunk, relative_path, terms, phrase)
                if score <= 0:
                    continue
                results.append(
                    SearchResult(
                        path=relative_path,
                        score=score,
                        snippet=_trim_snippet(chunk),
                        line_number=start_line,
                        end_line_number=end_line,
                    )
                )

        results.sort(key=lambda result: (-result.score, result.path, result.line_number))
        return results[:max_results]

    def context_for_question(self, question: str, max_results: int = 5) -> str:
        return "\n".join(
            [
                f"问题: {question}",
                "请只基于下面的来源片段回答；如果片段不足，请说明缺少依据。",
                "",
                "相关项目上下文:",
                self.search(question, max_results),
            ]
        )

    def _chunks(self, text: str):
        lines = text.splitlines()
        if not lines:
            return
        step = max(1, self.chunk_size - self.chunk_overlap)
        start = 0
        while start < len(lines):
            end = min(len(lines), start + self.chunk_size)
            chunk = "\n".join(lines[start:end]).strip()
            if chunk:
                yield start + 1, end, chunk
            if end == len(lines):
                break
            start += step

    def _iter_text_files(self):
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or not self._is_allowed(path):
                continue
            is_text = path.suffix.lower() in TEXT_EXTENSIONS or path.name in TEXT_FILENAMES
            if not is_text:
                continue
            if path.stat().st_size > self.max_file_bytes:
                continue
            yield path

    def _is_allowed(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            return False

        if path.name in DENIED_FILE_NAMES:
            return False
        if any(part in self.exclude_dirs for part in relative.parts):
            return False
        if self.include_paths:
            relative_text = relative.as_posix()
            return any(relative_text == prefix or relative_text.startswith(prefix + "/") for prefix in self.include_paths)
        return True

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ""


def _terms(query: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[\w.-]+", query) if len(term) > 1]


def _score(text: str, path: str, terms: list[str], phrase: str) -> int:
    lower_text = text.lower()
    lower_path = path.lower()
    matched_terms = {term for term in terms if term in lower_text or term in lower_path}
    if not matched_terms:
        return 0

    coverage_score = len(matched_terms) * 100
    phrase_score = 50 if len(phrase) > 1 and phrase in lower_text else 0
    path_score = sum(25 for term in terms if term in lower_path)
    frequency_score = min(sum(lower_text.count(term) for term in terms), 50)
    return coverage_score + phrase_score + path_score + frequency_score


def _trim_snippet(text: str, max_chars: int = 700) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n..."


def _format_result(index: int, result: SearchResult) -> str:
    return (
        f"[{index}] path={result.path} lines={result.line_number}-{result.end_line_number} "
        f"score={result.score}\n{result.snippet}"
    )
