import shutil
import shlex
from pathlib import Path
from typing import Callable, Optional

from mini_agent.git_tools import GitTools
from mini_agent.session import SessionStore
from mini_agent.settings import required_env_vars, env_alternatives


class MiniAgentCLI:
    def __init__(
        self,
        agent,
        registry,
        settings=None,
        root: Optional[Path] = None,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        session_store: Optional[SessionStore] = None,
    ):
        self.agent = agent
        self.registry = registry
        self.settings = settings
        self.root = (root or Path.cwd()).resolve()
        self.input_func = input_func
        self.output_func = output_func
        self.should_exit = False
        self.session_store = session_store

    def run(self) -> None:
        self.output_func(self.banner())
        while not self.should_exit:
            try:
                user_input = self.input_func(self.prompt()).strip()
            except EOFError:
                self.output_func("")
                break

            result = self.handle_input(user_input)
            if result:
                self.output_func(result)

    def banner(self) -> str:
        lines = [
            "Nora 已启动。本地优先，文件/Git/终端/浏览器等高风险工具会先确认。",
            "输入 /help 查看命令，输入 exit 或 quit 退出。",
            f"Workspace: {self.root}",
        ]
        if self.settings and getattr(self.settings, "is_llm_enabled", False):
            lines.append(f"LLM: {self.settings.provider} / {self.settings.model}")
        else:
            lines.append("LLM: disabled，本地规则模式")
        try:
            lines.append(f"Tools: {len(self.registry.to_openai_tools())}")
        except AttributeError:
            pass
        return "\n".join(lines)

    def prompt(self) -> str:
        branch = GitTools(self.root).current_branch().strip()
        if branch and not branch.startswith(("fatal:", "Git 命令失败", "Git 命令超时", "没有 Git 输出")):
            return f"Nora({branch})> "
        return "Nora> "

    def handle_input(self, text: str) -> Optional[str]:
        text = text.strip()
        if text.lower() in {"exit", "quit", "/exit", "/quit"}:
            self.should_exit = True
            return None
        if not text:
            return None
        if text == "<<<":
            multiline = self.read_multiline(text)
            if not multiline:
                return None
            return self._format_agent_response(self.agent.run(multiline))
        if text.startswith("/"):
            return self.handle_slash_command(text)
        return self._format_agent_response(self.agent.run(text))

    def read_multiline(self, first_line: str = "") -> str:
        lines = []
        while True:
            try:
                line = self.input_func("... ")
            except EOFError:
                break
            if line.strip() == ">>>":
                break
            lines.append(line)
        return "\n".join(lines).strip()

    def handle_slash_command(self, text: str) -> str:
        try:
            parts = shlex.split(text)
        except ValueError as error:
            return f"命令解析失败: {error}"
        if not parts:
            return ""
        command = parts[0]
        args = parts[1:]

        if command == "/help":
            return self._help()
        if command == "/tools":
            return self.registry.describe()
        if command == "/permissions":
            return self.registry.call("list_tool_permissions")
        if command == "/doctor":
            return self.doctor()
        if command == "/status":
            return self.registry.call("git_status")
        if command == "/diff":
            return self.registry.call("git_diff", path=args[0] if args else "")
        if command == "/staged":
            return self.registry.call("git_staged_diff")
        if command == "/changes":
            return self.registry.call("git_summarize_changes")
        if command == "/review-staged":
            return self.registry.call("git_review_staged_diff")
        if command == "/check-commit":
            return self.registry.call("git_check_before_commit")
        if command == "/branch":
            return self.registry.call("git_current_branch")
        if command == "/log":
            count = self._optional_int(args, default=5, name="max_count")
            if isinstance(count, str):
                return count
            return self.registry.call("git_log", max_count=count)
        if command == "/symbols":
            query = " ".join(args) if args else ""
            return self.registry.call("list_python_symbols", query=query)
        if command == "/symbol":
            if not args:
                return "用法: /symbol <name>"
            return self.registry.call("describe_python_symbol", **{"name": " ".join(args)})
        if command == "/refs":
            if not args:
                return "用法: /refs <name>"
            return self.registry.call("find_python_references", **{"name": " ".join(args)})
        if command == "/outline":
            if len(args) != 1:
                return "用法: /outline <path>"
            return self.registry.call("outline_python_file", path=args[0])
        if command == "/test":
            return self.registry.call("run_project_tests")
        if command == "/repair":
            attempts = self._optional_int(args, default=2, name="max_attempts")
            if isinstance(attempts, str):
                return attempts
            return self.registry.call("run_repair_loop", max_attempts=attempts)
        if command == "/auto":
            if not args:
                return "用法: /auto [n] <goal>"
            max_steps = None
            goal_parts = args
            try:
                max_steps = int(args[0])
                goal_parts = args[1:]
            except ValueError:
                pass
            if not goal_parts:
                return "用法: /auto [n] <goal>"
            return self._format_agent_response(self.agent.run_autonomous(" ".join(goal_parts), max_steps=max_steps))
        if command == "/task":
            if not args:
                return self.registry.call("list_task")
            # /task <task_id> → get durable task by ID
            store = getattr(self.registry, "durable_task_store", None)
            if not store:
                return "Durable task 存储未配置。"
            task = store.get_task(args[0])
            if not task:
                return f"未找到 durable task: {args[0]}"
            import json
            return json.dumps(task.to_dict(), ensure_ascii=False, indent=2)
        if command == "/task-next":
            return self.registry.call("run_task_once")
        if command == "/task-history":
            count = self._optional_int(args, default=20, name="max_results")
            if isinstance(count, str):
                return count
            return self.registry.call("list_task_history", max_results=count)
        if command == "/task-search":
            if not args:
                return "用法: /task-search <query>"
            return self.registry.call("search_task_history", query=" ".join(args))
        if command == "/task-restore":
            if len(args) != 1:
                return "用法: /task-restore <task_id>"
            return self.registry.call("restore_task", history_id=args[0])
        if command == "/logs":
            count = self._optional_int(args, default=10, name="max_entries")
            if isinstance(count, str):
                return count
            return self.registry.call("view_tool_logs", max_entries=count)
        if command == "/audit":
            count = self._optional_int(args, default=50, name="max_entries")
            if isinstance(count, str):
                return count
            return self.registry.call("generate_audit_report", max_entries=count)
        if command == "/context":
            count = self._optional_int(args, default=20, name="max_results")
            if isinstance(count, str):
                return count
            return self.registry.call("list_context_summaries", max_results=count)
        if command == "/context-search":
            if not args:
                return "用法: /context-search <query>"
            return self.registry.call("search_context_summaries", query=" ".join(args))
        if command == "/processes":
            return self.registry.call("list_background_processes")
        if command == "/git-stage":
            if not args:
                return "用法: /git-stage <path...>"
            return self.registry.call("git_stage_paths", paths=args, reason="cli slash command")
        if command == "/git-unstage":
            if not args:
                return "用法: /git-unstage <path...>"
            return self.registry.call("git_unstage_paths", paths=args, reason="cli slash command")
        if command == "/git-commit":
            if not args:
                return "用法: /git-commit <message>"
            return self.registry.call("git_commit_staged", message=" ".join(args), reason="cli slash command")
        if command == "/git-branch-create":
            if len(args) != 1:
                return "用法: /git-branch-create <name>"
            return self.registry.call("git_create_branch", name=args[0], reason="cli slash command")
        if command == "/process-start":
            if len(args) != 1:
                return "用法: /process-start <profile>"
            return self.registry.call("start_background_process", profile=args[0], reason="cli slash command")
        if command == "/process-stop":
            if len(args) != 1:
                return "用法: /process-stop <process_id>"
            return self.registry.call("stop_background_process", process_id=args[0], reason="cli slash command")
        if command == "/session-save":
            if not self.session_store:
                return "会话存储未配置。"
            name = args[0] if args else ""
            return self.session_store.save(self.agent.memory, name=name)
        if command == "/session-load":
            if not self.session_store:
                return "会话存储未配置。"
            if not args:
                return "用法: /session-load <name>"
            return self.session_store.load(args[0], self.agent.memory)
        if command == "/session-list":
            if not self.session_store:
                return "会话存储未配置。"
            return self.session_store.list_sessions()
        if command == "/traces":
            count = self._optional_int(args, default=20, name="max_results")
            if isinstance(count, str):
                return count
            trace_store = getattr(self.registry, "trace_store", None)
            if not trace_store:
                return "Trace 存储未配置。"
            traces = trace_store.list_traces(max_results=count)
            if not traces:
                return "暂无运行 trace。"
            lines = [f"最近 {len(traces)} 条运行 trace:"]
            for t in traces:
                tools = len(t.get("tool_calls", []))
                fail = t.get("failure", "")
                fail_part = f" failure={fail[:40]}" if fail else ""
                lines.append(
                    f"  {t['trace_id']}  {t['status']}  {t['input_preview'][:50]}"
                    f"  tools={tools}{fail_part}"
                )
            return "\n".join(lines)
        if command == "/trace":
            if not args:
                return "用法: /trace <trace_id>"
            trace_store = getattr(self.registry, "trace_store", None)
            if not trace_store:
                return "Trace 存储未配置。"
            t = trace_store.get_trace(args[0])
            if not t:
                return f"未找到 trace: {args[0]}"
            import json
            return json.dumps(t, ensure_ascii=False, indent=2)
        if command in ("/durable-tasks", "/tasks"):
            count = self._optional_int(args, default=20, name="limit")
            if isinstance(count, str):
                return count
            store = getattr(self.registry, "durable_task_store", None)
            if not store:
                return "Durable task 存储未配置。"
            tasks = store.list_tasks(limit=count)
            if not tasks:
                return "暂无 durable tasks。"
            lines = [f"最近 {len(tasks)} 条 durable tasks:"]
            for t in tasks:
                cp = len(t.checkpoints)
                lines.append(
                    f"  {t.task_id}  {t.status}  step={t.current_step or '-'}"
                    f"  checkpoints={cp}  {t.goal[:60]}"
                )
            return "\n".join(lines)
        if command == "/dashboard":
            store = getattr(self.registry, "durable_task_store", None)
            if not store:
                return "Durable task 存储未配置。"
            tasks = store.list_tasks(limit=200)
            if not tasks:
                return "暂无 durable tasks。"
            from collections import Counter
            counts = Counter(t.status for t in tasks)
            lines = ["Durable Task Dashboard", ""]
            lines.append("状态分布:")
            for status in ("pending", "running", "paused", "blocked", "completed", "failed", "cancelled"):
                n = counts.get(status, 0)
                if n > 0:
                    lines.append(f"  {status}: {n}")
            lines.append(f"  总计: {len(tasks)}")
            running = [t for t in tasks if t.status == "running"]
            if running:
                lines.append("")
                lines.append(f"进行中的任务 ({len(running)}):")
                for t in running:
                    step = t.current_step or "-"
                    total = len(t.steps)
                    lines.append(
                        f"  {t.task_id}  step={step}/{total}  {t.goal[:50]}"
                    )
            completed = [t for t in tasks if t.status == "completed"]
            if completed:
                recent = completed[:5]
                lines.append("")
                lines.append(f"最近完成的任务 ({len(recent)}):")
                for t in recent:
                    lines.append(
                        f"  {t.task_id}  {t.goal[:50]}"
                    )
            failed = [t for t in tasks if t.status == "failed"]
            if failed:
                recent_fail = failed[:5]
                lines.append("")
                lines.append(f"失败的任务 ({len(recent_fail)}):")
                for t in recent_fail:
                    reason = t.failure_reason[:40] if t.failure_reason else "-"
                    lines.append(
                        f"  {t.task_id}  {t.goal[:40]}  reason={reason}"
                    )
            return "\n".join(lines)
        if command == "/durable-task":
            if not args:
                return "用法: /durable-task <task_id>"
            store = getattr(self.registry, "durable_task_store", None)
            if not store:
                return "Durable task 存储未配置。"
            task = store.get_task(args[0])
            if not task:
                return f"未找到 durable task: {args[0]}"
            import json
            return json.dumps(task.to_dict(), ensure_ascii=False, indent=2)

        return f"未知命令: {command}\n输入 /help 查看可用命令。"

    def doctor(self) -> str:
        lines = [
            "Nora doctor",
            f"workspace: {self.root}",
        ]
        suggestions = []
        git_status = GitTools(self.root).status()
        if "not a git repository" in git_status.lower() or git_status.startswith(("Git 命令失败", "Git 命令超时")):
            lines.append("git: unavailable")
            suggestions.append("进入 Git 项目目录后再启动 Nora，或先运行 git init。")
        else:
            lines.append("git: available")
        if self.settings and getattr(self.settings, "is_llm_enabled", False):
            lines.append(f"llm: enabled ({self.settings.provider} / {self.settings.model})")
        else:
            lines.append("llm: disabled")
            provider = getattr(self.settings, "provider", "") if self.settings else ""
            env_vars = required_env_vars(provider)
            suggestions.append(f"如需模型能力，请检查 .env 中的 {', '.join(env_vars)}。")
            alternatives = env_alternatives(provider)
            for primary, alt in alternatives.items():
                suggestions.append(f"{primary} 也可用 {alt} 替代。")
        try:
            lines.append(f"tools: {len(self.registry.to_openai_tools())}")
        except AttributeError:
            lines.append("tools: unknown")
        data_path = self.root / "data"
        logs_path = self.root / "logs"
        lines.append(f"data path: {data_path} ({'exists' if data_path.exists() else 'missing'})")
        if not data_path.exists():
            suggestions.append("data/ 缺失通常没关系，首次保存记忆、任务或工具结果时会生成。")
        lines.append(f"logs path: {logs_path} ({'exists' if logs_path.exists() else 'missing'})")
        if not logs_path.exists():
            suggestions.append("logs/ 缺失通常没关系，首次记录工具调用日志时会生成。")
        nora_path = shutil.which("nora")
        lines.append(f"nora command: {nora_path if nora_path else 'not found on PATH'}")
        if not nora_path:
            suggestions.append('将 Python user scripts 加入 PATH，例如 export PATH="$HOME/Library/Python/3.9/bin:$PATH"。')
        if suggestions:
            lines.append("suggestions:")
            lines.extend(f"- {suggestion}" for suggestion in suggestions)
        return "\n".join(lines)

    def _optional_int(self, args: list[str], default: int, name: str):
        if not args:
            return default
        if len(args) > 1:
            return f"参数过多: {name} 只接受一个整数。"
        try:
            return int(args[0])
        except ValueError:
            return f"参数错误: {name} 必须是整数。"

    def _format_agent_response(self, response: str) -> str:
        report = getattr(self.agent, "last_run_report", None)
        report_text = report.format() if report and hasattr(report, "format") else ""
        if report_text:
            response = f"{response}\n\n{report_text}"
        if "\n" not in response:
            return f"Agent: {response}"
        first, rest = response.split("\n", 1)
        return f"Agent: {first}\n{rest}"

    def _help(self) -> str:
        return "\n".join(
            [
                "Nora 命令帮助",
                "",
                "推荐开始:",
                "  /status - 查看当前 Git 状态",
                "  /tools - 查看可用工具",
                "  /auto 3 总结 README 并说明项目能力",
                "",
                "状态与工具:",
                "  /help - 查看命令帮助",
                "  /tools - 查看工具列表",
                "  /permissions - 查看工具权限",
                "  /doctor - 检查 workspace、Git、LLM、工具数量和 PATH",
                "  /logs [n] - 查看工具日志",
                "  /audit [n] - 生成工具调用安全审计摘要",
                "  /traces [n] - 查看最近运行 trace",
                "  /trace <trace_id> - 查看单条 trace 详情",
                "  /durable-tasks [n] - 查看最近 durable tasks",
                "  /durable-task <task_id> - 查看单条 durable task 详情",
                "  /tasks [n] - durable-tasks 的别名",
                "  /dashboard - Durable task 状态概览",
                "",
                "Git:",
                "  /status - 查看 Git 状态",
                "  /diff [path] - 查看 Git diff",
                "  /staged - 查看 staged diff",
                "  /changes - 汇总当前 Git 变更",
                "  /review-staged - 审查 staged diff",
                "  /check-commit - 提交前检查",
                "  /branch - 查看当前分支",
                "  /log [n] - 查看最近提交",
                "  /git-stage <path...> - 暂存路径，需要确认",
                "  /git-unstage <path...> - 取消暂存路径，需要确认",
                "  /git-commit <message> - 提交 staged 改动，需要确认",
                "  /git-branch-create <name> - 创建本地分支，需要确认",
                "",
                "代码理解与测试:",
                "  /symbols [query] - 列出 Python 符号",
                "  /symbol <name> - 查看 Python 符号详情",
                "  /refs <name> - 查找 Python 可能引用",
                "  /outline <path> - 生成 Python 文件 outline",
                "  /test - 运行项目测试",
                "  /repair [n] - 运行受控修复测试循环",
                "",
                "任务、记忆与上下文:",
                "  /task - 查看当前任务",
                "  /task <task_id> - 查看 durable task 详情",
                "  /task-next - 推进当前任务一步",
                "  /task-history [n] - 查看最近完成的任务历史",
                "  /task-search <query> - 搜索已完成任务历史",
                "  /task-restore <task_id> - 从历史恢复任务为当前任务",
                "  /context [n] - 列出上下文摘要",
                "  /context-search <query> - 搜索上下文摘要",
                "",
                "会话管理:",
                "  /session-save [name] - 保存当前会话",
                "  /session-load <name> - 恢复已保存的会话",
                "  /session-list - 列出已保存的会话",
                "",
                "后台进程与浏览器:",
                "  /processes - 列出后台进程",
                "  /process-start <profile> - 启动后台进程，需要确认",
                "  /process-stop <process_id> - 停止后台进程，需要确认",
                "",
                "自主执行:",
                "  /auto [n] <goal> - 受控自主执行，最多 n 步，高风险工具仍需确认",
                "",
                "输入:",
                "  <<< 开始多行输入，>>> 结束。",
                "  exit 或 quit 退出。",
            ]
        )
