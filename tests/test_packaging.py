import unittest
from pathlib import Path


class PackagingTests(unittest.TestCase):
    def test_exposes_nora_console_command(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[project.scripts]", pyproject)
        self.assertIn('nora = "mini_agent.app:main"', pyproject)


if __name__ == "__main__":
    unittest.main()
