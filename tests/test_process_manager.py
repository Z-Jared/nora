import tempfile
import time
import unittest
from pathlib import Path

from mini_agent.process_manager import ProcessManager


class ProcessManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        self.profiles = {
            "echo_hello": ["python3", "-c", "print('hello')"],
            "sleep_short": ["python3", "-c", "import time; time.sleep(0.5); print('done')"],
        }

    def test_start_unknown_profile_rejected(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        result = pm.start("nonexistent")

        self.assertIn("拒绝启动", result)
        self.assertIn("未知 profile", result)

    def test_start_and_list_process(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        result = pm.start("echo_hello")

        self.assertIn("已启动后台进程", result)
        self.assertIn("proc_1", result)

        listing = pm.list_processes()
        self.assertIn("proc_1", listing)

    def test_max_processes_limit(self):
        pm = ProcessManager(self.root, profiles={"echo_hello": ["python3", "-c", "print('hi')"]}, max_processes=1)

        pm.start("echo_hello")
        result = pm.start("echo_hello")

        self.assertIn("拒绝启动", result)
        self.assertIn("最多同时运行", result)

    def test_status_returns_process_info(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        pm.start("echo_hello")
        time.sleep(0.2)

        status = pm.status("proc_1")
        self.assertIn("proc_1", status)
        self.assertIn("echo_hello", status)

    def test_status_unknown_process(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        result = pm.status("proc_999")

        self.assertIn("未找到", result)

    def test_read_output_captures_stdout(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        pm.start("echo_hello")
        time.sleep(0.5)

        output = pm.read_output("proc_1")
        self.assertIn("hello", output)

    def test_read_output_unknown_process(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        result = pm.read_output("proc_999")

        self.assertIn("未找到", result)

    def test_wait_for_output_matches_pattern(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        pm.start("sleep_short")

        result = pm.wait_for_output("proc_1", "done", timeout_seconds=5)
        self.assertIn("已匹配", result)

    def test_wait_for_output_empty_pattern_rejected(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        pm.start("echo_hello")
        result = pm.wait_for_output("proc_1", "", timeout_seconds=1)

        self.assertIn("拒绝等待", result)

    def test_wait_for_output_unknown_process(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        result = pm.wait_for_output("proc_999", "x", timeout_seconds=1)

        self.assertIn("未找到", result)

    def test_stop_terminates_process(self):
        pm = ProcessManager(self.root, profiles={
            "sleeper": ["python3", "-c", "import time; time.sleep(60)"],
        }, max_processes=2)

        pm.start("sleeper")
        time.sleep(0.2)

        result = pm.stop("proc_1")

        self.assertIn("已停止", result)
        status = pm.status("proc_1")
        self.assertIn("exited", status)

    def test_stop_unknown_process(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        result = pm.stop("proc_999")

        self.assertIn("未找到", result)

    def test_list_empty(self):
        pm = ProcessManager(self.root, profiles=self.profiles, max_processes=2)

        result = pm.list_processes()

        self.assertEqual(result, "没有后台进程。")

    def test_cleanup_terminates_all(self):
        pm = ProcessManager(self.root, profiles={
            "sleeper": ["python3", "-c", "import time; time.sleep(60)"],
        }, max_processes=2)

        pm.start("sleeper")
        time.sleep(0.2)

        pm.cleanup()

        status = pm.status("proc_1")
        self.assertIn("exited", status)


if __name__ == "__main__":
    unittest.main()
