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
    line_number: int


class ProjectRAG:
    def __init__(self, root: Path, max_file_bytes: int = MAX_FILE_BYTES):
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes

    def search(self, query: str, max_results: int = 5) -> str:
        terms = _terms(query)
        if not terms:
            return "请提供要检索的关键词。"

        results = self.search_results(query, max_results)
        if not results:
            return "没有找到相关项目上下文。"

        return "\n\n".join(
            f"[{index}] {result.path}:L{result.line_number} (score={result.score})\n{result.snippet}"
            for index, result in enumerate(results, 1)
        )

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
            score = _score(text, relative_path, terms, phrase)
            if score <= 0:
                continue

            snippet, line_number = _snippet(text, terms)
            results.append(
                SearchResult(
                    path=relative_path,
                    score=score,
                    snippet=snippet,
                    line_number=line_number,
                )
            )

        results.sort(key=lambda result: (-result.score, result.path))
        return results[:max_results]

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


def _snippet(text: str, terms: list[str], max_chars: int = 500) -> tuple[str, int]:
    lines = text.splitlines()
    if not lines:
        return "", 1

    best_index = 0
    best_score = -1
    for index, line in enumerate(lines):
        lower_line = line.lower()
        score = len({term for term in terms if term in lower_line}) * 10
        score += sum(lower_line.count(term) for term in terms)
        if score > best_score:
            best_index = index
            best_score = score

    start_line = max(0, best_index - 2)
    selected = []
    current_chars = 0
    for line in lines[start_line:]:
        if selected and current_chars + len(line) + 1 > max_chars:
            break
        selected.append(line)
        current_chars += len(line) + 1

    snippet = "\n".join(selected).strip()
    return re.sub(r"\n{3,}", "\n\n", snippet), start_line + 1
