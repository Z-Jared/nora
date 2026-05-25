import tempfile
import unittest
from pathlib import Path

from mini_agent.rag import ProjectRAG
from mini_agent.tools import build_default_registry


class ProjectRAGTests(unittest.TestCase):
    def test_searches_project_text_files_by_keyword(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("agent tool calling architecture", encoding="utf-8")
            (root / ".env").write_text("secret", encoding="utf-8")
            rag = ProjectRAG(root)

            result = rag.search("tool architecture", max_results=3)

        self.assertIn("README.md", result)
        self.assertIn("tool calling architecture", result)
        self.assertNotIn(".env", result)

    def test_answers_with_project_context_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("agent supports tools", encoding="utf-8")
            rag = ProjectRAG(root)

            result = rag.context_for_question("what supports tools?")

        self.assertIn("问题: what supports tools?", result)
        self.assertIn("agent supports tools", result)

    def test_ranks_files_matching_more_terms_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "partial.md").write_text("tool " * 20, encoding="utf-8")
            (root / "complete.md").write_text("tool architecture", encoding="utf-8")
            rag = ProjectRAG(root)

            results = rag.search_results("tool architecture", max_results=2)

        self.assertEqual(results[0].path, "complete.md")

    def test_boosts_path_matches_and_reports_line_number(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "task_runner.py").write_text("nothing here", encoding="utf-8")
            (root / "other.py").write_text("task\nrunner\n", encoding="utf-8")
            rag = ProjectRAG(root)

            result = rag.search("task runner", max_results=1)

        self.assertIn("path=task_runner.py lines=1-1", result)

    def test_chunks_files_and_reports_line_ranges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lines = [f"filler {index}" for index in range(25)]
            lines[4] = "needle first"
            lines[16] = "needle second"
            (root / "notes.md").write_text("\n".join(lines), encoding="utf-8")
            rag = ProjectRAG(root, chunk_size=10, chunk_overlap=0)

            results = rag.search_results("needle", max_results=5)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].path, "notes.md")
        self.assertEqual(results[0].line_number, 1)
        self.assertEqual(results[0].end_line_number, 10)
        self.assertEqual(f"lines={results[0].line_number}-{results[0].end_line_number}", "lines=1-10")

    def test_include_paths_and_exclude_dirs_filter_rag_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "docs").mkdir()
            (root / "src" / "app.py").write_text("needle src", encoding="utf-8")
            (root / "docs" / "guide.md").write_text("needle docs", encoding="utf-8")
            included = ProjectRAG(root, include_paths=["src"]).search("needle")
            excluded = ProjectRAG(root, exclude_dirs=["src"]).search("needle")

        self.assertIn("src/app.py", included)
        self.assertNotIn("docs/guide.md", included)
        self.assertIn("docs/guide.md", excluded)
        self.assertNotIn("src/app.py", excluded)

    def test_registry_uses_configured_rag_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "docs").mkdir()
            (root / "src" / "app.py").write_text("needle src", encoding="utf-8")
            (root / "docs" / "guide.md").write_text("needle docs", encoding="utf-8")
            registry = build_default_registry(
                workspace_root=root,
                rag_include_paths=["src"],
                rag_chunk_size=10,
                rag_chunk_overlap=2,
            )

            result = registry.call("search_project_context", query="needle")

        self.assertIn("src/app.py", result)
        self.assertNotIn("docs/guide.md", result)

    def test_skips_sensitive_rag_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for dirname in ("data", "logs", ".git", "evals/.tmp"):
                (root / dirname).mkdir(parents=True)
                (root / dirname / "secret.md").write_text("needle", encoding="utf-8")
            (root / "public.md").write_text("needle", encoding="utf-8")
            rag = ProjectRAG(root)

            result = rag.search("needle", max_results=5)

        self.assertIn("public.md", result)
        self.assertNotIn("secret.md", result)
