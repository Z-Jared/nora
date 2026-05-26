import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class PackagingTests(unittest.TestCase):
    def test_pyproject_exposes_nora_console_command(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[project.scripts]", pyproject)
        self.assertIn('nora = "mini_agent.app:main"', pyproject)

    def test_setup_exposes_nora_console_command_for_legacy_pip(self):
        setup_py = Path("setup.py").read_text(encoding="utf-8")

        self.assertIn('name="nora-local-ai"', setup_py)
        self.assertIn('"nora=mini_agent.app:main"', setup_py)

    def test_main_delegates_to_app_entrypoint(self):
        fake_app = Mock()
        fake_app.main = Mock()

        with patch.dict(sys.modules, {"mini_agent.app": fake_app}):
            runpy.run_path("main.py", run_name="__main__")

        fake_app.main.assert_called_once_with()

    def test_pyproject_includes_static_package_data(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[tool.setuptools.package-data]", pyproject)
        self.assertIn("static/*.html", pyproject)

    def test_setup_includes_package_data(self):
        setup_py = Path("setup.py").read_text(encoding="utf-8")

        self.assertIn("package_data", setup_py)
        self.assertIn("static/*.html", setup_py)

    def test_static_index_html_exists(self):
        static_file = Path("mini_agent/static/index.html")

        self.assertTrue(static_file.exists(), "mini_agent/static/index.html should exist")


if __name__ == "__main__":
    unittest.main()
