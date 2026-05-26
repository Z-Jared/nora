import tempfile
import unittest
from pathlib import Path

from mini_agent.git_tools import GitTools


class ValidateBranchNameTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        # Initialize a git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, capture_output=True)

    def test_empty_name_rejected(self):
        gt = GitTools(self.root)

        result = gt.create_branch("")

        self.assertIn("不能为空", result)

    def test_dash_prefix_rejected(self):
        gt = GitTools(self.root)

        result = gt.create_branch("-bad")

        self.assertIn("不能以 - 开头", result)

    def test_dotdot_rejected(self):
        gt = GitTools(self.root)

        result = gt.create_branch("a..b")

        self.assertIn("非法片段", result)

    def test_at_brace_rejected(self):
        gt = GitTools(self.root)

        result = gt.create_branch("a@{b")

        self.assertIn("非法片段", result)

    def test_dot_suffix_rejected(self):
        gt = GitTools(self.root)

        result = gt.create_branch("branch.")

        self.assertIn("结尾非法", result)

    def test_lock_suffix_rejected(self):
        gt = GitTools(self.root)

        result = gt.create_branch("branch.lock")

        self.assertIn("结尾非法", result)

    def test_invalid_chars_rejected(self):
        gt = GitTools(self.root)

        result = gt.create_branch("branch name")

        self.assertIn("非法字符", result)


class SafePathsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        import subprocess
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, capture_output=True)

    def test_empty_paths_rejected(self):
        gt = GitTools(self.root)

        result = gt.stage_paths([])

        self.assertIn("不能为空", result)

    def test_dot_path_rejected(self):
        gt = GitTools(self.root)

        result = gt.stage_paths(["."])

        self.assertIn("显式指定", result)

    def test_star_path_rejected(self):
        gt = GitTools(self.root)

        result = gt.stage_paths(["*"])

        self.assertIn("显式指定", result)

    def test_sensitive_path_rejected(self):
        gt = GitTools(self.root)

        result = gt.stage_paths([".env"])

        self.assertIn("非敏感路径", result)

    def test_absolute_path_rejected(self):
        gt = GitTools(self.root)

        result = gt.stage_paths(["/etc/passwd"])

        self.assertIn("非敏感路径", result)

    def test_data_dir_path_rejected(self):
        gt = GitTools(self.root)

        result = gt.stage_paths(["data/state.json"])

        self.assertIn("非敏感路径", result)


class CommitEdgeCasesTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        import subprocess
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, capture_output=True)

    def test_empty_message_rejected(self):
        gt = GitTools(self.root)

        result = gt.commit_staged("")

        self.assertIn("不能为空", result)

    def test_long_message_rejected(self):
        gt = GitTools(self.root)

        result = gt.commit_staged("x" * 10000)

        self.assertIn("最多", result)

    def test_no_staged_changes_rejected(self):
        gt = GitTools(self.root)

        result = gt.commit_staged("test commit")

        self.assertIn("没有已暂存的改动", result)


class UnstagePathsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        import subprocess
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, capture_output=True)

    def test_empty_paths_rejected(self):
        gt = GitTools(self.root)

        result = gt.unstage_paths([])

        self.assertIn("不能为空", result)

    def test_sensitive_path_rejected(self):
        gt = GitTools(self.root)

        result = gt.unstage_paths([".git/config"])

        self.assertIn("非敏感路径", result)


if __name__ == "__main__":
    unittest.main()
