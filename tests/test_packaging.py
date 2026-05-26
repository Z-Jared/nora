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
        self.assertIn('"nora-serve=mini_agent.app:serve"', setup_py)

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

    def test_install_sh_exists_and_contains_repo_url(self):
        install_sh = Path("install.sh")

        self.assertTrue(install_sh.exists(), "install.sh should exist")
        content = install_sh.read_text(encoding="utf-8")
        self.assertIn("git+https://github.com/Z-Jared/nora.git", content)

    def test_install_ps1_exists_and_contains_repo_url(self):
        install_ps1 = Path("install.ps1")

        self.assertTrue(install_ps1.exists(), "install.ps1 should exist")
        content = install_ps1.read_text(encoding="utf-8")
        self.assertIn("git+https://github.com/Z-Jared/nora.git", content)

    def test_install_sh_is_executable(self):
        import os
        install_sh = Path("install.sh")

        self.assertTrue(os.access(install_sh, os.X_OK), "install.sh should be executable")

    def test_readme_contains_curl_install_command(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("curl", readme)
        self.assertIn("install.sh", readme)
        self.assertIn("irm", readme)
        self.assertIn("install.ps1", readme)

    def test_readme_contains_nora_commands(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("nora", readme)
        self.assertIn("nora-serve", readme)

    def test_readme_contains_developer_install(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("pip install", readme)
        self.assertIn("-e .", readme)


if __name__ == "__main__":
    unittest.main()
