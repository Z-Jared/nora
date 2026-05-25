import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DENIED_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "data", "logs"}
MAX_CONTEXT_CHARS = 3000


@dataclass(frozen=True)
class PythonSymbol:
    path: str
    name: str
    kind: str
    line_number: int
    end_line_number: int
    signature: str = ""
    docstring: str = ""
    parent: str = ""


@dataclass(frozen=True)
class PythonReference:
    path: str
    line_number: int
    kind: str
    line: str


class PythonSymbolIndex:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def list_symbols(self, query: str = "", max_results: int = 50) -> str:
        query = query.strip().lower()
        max_results = max(1, min(max_results, 200))
        symbols = [symbol for symbol in self._symbols() if not query or query in symbol.name.lower() or query in symbol.path.lower()]
        if not symbols:
            return "没有找到 Python 符号。"
        return "\n".join(_format_symbol(symbol) for symbol in symbols[:max_results])

    def find_symbol(self, name: str, max_results: int = 20) -> str:
        name = name.strip().lower()
        if not name:
            return "请提供符号名称。"
        max_results = max(1, min(max_results, 100))
        symbols = [symbol for symbol in self._symbols() if name in symbol.name.lower()]
        if not symbols:
            return "没有找到 Python 符号。"
        symbols.sort(key=lambda symbol: (symbol.name.lower() != name, symbol.path, symbol.line_number))
        return "\n".join(_format_symbol(symbol) for symbol in symbols[:max_results])

    def outline_file(self, path: str, max_symbols: int = 100) -> str:
        relative_path = path.strip()
        if not relative_path:
            return "请提供 Python 文件路径。"
        max_symbols = max(1, min(max_symbols, 300))
        target = self._resolve_project_path(relative_path)
        if target is None:
            return "路径不在项目目录内或位于受保护目录。"
        if target.suffix != ".py":
            return "只支持 Python 文件。"
        try:
            source = target.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except FileNotFoundError:
            return "文件不存在。"
        except (OSError, UnicodeDecodeError):
            return "无法读取 Python 文件。"
        except SyntaxError as error:
            return f"Python 语法错误，无法生成 outline: L{error.lineno or '?'} {error.msg}"
        relative = target.relative_to(self.root).as_posix()
        symbols = self._symbols_from_tree(tree, relative)
        if not symbols:
            return "没有找到 Python 符号。"
        lines = [f"{relative} outline:"]
        for symbol in symbols[:max_symbols]:
            indent = "  " * symbol.name.count(".")
            lines.append(f"{indent}L{symbol.line_number}-{symbol.end_line_number} {symbol.kind} {symbol.name}{symbol.signature}")
        if len(symbols) > max_symbols:
            lines.append(f"... 还有 {len(symbols) - max_symbols} 个符号未显示")
        return "\n".join(lines)

    def describe_symbol(self, name: str, max_results: int = 5, context_lines: int = 8) -> str:
        query = name.strip().lower()
        if not query:
            return "请提供符号名称。"
        max_results = max(1, min(max_results, 20))
        context_lines = max(0, min(context_lines, 30))
        symbols = [symbol for symbol in self._symbols() if query in symbol.name.lower()]
        if not symbols:
            return "没有找到 Python 符号。"
        symbols.sort(key=lambda symbol: (symbol.name.lower() != query, symbol.path, symbol.line_number))
        blocks = []
        for symbol in symbols[:max_results]:
            blocks.append(self._describe_one_symbol(symbol, context_lines))
        return "\n\n".join(blocks)

    def find_references(self, name: str, max_results: int = 100) -> str:
        query = name.strip()
        if not query:
            return "请提供引用名称。"
        if "." in query:
            query = query.rsplit(".", 1)[-1]
        max_results = max(1, min(max_results, 300))
        references = []
        for path, tree, source_lines in self._python_trees():
            relative = path.relative_to(self.root).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == query:
                    references.append(PythonReference(relative, node.lineno, "Name", _source_line(source_lines, node.lineno)))
                elif isinstance(node, ast.Attribute) and node.attr == query:
                    references.append(PythonReference(relative, node.lineno, "Attribute", _source_line(source_lines, node.lineno)))
                if len(references) >= max_results:
                    return _format_references(query, references, truncated=True)
        if not references:
            return "没有找到可能引用。"
        return _format_references(query, references, truncated=False)

    def module_imports(self, path: str) -> str:
        relative_path = path.strip()
        if not relative_path:
            return "请提供 Python 文件路径。"
        target = self._resolve_project_path(relative_path)
        if target is None:
            return "路径不在项目目录内或位于受保护目录。"
        if target.suffix != ".py":
            return "只支持 Python 文件。"
        try:
            tree = ast.parse(target.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return "文件不存在。"
        except (OSError, UnicodeDecodeError):
            return "无法读取 Python 文件。"
        except SyntaxError as error:
            return f"Python 语法错误，无法读取 imports: L{error.lineno or '?'} {error.msg}"
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = ", ".join(alias.name if alias.asname is None else f"{alias.name} as {alias.asname}" for alias in node.names)
                imports.append(f"L{node.lineno} import {names}")
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                names = ", ".join(alias.name if alias.asname is None else f"{alias.name} as {alias.asname}" for alias in node.names)
                imports.append(f"L{node.lineno} from {module} import {names}")
        if not imports:
            return "没有找到 import。"
        relative = target.relative_to(self.root).as_posix()
        return f"{relative} imports:\n" + "\n".join(imports)

    def _symbols(self) -> list[PythonSymbol]:
        symbols = []
        for path, tree, _source_lines in self._python_trees():
            relative = path.relative_to(self.root).as_posix()
            symbols.extend(self._symbols_from_tree(tree, relative))
        return symbols

    def _python_trees(self):
        for path in sorted(self.root.rglob("*.py")):
            if not self._is_allowed(path):
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            yield path, tree, source.splitlines()

    def _symbols_from_tree(self, tree: ast.AST, relative: str) -> list[PythonSymbol]:
        symbols = []
        for node in ast.iter_child_nodes(tree):
            self._collect_symbols(node, relative, parent="", parent_kind="", symbols=symbols)
        return symbols

    def _collect_symbols(self, node: ast.AST, relative: str, parent: str, parent_kind: str, symbols: list[PythonSymbol]) -> None:
        if isinstance(node, ast.ClassDef):
            name = f"{parent}.{node.name}" if parent else node.name
            symbols.append(_symbol_from_node(relative, name, "class", node, parent))
            for child in node.body:
                self._collect_symbols(child, relative, name, "class", symbols)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = f"{parent}.{node.name}" if parent else node.name
            kind = "method" if parent_kind == "class" else "function"
            if isinstance(node, ast.AsyncFunctionDef):
                kind = f"async {kind}"
            symbols.append(_symbol_from_node(relative, name, kind, node, parent))
            for child in node.body:
                if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._collect_symbols(child, relative, name, "function", symbols)

    def _describe_one_symbol(self, symbol: PythonSymbol, context_lines: int) -> str:
        target = self.root / symbol.path
        try:
            source_lines = target.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            source_lines = []
        lines = [
            f"{symbol.path}:L{symbol.line_number}-{symbol.end_line_number} {symbol.kind} {symbol.name}",
        ]
        if symbol.signature:
            lines.append(f"signature: {symbol.signature}")
        if symbol.parent:
            lines.append(f"parent: {symbol.parent}")
        if symbol.docstring:
            lines.append(f"docstring: {_single_line(symbol.docstring)}")
        if source_lines and context_lines:
            start = max(1, symbol.line_number - context_lines)
            end = min(len(source_lines), symbol.end_line_number + context_lines)
            context = []
            for line_number in range(start, end + 1):
                context.append(f"{line_number}: {source_lines[line_number - 1]}")
            text = "\n".join(context)
            if len(text) > MAX_CONTEXT_CHARS:
                text = text[:MAX_CONTEXT_CHARS].rstrip() + "\n..."
            lines.append("source:\n" + text)
        return "\n".join(lines)

    def _resolve_project_path(self, path: str) -> Optional[Path]:
        target = (self.root / path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            return None
        if not self._is_allowed(target):
            return None
        return target

    def _is_allowed(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            return False
        return not any(part in DENIED_DIR_NAMES for part in relative.parts)


def _symbol_from_node(relative: str, name: str, kind: str, node: ast.AST, parent: str) -> PythonSymbol:
    return PythonSymbol(
        path=relative,
        name=name,
        kind=kind,
        line_number=getattr(node, "lineno", 1),
        end_line_number=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
        signature=_signature(node),
        docstring=ast.get_docstring(node) or "",
        parent=parent,
    )


def _signature(node: ast.AST) -> str:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    try:
        return f"({_args_to_text(node.args)})"
    except Exception:
        return ""


def _args_to_text(args: ast.arguments) -> str:
    try:
        text = ast.unparse(args)
    except Exception:
        parts = [arg.arg for arg in args.args]
        if args.vararg:
            parts.append("*" + args.vararg.arg)
        parts.extend(arg.arg for arg in args.kwonlyargs)
        if args.kwarg:
            parts.append("**" + args.kwarg.arg)
        text = ", ".join(parts)
    return text


def _source_line(source_lines: list[str], line_number: int) -> str:
    if line_number < 1 or line_number > len(source_lines):
        return ""
    return source_lines[line_number - 1].strip()


def _single_line(text: str) -> str:
    return " ".join(text.strip().split())[:300]


def _format_references(query: str, references: list[PythonReference], truncated: bool) -> str:
    lines = [f"可能引用 {query}:"]
    lines.extend(f"{reference.path}:L{reference.line_number} {reference.kind} {reference.line}" for reference in references)
    if truncated:
        lines.append("... 结果已截断")
    return "\n".join(lines)


def _format_symbol(symbol: PythonSymbol) -> str:
    return f"{symbol.path}:L{symbol.line_number}-{symbol.end_line_number} {symbol.kind} {symbol.name}"
