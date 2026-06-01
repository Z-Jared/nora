import subprocess
import tempfile
import unittest
from pathlib import Path

from mini_agent.context_compiler import ContextCompiler, ContextPack
from mini_agent.database import NoraDB
from mini_agent.memory_records import MemoryRecordStore
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


class ContextCompilerMemoryRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.store = MemoryRecordStore(db=self.db)
        self.compiler = ContextCompiler(
            self.root,
            memory_record_store=self.store,
        )

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_compile_includes_memory_records_by_default_query(self):
        self.store.create(kind="decision", title="Use SQLite", content="SQLite for local persistence")
        pack = self.compiler.compile("SQLite persistence", include_git_status=False, include_changed_files=False)

        titles = [s.title for s in pack.sections]
        self.assertIn("结构化记忆", titles)
        section = next(s for s in pack.sections if s.title == "结构化记忆")
        self.assertIn("Use SQLite", section.content)
        self.assertIn("[decision]", section.content)

    def test_compile_explicit_memory_query(self):
        self.store.create(kind="fact", title="Redis", content="Redis for caching layer")
        self.store.create(kind="decision", title="Postgres", content="Postgres for production DB")
        pack = self.compiler.compile("database", memory_query="Redis", include_git_status=False, include_changed_files=False)

        section = next(s for s in pack.sections if s.title == "结构化记忆")
        self.assertIn("Redis", section.content)
        self.assertNotIn("Postgres", section.content)

    def test_compile_disable_memory_records(self):
        self.store.create(kind="decision", title="Use SQLite", content="SQLite for persistence")
        pack = self.compiler.compile("SQLite", include_memory_records=False, include_git_status=False, include_changed_files=False)

        titles = [s.title for s in pack.sections]
        self.assertNotIn("结构化记忆", titles)

    def test_compile_no_memory_when_no_store(self):
        compiler = ContextCompiler(self.root)
        pack = compiler.compile("SQLite", include_git_status=False, include_changed_files=False)

        titles = [s.title for s in pack.sections]
        self.assertNotIn("结构化记忆", titles)

    def test_compile_no_memory_when_no_matches(self):
        self.store.create(kind="decision", title="Use SQLite", content="SQLite for persistence")
        pack = self.compiler.compile("xyznonexistent123", include_git_status=False, include_changed_files=False)

        titles = [s.title for s in pack.sections]
        self.assertNotIn("结构化记忆", titles)

    def test_compile_filters_unsafe_memory_records(self):
        self.db.conn.execute(
            "INSERT INTO memory_records (record_id, kind, scope, title, content, tags, source, confidence, related_task_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("mrec_bad", "note", "project", "OPENAI_API_KEY=sk-leaked", "Some content", "", "", 1.0, "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        self.db.conn.commit()
        self.store.create(kind="note", title="Normal note", content="Safe content here")
        pack = self.compiler.compile("Safe content", include_git_status=False, include_changed_files=False)

        section = next(s for s in pack.sections if s.title == "结构化记忆")
        self.assertNotIn("OPENAI_API_KEY", section.content)
        self.assertIn("Normal note", section.content)

    def test_compile_filters_unsafe_metadata(self):
        self.db.conn.execute(
            "INSERT INTO memory_records (record_id, kind, scope, title, content, tags, source, confidence, related_task_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("mrec_meta", "note", "project", "Config note", "Safe content", "OPENAI_API_KEY=secret", "", 1.0, "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        self.db.conn.commit()
        self.store.create(kind="note", title="Clean note", content="Clean metadata content")
        pack = self.compiler.compile("Clean metadata", include_git_status=False, include_changed_files=False)

        section = next(s for s in pack.sections if s.title == "结构化记忆")
        self.assertNotIn("OPENAI_API_KEY", section.content)
        self.assertIn("Clean note", section.content)

    def test_compile_memory_max_results_bounded(self):
        for i in range(5):
            self.store.create(kind="fact", title=f"Fact {i}", content=f"Content about topic X number {i}")
        pack = self.compiler.compile("topic X", memory_max_results=2, include_git_status=False, include_changed_files=False)

        section = next(s for s in pack.sections if s.title == "结构化记忆")
        count = section.content.count("[fact]")
        self.assertLessEqual(count, 2)

    def test_compile_memory_coexists_with_other_sections(self):
        self.store.create(kind="decision", title="Use SQLite", content="SQLite for local storage")
        (self.root / "README.md").write_text("# Test Project\n", encoding="utf-8")
        compiler = ContextCompiler(
            self.root,
            memory_record_store=self.store,
        )
        pack = compiler.compile(
            "SQLite",
            include_git_status=False,
            include_changed_files=False,
            include_knowledge_excerpts=["README.md"],
        )

        titles = [s.title for s in pack.sections]
        self.assertIn("结构化记忆", titles)
        self.assertIn("Knowledge: README.md", titles)

    def test_compile_memory_safe_metadata_still_appears(self):
        self.store.create(kind="decision", title="Use Postgres", content="Postgres for production", tags="review,approved", source="retro", related_task_id="dtask_42")
        pack = self.compiler.compile("Postgres", include_git_status=False, include_changed_files=False)

        section = next(s for s in pack.sections if s.title == "结构化记忆")
        self.assertIn("review", section.content)
        self.assertIn("approved", section.content)
        self.assertIn("source: retro", section.content)
        self.assertIn("task: dtask_42", section.content)

    def test_compile_memory_record_tool_integration(self):
        registry = build_default_registry(workspace_root=self.root, db=self.db)
        registry.call(
            "save_memory_record",
            kind="decision",
            title="Use Redis",
            content="Redis for caching",
        )

        result = registry.call(
            "compile_context_pack",
            task_description="Redis cache",
            include_git_status=False,
            include_changed_files=False,
        )

        self.assertIn("结构化记忆", result)
        self.assertIn("Use Redis", result)
        self.assertIn("[decision]", result)


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
