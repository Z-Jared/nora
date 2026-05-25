import subprocess
import tempfile
import unittest
from pathlib import Path

from mini_agent.git_tools import GitTools


class GitToolsTests(unittest.TestCase):
    def test_reports_non_git_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = GitTools(Path(tmpdir)).status()

        self.assertIn("not a git repository", result.lower())

    def test_reads_status_log_and_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            target = root / "README.md"
            target.write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)
            target.write_text("new\n", encoding="utf-8")
            git = GitTools(root)

            self.assertIn("README.md", git.status())
            self.assertIn("initial", git.log())
            self.assertIn("-old", git.diff("README.md"))

    def test_rejects_diff_path_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = GitTools(Path(tmpdir)).diff("../secret.txt")

        self.assertIn("拒绝查看 diff", result)

    def test_rejects_diff_for_sensitive_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            (root / ".env").write_text("SECRET=old\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", ".env"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "track env"], cwd=root, check=True, capture_output=True)
            (root / ".env").write_text("SECRET=new\n", encoding="utf-8")

            result = GitTools(root).diff(".env")
            full_diff = GitTools(root).diff()

        self.assertIn("拒绝查看 diff", result)
        self.assertIn("拒绝查看 diff", full_diff)
        self.assertNotIn("SECRET=new", full_diff)

    def test_reads_branch_and_staged_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            git = GitTools(root)
            git.stage_paths(["README.md"])

            self.assertTrue(git.current_branch().strip())
            self.assertIn("*", git.branches())
            self.assertIn("+changed", git.staged_diff())

    def test_stage_rejects_sensitive_and_outside_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            (root / ".env").write_text("secret", encoding="utf-8")
            git = GitTools(root)

            self.assertIn("拒绝暂存", git.stage_paths([".env"]))
            self.assertIn("拒绝暂存", git.stage_paths(["../outside.txt"]))

    def test_unstage_paths_removes_staged_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            git = GitTools(root)
            git.stage_paths(["README.md"])

            result = git.unstage_paths(["README.md"])

            self.assertIn("已取消暂存", result)
            self.assertEqual(git.staged_diff(), "没有 Git 输出。")

    def test_create_branch_validates_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            git = GitTools(root)

            self.assertIn("拒绝创建分支", git.create_branch("bad name"))
            self.assertIn("没有 Git 输出", git.create_branch("feature/test"))
            self.assertIn("feature/test", git.branches())

    def test_commit_staged_rejects_empty_message_and_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            git = GitTools(root)

            self.assertIn("message 不能为空", git.commit_staged(""))
            self.assertIn("没有已暂存", git.commit_staged("test"))

    def test_commit_staged_creates_local_commit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            git = GitTools(root)
            git.stage_paths(["README.md"])

            result = git.commit_staged("update readme")

            self.assertIn("已创建本地提交", result)
            self.assertIn("update readme", git.log(max_count=1))

    def test_commit_staged_rejects_sensitive_staged_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", ".env"], cwd=root, check=True)
            git = GitTools(root)

            result = git.commit_staged("commit env")

        self.assertIn("拒绝提交", result)
        self.assertIn(".env", result)

    def test_summarize_changes_includes_branch_status_and_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            git = GitTools(root)

            result = git.summarize_changes()

        self.assertIn("## branch", result)
        self.assertIn("## status", result)
        self.assertIn("## unstaged stat", result)
        self.assertIn("README.md", result)

    def test_review_staged_diff_reports_empty_and_present_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            git = GitTools(root)
            empty = git.review_staged_diff()
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            git.stage_paths(["README.md"])
            present = git.review_staged_diff()

        self.assertIn("没有 staged diff", empty)
        self.assertIn("staged diff 审查", present)
        self.assertIn("README.md", present)

    def test_check_before_commit_distinguishes_staged_and_unstaged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _init_git_repo(root)
            git = GitTools(root)
            no_staged = git.check_before_commit()
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            unstaged = git.check_before_commit()
            git.stage_paths(["README.md"])
            staged = git.check_before_commit()

        self.assertIn("staged changes: 无", no_staged)
        self.assertIn("unstaged/untracked changes: 有", unstaged)
        self.assertIn("staged changes: 有", staged)


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
