import subprocess
import tempfile
import unittest
from pathlib import Path

from mini_agent.context_compiler import ContextCompiler, ContextPack
from mini_agent.rag import ProjectRAG
from mini_agent.symbols import PythonSymbolIndex
from mini_agent.tools import build_default_registry


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, capture_output=True)


def _write_and_commit(root: Path, rel_path: str, content: str) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", rel_path], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"add {rel_path}"], cwd=root, capture_output=True)


class ContextCompilerTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        _init_git_repo(self.root)
        _write_and_commit(self.root, "README.md", "# Test Project\nA test project for context compiler.\n")
        _write_and_commit(self.root, "main.py", "def hello():\n    return 'hello'\n\nif __name__ == '__main__':\n    print(hello())\n")
        _write_and_commit(self.root, "mini_agent/core.py", "class Agent:\n    def run(self, msg):\n        return msg\n\ndef helper():\n    pass\n")
        self.symbol_index = PythonSymbolIndex(self.root)
        self.rag = ProjectRAG(self.root)
        self.compiler = ContextCompiler(
            self.root,
            symbol_index=self.symbol_index,
            project_rag=self.rag,
        )

    def test_compile_basic_returns_pack(self):
        pack = self.compiler.compile("test task")

        self.assertIsInstance(pack, ContextPack)
        self.assertEqual(pack.task_description, "test task")

    def test_compile_includes_git_status(self):
        (self.root / "new_file.txt").write_text("new content")
        pack = self.compiler.compile("test", include_git_status=True)

        titles = [s.title for s in pack.sections]
        self.assertIn("Git Status", titles)

    def test_compile_excludes_git_status(self):
        pack = self.compiler.compile("test", include_git_status=False)

        titles = [s.title for s in pack.sections]
        self.assertNotIn("Git Status", titles)

    def test_compile_includes_changed_files(self):
        (self.root / "new_file.txt").write_text("new content")
        pack = self.compiler.compile("test", include_changed_files=True)

        titles = [s.title for s in pack.sections]
        self.assertIn("Changed Files", titles)

    def test_compile_includes_file_outline(self):
        pack = self.compiler.compile("test", include_file_outlines=["main.py"])

        titles = [s.title for s in pack.sections]
        self.assertIn("Outline: main.py", titles)
        outline_section = next(s for s in pack.sections if s.title == "Outline: main.py")
        self.assertIn("hello", outline_section.content)

    def test_compile_includes_nested_file_outline(self):
        pack = self.compiler.compile("test", include_file_outlines=["mini_agent/core.py"])

        titles = [s.title for s in pack.sections]
        self.assertIn("Outline: mini_agent/core.py", titles)
        outline_section = next(s for s in pack.sections if s.title == "Outline: mini_agent/core.py")
        self.assertIn("Agent", outline_section.content)
        self.assertIn("helper", outline_section.content)

    def test_compile_includes_knowledge_excerpt(self):
        pack = self.compiler.compile("test", include_knowledge_excerpts=["README.md"])

        titles = [s.title for s in pack.sections]
        self.assertIn("Knowledge: README.md", titles)
        knowledge_section = next(s for s in pack.sections if s.title == "Knowledge: README.md")
        self.assertIn("Test Project", knowledge_section.content)

    def test_compile_includes_rag_snippets(self):
        pack = self.compiler.compile("test", rag_query="hello")

        titles = [s.title for s in pack.sections]
        self.assertIn("RAG Snippets (auxiliary)", titles)

    def test_compile_no_rag_when_no_results(self):
        pack = self.compiler.compile("test", rag_query="xyznonexistent123")

        titles = [s.title for s in pack.sections]
        self.assertNotIn("RAG Snippets (auxiliary)", titles)

    def test_compile_rag_labeled_auxiliary(self):
        pack = self.compiler.compile("test", rag_query="hello")

        rag_section = next((s for s in pack.sections if "auxiliary" in s.title.lower()), None)
        self.assertIsNotNone(rag_section)

    def test_compile_respects_max_chars(self):
        compiler = ContextCompiler(
            self.root,
            symbol_index=self.symbol_index,
            project_rag=self.rag,
            max_chars=500,
        )
        pack = compiler.compile(
            "test",
            include_file_outlines=["main.py", "mini_agent/core.py"],
            include_knowledge_excerpts=["README.md"],
        )

        total = sum(len(s.content) for s in pack.sections)
        self.assertLessEqual(total, 600)

    def test_compile_sets_truncated_when_over_budget(self):
        big_content = "# Big File\n" + "x" * 500 + "\n"
        (self.root / "big.md").write_text(big_content)
        compiler = ContextCompiler(
            self.root,
            symbol_index=self.symbol_index,
            project_rag=self.rag,
            max_chars=200,
        )
        pack = compiler.compile("test", include_knowledge_excerpts=["big.md"])

        self.assertTrue(pack.truncated or pack.omitted_chars > 0)

    def test_compile_markdown_output(self):
        pack = self.compiler.compile("test task", include_git_status=False, include_changed_files=False,
                                     include_knowledge_excerpts=["README.md"])
        md = pack.to_markdown()

        self.assertIn("# Context Pack: test task", md)
        self.assertIn("## Knowledge: README.md", md)

    def test_compile_nonexistent_file_outline_skipped(self):
        pack = self.compiler.compile("test", include_file_outlines=["nonexistent.py"])

        titles = [s.title for s in pack.sections]
        self.assertNotIn("Outline: nonexistent.py", titles)

    def test_compile_nonexistent_knowledge_skipped(self):
        pack = self.compiler.compile("test", include_knowledge_excerpts=["nonexistent.md"])

        titles = [s.title for s in pack.sections]
        self.assertNotIn("Knowledge: nonexistent.md", titles)

    def test_compile_skips_denied_knowledge_paths(self):
        (self.root / ".env").write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data" / "private.md").write_text("secret data", encoding="utf-8")
        (self.root / "logs").mkdir(exist_ok=True)
        (self.root / "logs" / "trace.log").write_text("secret log", encoding="utf-8")

        pack = self.compiler.compile(
            "test",
            include_knowledge_excerpts=[".env", "data/private.md", "logs/trace.log"],
        )

        self.assertEqual(pack.sections, [])

    def test_compile_skips_denied_file_outline_paths(self):
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data" / "private.py").write_text("def secret():\n    pass\n", encoding="utf-8")

        pack = self.compiler.compile("test", include_file_outlines=["data/private.py"])

        self.assertEqual(pack.sections, [])

    def test_compile_sections_have_source(self):
        pack = self.compiler.compile("test", include_knowledge_excerpts=["README.md"])

        knowledge_section = next(s for s in pack.sections if s.title == "Knowledge: README.md")
        self.assertEqual(knowledge_section.source, "README.md")

    def test_compile_full_workflow(self):
        (self.root / "new_file.txt").write_text("new content")
        pack = self.compiler.compile(
            "implement context compiler",
            include_git_status=True,
            include_changed_files=True,
            include_file_outlines=["main.py"],
            include_knowledge_excerpts=["README.md"],
            rag_query="hello",
        )

        md = pack.to_markdown()
        self.assertIn("implement context compiler", md)
        self.assertGreater(len(pack.sections), 3)

    def test_context_pack_to_markdown_omit_note(self):
        compiler = ContextCompiler(
            self.root,
            symbol_index=self.symbol_index,
            max_chars=100,
        )
        pack = compiler.compile("test", include_knowledge_excerpts=["README.md"])
        md = pack.to_markdown()

        if pack.omitted_chars > 0:
            self.assertIn("omitted", md)

    def test_compile_no_sources_returns_empty_pack(self):
        pack = self.compiler.compile(
            "test",
            include_git_status=False,
            include_changed_files=False,
        )

        self.assertEqual(len(pack.sections), 0)
        self.assertEqual(pack.total_chars, 0)

    def test_compile_context_pack_tool_returns_markdown_string(self):
        registry = build_default_registry(workspace_root=self.root)

        result = registry.call(
            "compile_context_pack",
            task_description="test task",
            include_git_status=False,
            include_changed_files=False,
            include_knowledge_excerpts=["README.md"],
        )

        self.assertIsInstance(result, str)
        self.assertIn("# Context Pack: test task", result)
        self.assertIn("## Knowledge: README.md", result)


class ContextCompilerNoGitTests(unittest.TestCase):
    def test_compile_without_git_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Hello\n")
            compiler = ContextCompiler(root)
            pack = compiler.compile("test", include_knowledge_excerpts=["README.md"])

            self.assertIsInstance(pack, ContextPack)
            titles = [s.title for s in pack.sections]
            self.assertIn("Knowledge: README.md", titles)


if __name__ == "__main__":
    unittest.main()
