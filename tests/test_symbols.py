import tempfile
import unittest
from pathlib import Path

from mini_agent.symbols import PythonSymbolIndex


class ListSymbolsTests(unittest.TestCase):
    def test_lists_symbols_in_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("def hello(): pass\nclass Foo: pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.list_symbols()

            self.assertIn("hello", result)
            self.assertIn("Foo", result)

    def test_filters_by_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("def hello(): pass\ndef world(): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.list_symbols(query="hello")

            self.assertIn("hello", result)
            self.assertNotIn("world", result)

    def test_no_symbols_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "empty.py").write_text("# no symbols\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.list_symbols()

            self.assertIn("没有找到", result)


class FindSymbolTests(unittest.TestCase):
    def test_finds_symbol_by_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("def hello(): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.find_symbol("hello")

            self.assertIn("hello", result)
            self.assertIn("function", result)

    def test_empty_name_returns_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = PythonSymbolIndex(Path(tmpdir))

            result = index.find_symbol("")

            self.assertIn("请提供", result)

    def test_no_match_returns_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("def hello(): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.find_symbol("nonexistent")

            self.assertIn("没有找到", result)

    def test_exact_match_sorted_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("def hello_world(): pass\ndef hello(): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.find_symbol("hello")

            lines = result.strip().split("\n")
            self.assertIn("hello", lines[0])
            self.assertNotIn("hello_world", lines[0])


class OutlineFileTests(unittest.TestCase):
    def test_generates_outline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text(
                "class Foo:\n    def bar(self): pass\ndef baz(): pass\n",
                encoding="utf-8",
            )
            index = PythonSymbolIndex(root)

            result = index.outline_file("mod.py")

            self.assertIn("outline", result)
            self.assertIn("Foo", result)
            self.assertIn("bar", result)
            self.assertIn("baz", result)

    def test_empty_path_returns_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = PythonSymbolIndex(Path(tmpdir))

            result = index.outline_file("")

            self.assertIn("请提供", result)

    def test_non_py_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "readme.txt").write_text("hello", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.outline_file("readme.txt")

            self.assertIn("Python 文件", result)

    def test_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index = PythonSymbolIndex(root)

            result = index.outline_file("missing.py")

            self.assertIn("不存在", result)

    def test_syntax_error_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "bad.py").write_text("def foo(\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.outline_file("bad.py")

            self.assertIn("语法错误", result)

    def test_path_outside_project_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = PythonSymbolIndex(Path(tmpdir))

            result = index.outline_file("../outside.py")

            self.assertIn("不在项目目录", result)


class DescribeSymbolTests(unittest.TestCase):
    def test_describes_symbol_with_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text(
                'def hello():\n    """A greeting."""\n    return "hi"\n',
                encoding="utf-8",
            )
            index = PythonSymbolIndex(root)

            result = index.describe_symbol("hello")

            self.assertIn("hello", result)
            self.assertIn("function", result)

    def test_empty_name_returns_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = PythonSymbolIndex(Path(tmpdir))

            result = index.describe_symbol("")

            self.assertIn("请提供", result)

    def test_no_match_returns_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("def hello(): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.describe_symbol("nonexistent")

            self.assertIn("没有找到", result)


class FindReferencesTests(unittest.TestCase):
    def test_finds_name_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("x = 1\ny = x + 1\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.find_references("x")

            self.assertIn("可能引用", result)
            self.assertIn("Name", result)

    def test_finds_attribute_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("obj.method()\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.find_references("method")

            self.assertIn("Attribute", result)

    def test_empty_name_returns_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = PythonSymbolIndex(Path(tmpdir))

            result = index.find_references("")

            self.assertIn("请提供", result)

    def test_dotted_name_searches_last_part(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.find_references("module.x")

            self.assertIn("x", result)

    def test_no_references_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.find_references("nonexistent")

            self.assertIn("没有找到", result)


class ModuleImportsTests(unittest.TestCase):
    def test_lists_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("import os\nfrom pathlib import Path\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.module_imports("mod.py")

            self.assertIn("import os", result)
            self.assertIn("from pathlib import Path", result)

    def test_empty_path_returns_hint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = PythonSymbolIndex(Path(tmpdir))

            result = index.module_imports("")

            self.assertIn("请提供", result)

    def test_non_py_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "readme.txt").write_text("hello", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.module_imports("readme.txt")

            self.assertIn("Python 文件", result)

    def test_no_imports_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.module_imports("mod.py")

            self.assertIn("没有找到 import", result)

    def test_syntax_error_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "bad.py").write_text("def foo(\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.module_imports("bad.py")

            self.assertIn("语法错误", result)

    def test_path_outside_project_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = PythonSymbolIndex(Path(tmpdir))

            result = index.module_imports("../outside.py")

            self.assertIn("不在项目目录", result)

    def test_relative_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("from . import helper\nfrom ..base import Base\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.module_imports("mod.py")

            self.assertIn("from . import helper", result)
            self.assertIn("from ..base import Base", result)

    def test_import_with_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("import numpy as np\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.module_imports("mod.py")

            self.assertIn("numpy as np", result)


class AsyncFunctionTests(unittest.TestCase):
    def test_detects_async_function(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("async def fetch(): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.list_symbols()

            self.assertIn("async function", result)

    def test_detects_async_method(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("class Svc:\n    async def run(self): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.list_symbols()

            self.assertIn("async method", result)


class NestedSymbolTests(unittest.TestCase):
    def test_nested_function_in_function(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "mod.py").write_text("def outer():\n    def inner(): pass\n", encoding="utf-8")
            index = PythonSymbolIndex(root)

            result = index.list_symbols()

            self.assertIn("outer", result)
            self.assertIn("inner", result)


if __name__ == "__main__":
    unittest.main()
