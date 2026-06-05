import shutil
import shlex
from pathlib import Path
from typing import Callable, Optional

from mini_agent.git_tools import GitTools
from mini_agent.session import SessionStore
from mini_agent.settings import required_env_vars, env_alternatives


def _section_header(title: str) -> str:
    return f"─── {title} ───"


def _status_line(label: str, ok: bool) -> str:
    mark = "✓" if ok else "✗"
    return f"  {mark} {label}"


def _truncate_text(text: str, max_len: int = 120) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


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
            "=== Nora 已启动 ===",
            "本地优先，文件/Git/终端/浏览器等高风险工具会先确认。",
            "输入 / 查看命令菜单，输入 exit 或 quit 退出。",
            "",
        ]
        lines.append(_section_header("Status"))
        lines.append(_status_line("Nora ready", True))
        lines.append(_status_line("高风险工具需要确认", True))
        lines.append("")

        lines.append(_section_header("Workspace"))
        lines.append(f"Workspace: {self.root}")
        git = GitTools(self.root)
        branch = git.current_branch().strip()
        if branch and not branch.startswith(("fatal:", "Git 命令失败", "Git 命令超时", "没有 Git 输出")):
            lines.append(f"Branch: {branch}")
        lines.append("")

        lines.append(_section_header("Model"))
        if self.settings and getattr(self.settings, "is_llm_enabled", False):
            provider = getattr(self.settings, "provider", "")
            model = getattr(self.settings, "model", "")
            lines.append(f"LLM: {provider} / {model}")
        else:
            lines.append("LLM: disabled，本地规则模式")
        if self.settings:
            provider = getattr(self.settings, "provider", "")
            api_key = getattr(self.settings, "api_key", "")
            if api_key:
                lines.append(f"API key: configured ({provider})")
            else:
                env_vars = required_env_vars(provider)
                lines.append(f"API key: missing (需设置 {', '.join(env_vars)})")
        lines.append("")

        lines.append(_section_header("Tools"))
        try:
            tool_count = len(self.registry.to_openai_tools())
        except AttributeError:
            tool_count = "unknown"
        lines.append(f"Tools: {tool_count}")
        lines.append("")

        task_summary = self._task_backlog_summary()
        if task_summary:
            lines.append(_section_header("Tasks"))
            lines.append(f"  {task_summary}")
            lines.append("")

        worker_summary = self._worker_state_summary()
        if worker_summary:
            lines.append(_section_header("Workers"))
            lines.append(f"  {worker_summary}")
            lines.append("")

        lines.append(_section_header("Next"))
        lines.append("下一步: / 打开命令菜单；/wake 查看项目；/setup 检查配置")
        lines.append("常用命令: /wake  /setup  /model  /workers  /status  /test  /help")
        return "\n".join(lines)

    def _task_backlog_summary(self) -> str:
        """Read agent_tasks/BACKLOG.md and return a short summary line."""
        backlog_path = self.root / "agent_tasks" / "BACKLOG.md"
        if not backlog_path.exists():
            return ""
        try:
            text = backlog_path.read_text(encoding="utf-8")
        except OSError:
            return ""
        in_progress = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("### TASK-") and "✅" not in stripped:
                in_progress.append(stripped.lstrip("# ").split(":")[0].strip())
        if in_progress:
            return f"Active tasks: {', '.join(in_progress[:3])}"
        return ""

    def _worker_state_summary(self) -> str:
        """Read .ccb/ worker status files and return a short summary."""
        ccb_path = self.root / ".ccb"
        if not ccb_path.exists():
            return ""
        lines = []
        for agent in ("claude-a", "claude-b"):
            done_path = ccb_path / "workspaces" / agent / "agent_tasks" / f"{agent.split('-')[-1].upper()}_DONE.md"
            if done_path.exists():
                try:
                    content = done_path.read_text(encoding="utf-8")[:200]
                    if "ready for review" in content.lower() or "done" in content.lower()[:50]:
                        lines.append(f"{agent}: done")
                    else:
                        lines.append(f"{agent}: working")
                except OSError:
                    lines.append(f"{agent}: unknown")
            else:
                lines.append(f"{agent}: no done file")
        if lines:
            return "Workers: " + ", ".join(lines)
        return ""

    def _wake_panel(self) -> str:
        """Read project context files and output a concise wake panel."""
        lines = ["=== Nora Project Wake ===", ""]

        # Workspace & branch
        lines.append(_section_header("Workspace"))
        lines.append(f"Workspace: {self.root}")
        git = GitTools(self.root)
        branch = git.current_branch().strip()
        if branch and not branch.startswith(("fatal:", "Git 命令失败", "Git 命令超时", "没有 Git 输出")):
            lines.append(f"Branch: {branch}")
        else:
            lines.append("Branch: (not in git repo)")

        # Git status (brief)
        status = git.status()
        if status and not status.startswith(("Git 命令失败", "Git 命令超时", "没有 Git 输出")):
            status_lines = [l for l in status.splitlines() if l.strip()][:5]
            if status_lines:
                lines.append("")
                lines.append("Git status:")
                for sl in status_lines:
                    lines.append(f"  {sl}")

        # Provider / model
        lines.append("")
        lines.append(_section_header("Model"))
        if self.settings and getattr(self.settings, "is_llm_enabled", False):
            provider = getattr(self.settings, "provider", "")
            model = getattr(self.settings, "model", "")
            api_key = getattr(self.settings, "api_key", "")
            lines.append(f"Provider: {provider}")
            lines.append(f"Model: {model}")
            lines.append(f"API key: {'configured' if api_key else 'missing'}")
        else:
            lines.append("Provider: disabled (本地规则模式)")
            if self.settings:
                provider = getattr(self.settings, "provider", "")
                if provider:
                    env_vars = required_env_vars(provider)
                    lines.append(f"需设置: {', '.join(env_vars)}")

        # Project knowledge files
        lines.append("")
        lines.append(_section_header("Knowledge"))
        knowledge_files = [
            ("PROJECT_WAKEUP.md", "docs/knowledge/PROJECT_WAKEUP.md"),
            ("DECISIONS.md", "docs/knowledge/DECISIONS.md"),
            ("CHAT_INDEX.md", "docs/knowledge/CHAT_INDEX.md"),
            ("AGENTS.md", "AGENTS.md"),
        ]
        for label, relpath in knowledge_files:
            fpath = self.root / relpath
            if fpath.exists():
                lines.append(f"  ✓ {label}")
            else:
                lines.append(f"  ✗ {label} (missing)")

        # Agent tasks
        lines.append("")
        lines.append(_section_header("Tasks"))
        task_summary = self._task_backlog_summary()
        if task_summary:
            lines.append(f"  {task_summary}")
        else:
            lines.append("  Active tasks: none")

        # Worker state
        worker_summary = self._worker_state_summary()
        if worker_summary:
            lines.append(f"  {worker_summary}")

        # Recovery hints if things look wrong
        lines.append("")
        hints = []
        if not (self.root / ".git").exists():
            hints.append("未在 Git 项目中。请 cd 到 Nora 项目目录后重新启动。")
        if self.settings and not getattr(self.settings, "api_key", ""):
            provider = getattr(self.settings, "provider", "")
            if provider:
                env_vars = required_env_vars(provider)
                hints.append(f"模型未配置。请在 .env 中设置 {', '.join(env_vars)}。")
        if not (self.root / "agent_tasks").exists():
            hints.append("agent_tasks/ 目录不存在。请确认在正确的 Nora 项目目录中。")
        if hints:
            lines.append(_section_header("Recovery"))
            lines.append("提示:")
            for h in hints:
                lines.append(f"  - {h}")

        return "\n".join(lines)

    def _model_info(self) -> str:
        """Show current provider/model/base URL/key presence without leaking key values."""
        lines = ["=== Nora Model Configuration ===", ""]
        if not self.settings:
            lines.append("Settings 未配置。")
            lines.append("")
            lines.append("如需模型能力，请在 .env 中设置:")
            lines.append("  LLM_PROVIDER=openai-compatible")
            lines.append("  LLM_API_KEY=your-key")
            lines.append("  LLM_MODEL=gpt-4.1-mini")
            return "\n".join(lines)

        provider = getattr(self.settings, "provider", "")
        model = getattr(self.settings, "model", "")
        base_url = getattr(self.settings, "base_url", "")
        api_key = getattr(self.settings, "api_key", "")
        timeout = getattr(self.settings, "timeout_seconds", 60)
        enabled = getattr(self.settings, "is_llm_enabled", False)

        lines.append(f"Provider: {provider or '(not set)'}")
        lines.append(f"Model: {model or '(not set)'}")
        lines.append(f"Base URL: {base_url or '(not set)'}")
        lines.append(f"API key: {'configured' if api_key else 'missing'}")
        lines.append(f"Timeout: {timeout}s")
        lines.append(f"Enabled: {'yes' if enabled else 'no'}")

        # Diagnostics
        lines.append("")
        lines.append("Diagnostics:")
        if not provider:
            lines.append("  LLM_PROVIDER 未设置。")
        if not api_key:
            env_vars = required_env_vars(provider)
            lines.append(f"  API key 缺失。需设置: {', '.join(env_vars)}")
            alternatives = env_alternatives(provider)
            for primary, alt in alternatives.items():
                lines.append(f"    {primary} 也可用 {alt} 替代。")
        if not model:
            lines.append("  LLM_MODEL 未设置，将使用默认模型。")

        # Error recovery hints
        lines.append("")
        lines.append("常见问题:")
        lines.append("  401 Unauthorized → API key 无效或过期，请检查 .env")
        lines.append("  连接超时 → 检查网络或 base URL 是否正确")
        lines.append("  模型不存在 → 检查模型名称拼写和 provider 匹配")
        return "\n".join(lines)

    def _setup_info(self) -> str:
        """Show setup/config guidance without leaking key values."""
        lines = ["=== Nora Setup / Config ===", ""]

        if self.settings:
            provider = getattr(self.settings, "provider", "")
            model = getattr(self.settings, "model", "")
            base_url = getattr(self.settings, "base_url", "")
            api_key = getattr(self.settings, "api_key", "")
            timeout = getattr(self.settings, "timeout_seconds", 60)
            enabled = getattr(self.settings, "is_llm_enabled", False)

            lines.append("当前配置:")
            lines.append(f"  Provider: {provider or '(not set)'}")
            lines.append(f"  Model: {model or '(not set)'}")
            lines.append(f"  Base URL: {base_url or '(not set)'}")
            lines.append(f"  API key: {'configured' if api_key else 'missing'}")
            lines.append(f"  Timeout: {timeout}s")
            lines.append(f"  Enabled: {'yes' if enabled else 'no'}")
        else:
            lines.append("当前配置: Settings 未加载")
            provider = ""

        lines.append("")
        lines.append("各 Provider 配置键:")
        lines.append("  openai-compatible:")
        lines.append("    LLM_PROVIDER=openai-compatible")
        lines.append("    LLM_API_KEY=your-key  (或 OPENAI_API_KEY)")
        lines.append("    LLM_MODEL=gpt-4.1-mini")
        lines.append("    LLM_BASE_URL=https://api.openai.com/v1  (可选)")
        lines.append("")
        lines.append("  anthropic:")
        lines.append("    LLM_PROVIDER=anthropic")
        lines.append("    ANTHROPIC_API_KEY=your-key")
        lines.append("    ANTHROPIC_MODEL=claude-sonnet-4-5")
        lines.append("    ANTHROPIC_BASE_URL=https://api.anthropic.com/v1  (可选)")
        lines.append("")
        lines.append("  gemini:")
        lines.append("    LLM_PROVIDER=gemini")
        lines.append("    GEMINI_API_KEY=your-key")
        lines.append("    GEMINI_MODEL=gemini-2.5-pro")
        lines.append("    GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta  (可选)")

        lines.append("")
        lines.append("诊断:")
        if not provider:
            lines.append("  LLM_PROVIDER 未设置，默认 openai-compatible")
        if self.settings:
            api_key = getattr(self.settings, "api_key", "")
            model = getattr(self.settings, "model", "")
            if not api_key:
                env_vars = required_env_vars(provider)
                lines.append(f"  API key 缺失。需设置: {', '.join(env_vars)}")
                alternatives = env_alternatives(provider)
                for primary, alt in alternatives.items():
                    lines.append(f"    {primary} 也可用 {alt} 替代")
            if not model:
                lines.append("  LLM_MODEL 未设置，将使用默认模型")

        lines.append("")
        lines.append("常见问题排查:")
        lines.append("  401 Unauthorized → API key 无效或过期，请检查 .env")
        lines.append("  403 Forbidden → key 无权限，请检查 key 的访问范围")
        lines.append("  连接超时 → 检查网络或 base URL 是否正确")
        lines.append("  模型不存在 → 检查模型名称拼写和 provider 匹配")
        lines.append("  provider/model 不匹配 → openai-compatible 用 gpt-*，anthropic 用 claude-*，gemini 用 gemini-*")
        lines.append("  端口占用 → 关闭占用端口的进程或更换端口")
        lines.append("  频率超限 → 稍后重试或升级 API 计划")

        return "\n".join(lines)

    def _workers_status(self) -> str:
        """Show Claude A/B / CCB worker status from project files."""
        lines = ["=== Nora Worker Status ===", ""]

        ccb_path = self.root / ".ccb"
        if not ccb_path.exists():
            lines.append("未找到 .ccb/ 目录。Worker 状态不可用。")
            lines.append("")
            lines.append("这可能意味着:")
            lines.append("  - 不在 Nora CCB 项目目录中")
            lines.append("  - Worker 尚未初始化")
            return "\n".join(lines)

        # Check each worker
        for agent in ("claude-a", "claude-b"):
            workspace = ccb_path / "workspaces" / agent
            lines.append(f"--- {agent} ---")

            if not workspace.exists():
                lines.append(f"  Workspace: 不存在")
                lines.append("")
                continue

            lines.append(f"  Workspace: {workspace}")

            # Task file
            task_letter = agent.split("-")[-1].upper()
            task_path = workspace / "agent_tasks" / f"{task_letter}_TASK.md"
            done_path = workspace / "agent_tasks" / f"{task_letter}_DONE.md"

            if task_path.exists():
                try:
                    task_content = task_path.read_text(encoding="utf-8")[:300]
                    # Extract first heading or task line
                    for tl in task_content.splitlines():
                        tl = tl.strip()
                        if tl.startswith("#") or tl.startswith("TASK-"):
                            lines.append(f"  Task: {_truncate_text(tl, 80)}")
                            break
                    else:
                        lines.append(f"  Task: (file exists)")
                except OSError:
                    lines.append(f"  Task: (read error)")
            else:
                lines.append(f"  Task: 无任务文件")

            # Done file
            if done_path.exists():
                try:
                    done_content = done_path.read_text(encoding="utf-8")[:300]
                    if "ready for review" in done_content.lower():
                        lines.append(f"  Done: ✓ ready for PM review")
                    elif "done" in done_content.lower()[:50]:
                        lines.append(f"  Done: ✓ completed")
                    else:
                        lines.append(f"  Done: (file exists)")
                except OSError:
                    lines.append(f"  Done: (read error)")
            else:
                lines.append(f"  Done: 未完成")

            lines.append("")

        # PM inbox hint
        pm_inbox = self.root / "agent_tasks" / "PM_INBOX.md"
        if pm_inbox.exists():
            lines.append(f"PM inbox: {pm_inbox}")

        return "\n".join(lines)

    def _error_recovery_hint(self, error_text: str) -> str:
        """Return user-readable suggestions for common provider/config failures."""
        error_lower = error_text.lower()

        if "401" in error_text or "unauthorized" in error_lower:
            return "提示: API key 可能无效或过期。请检查 .env 中的 API key 是否正确。"
        if "403" in error_text or "forbidden" in error_lower:
            return "提示: API key 可能没有访问权限。请检查 key 的权限范围。"
        if "missing" in error_lower and "key" in error_lower:
            return "提示: 缺少 API key。请在 .env 中设置对应的 API key。"
        if "missing" in error_lower and "api" in error_lower:
            return "提示: 缺少 API key。请在 .env 中设置对应的 API key。"
        if "port" in error_lower and ("in use" in error_lower or "already" in error_lower):
            return "提示: 端口已被占用。请关闭占用该端口的进程或使用其他端口。"
        if "connection" in error_lower or "timeout" in error_lower:
            return "提示: 连接超时。请检查网络连接或 base URL 是否正确。"
        if "model" in error_lower and ("not found" in error_lower or "does not exist" in error_lower):
            return "提示: 模型不存在。请检查模型名称和 provider 是否匹配。"
        if "unsupported" in error_lower and "provider" in error_lower:
            return "提示: 不支持的 provider。请检查 LLM_PROVIDER 设置。"
        if "rate" in error_lower and "limit" in error_lower:
            return "提示: API 调用频率超限。请稍后重试。"
        if "quota" in error_lower or "billing" in error_lower:
            return "提示: API 配额或计费问题。请检查账户余额和使用限制。"
        return ""

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
            self._model_call_start()
            response = self._format_agent_response(self.agent.run(multiline))
            self._model_call_end()
            return self._append_recovery_hint(response)
        if text.startswith("/"):
            return self.handle_slash_command(text)
        self._model_call_start()
        response = self._format_agent_response(self.agent.run(text))
        self._model_call_end()
        return self._append_recovery_hint(response)

    def _model_call_start(self) -> None:
        self.output_func("✓ 已接收输入")
        self.output_func("⏳ 正在调用模型...")

    def _model_call_end(self) -> None:
        self.output_func("✓ 模型响应完成")

    def _append_recovery_hint(self, response: str) -> str:
        """Append error recovery hint if response contains common error patterns."""
        hint = self._error_recovery_hint(response)
        if hint:
            return f"{response}\n\n{hint}"
        return response

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

        if command == "/":
            return self._slash_menu()
        if command == "/help":
            return self._help()
        if command == "/wake":
            return self._wake_panel()
        if command == "/model":
            return self._model_info()
        if command in ("/setup", "/config"):
            return self._setup_info()
        if command == "/workers":
            return self._workers_status()
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

        return f"未知命令: {command}\n输入 / 查看命令菜单，或输入 /help 查看完整帮助。"

    def _slash_menu(self) -> str:
        """Show a compact command launcher for exact '/' input."""
        return "\n".join(
            [
                "Nora 命令菜单",
                "",
                "Start",
                "  /wake       项目状态面板",
                "  /setup      配置检查与排查指南",
                "  /model      当前模型配置和诊断",
                "",
                "Project",
                "  /status     当前 Git 状态",
                "  /diff       查看 Git diff",
                "  /test       运行项目测试",
                "  /tools      查看可用工具",
                "",
                "Workers",
                "  /workers    查看 Claude/CCB worker 状态",
                "",
                "Memory / Tasks / Context",
                "  /task       当前任务",
                "  /tasks      Durable tasks",
                "  /dashboard  Durable task 状态概览",
                "  /context    最近上下文摘要",
                "",
                "Diagnostics",
                "  /doctor     检查 workspace、Git、LLM、工具和 PATH",
                "  /logs       查看工具日志",
                "  /audit      工具调用安全审计摘要",
                "",
                "Help",
                "  /help       完整命令帮助",
                "  exit        退出 Nora",
            ]
        )

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
                "  /wake - 项目状态面板（新窗口推荐）",
                "  /setup - 完整配置检查与排查指南",
                "  /model - 查看当前模型配置和诊断",
                "  /workers - 查看 worker 状态",
                "  /status - 查看当前 Git 状态",
                "  /tools - 查看可用工具",
                "  /auto 3 总结 README 并说明项目能力",
                "",
                "状态与工具:",
                "  /help - 查看命令帮助",
                "  /wake - 项目状态面板",
                "  /setup - 完整配置检查（/config 别名）",
                "  /model - 模型配置和诊断",
                "  /workers - worker 状态",
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
