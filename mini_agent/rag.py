import re
from dataclasses import dataclass
from pathlib import Path


TEXT_EXTENSIONS = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml"}
MAX_FILE_BYTES = 64 * 1024
DENIED_FILE_NAMES = {".env", ".env.local", ".env.production"}
DENIED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "data"}


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: int
    snippet: str


class ProjectRAG:
    def __init__(self, root: Path, max_file_bytes: int = MAX_FILE_BYTES):
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes

    def search(self, query: str, max_results: int = 5) -> str:
        terms = _terms(query)
        if not terms:
            return "请提供要检索的关键词。"

        max_results = max(1, min(max_results, 10))
        results = []
        for path in self._iter_text_files():
            text = self._read_text(path)
            if not text:
                continue

            score = sum(text.lower().count(term) for term in terms)
            if score <= 0:
                continue

            results.append(
                SearchResult(
                    path=path.relative_to(self.root).as_posix(),
                    score=score,
                    snippet=_snippet(text, terms),
                )
            )

        if not results:
            return "没有找到相关项目上下文。"

        results.sort(key=lambda result: (-result.score, result.path))
        return "\n\n".join(
            f"[{index}] {result.path} (score={result.score})\n{result.snippet}"
            for index, result in enumerate(results[:max_results], 1)
        )

    def context_for_question(self, question: str, max_results: int = 5) -> str:
        return f"问题: {question}\n\n相关项目上下文:\n{self.search(question, max_results)}"

    def _iter_text_files(self):
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or not self._is_allowed(path):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
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

        return not any(part in DENIED_DIR_NAMES or part == "logs" for part in relative.parts)

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ""


def _terms(query: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[\w.-]+", query) if len(term) > 1]


def _snippet(text: str, terms: list[str], max_chars: int = 500) -> str:
    lower = text.lower()
    first_match = min((lower.find(term) for term in terms if term in lower), default=0)
    start = max(0, first_match - 120)
    snippet = text[start : start + max_chars].strip()
    return re.sub(r"\n{3,}", "\n\n", snippet)
