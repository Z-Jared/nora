import atexit
import os
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_PROFILES = {
    "static_server_8000": ["python3", "-m", "http.server", "8000"],
}


@dataclass
class ManagedProcess:
    id: str
    profile: str
    command: List[str]
    process: subprocess.Popen
    output: deque[str]
    started_at: float


class ProcessManager:
    def __init__(
        self,
        root: Path,
        profiles: Optional[Dict[str, List[str]]] = None,
        max_processes: int = 2,
        max_output_lines: int = 500,
    ):
        self.root = root.resolve()
        self.profiles = profiles or DEFAULT_PROFILES
        self.max_processes = max(1, min(max_processes, 5))
        self.max_output_lines = max(50, min(max_output_lines, 2000))
        self._processes: dict[str, ManagedProcess] = {}
        self._next_id = 1
        atexit.register(self.cleanup)

    def start(self, profile: str, reason: str = "") -> str:
        profile = profile.strip()
        if profile not in self.profiles:
            return f"拒绝启动后台进程: 未知 profile。可用 profile: {', '.join(sorted(self.profiles))}"
        if len(self._running_processes()) >= self.max_processes:
            return f"拒绝启动后台进程: 最多同时运行 {self.max_processes} 个进程。"

        process_id = f"proc_{self._next_id}"
        self._next_id += 1
        command = self.profiles[profile]
        output: deque[str] = deque(maxlen=self.max_output_lines)
        try:
            process = subprocess.Popen(
                command,
                cwd=self.root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False,
                start_new_session=True,
            )
        except OSError as error:
            return f"后台进程启动失败: {error}"

        managed = ManagedProcess(process_id, profile, command, process, output, time.time())
        self._processes[process_id] = managed
        thread = threading.Thread(target=self._drain_output, args=(managed,), daemon=True)
        thread.start()
        return f"已启动后台进程: {process_id} profile={profile} pid={process.pid}"

    def list_processes(self) -> str:
        if not self._processes:
            return "没有后台进程。"
        return "\n".join(self._format_process(process) for process in self._processes.values())

    def status(self, process_id: str) -> str:
        managed = self._processes.get(process_id.strip())
        if not managed:
            return f"未找到后台进程: {process_id}"
        return self._format_process(managed)

    def read_output(self, process_id: str, max_chars: int = 4000) -> str:
        managed = self._processes.get(process_id.strip())
        if not managed:
            return f"未找到后台进程: {process_id}"
        max_chars = max(200, min(max_chars, 20000))
        output = "".join(managed.output)
        return output[-max_chars:] if output else "暂无后台进程输出。"

    def wait_for_output(self, process_id: str, pattern: str, timeout_seconds: int = 10) -> str:
        managed = self._processes.get(process_id.strip())
        if not managed:
            return f"未找到后台进程: {process_id}"
        pattern = pattern.strip()
        if not pattern:
            return "拒绝等待输出: pattern 不能为空。"
        timeout_seconds = max(1, min(timeout_seconds, 30))
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            output = "".join(managed.output)
            if pattern in output:
                return f"已匹配后台进程输出: {pattern}"
            if managed.process.poll() is not None:
                return f"后台进程已退出，未匹配输出: {pattern}\n{self.read_output(process_id)}"
            time.sleep(0.1)
        return f"等待后台进程输出超时: {pattern}"

    def stop(self, process_id: str, reason: str = "") -> str:
        managed = self._processes.get(process_id.strip())
        if not managed:
            return f"未找到后台进程: {process_id}"
        if managed.process.poll() is None:
            self._terminate(managed)
        status = self._format_process(managed)
        return f"已停止后台进程: {process_id}\n{status}"

    def cleanup(self) -> None:
        for managed in list(self._processes.values()):
            if managed.process.poll() is None:
                self._terminate(managed)

    def _running_processes(self) -> list[ManagedProcess]:
        return [process for process in self._processes.values() if process.process.poll() is None]

    def _drain_output(self, managed: ManagedProcess) -> None:
        if managed.process.stdout is None:
            return
        try:
            for line in managed.process.stdout:
                managed.output.append(line)
        except ValueError:
            return

    def _format_process(self, managed: ManagedProcess) -> str:
        return_code = managed.process.poll()
        state = "running" if return_code is None else f"exited({return_code})"
        command = " ".join(managed.command)
        return f"{managed.id}: {state} profile={managed.profile} pid={managed.process.pid} command={command}"

    def _terminate(self, managed: ManagedProcess) -> None:
        try:
            os.killpg(managed.process.pid, signal.SIGTERM)
        except OSError:
            managed.process.terminate()
        try:
            managed.process.wait(timeout=3)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(managed.process.pid, signal.SIGKILL)
        except OSError:
            managed.process.kill()
        managed.process.wait(timeout=3)
