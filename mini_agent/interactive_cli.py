"""TTY/raw terminal interactive frontend for Nora."""

import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension, HSplit, Layout, Window
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import Frame, TextArea

from mini_agent.cli import MiniAgentCLI
from mini_agent.tools_common import ALLOW_ONCE, ALWAYS_ALLOW_SESSION, DENY, confirm_in_terminal


COMMAND_META = {
    "/audit": "审计报告",
    "/help": "命令索引",
    "/wake": "项目上下文",
    "/status": "Git 状态",
    "/diff": "查看改动",
    "/staged": "暂存改动",
    "/changes": "改动摘要",
    "/review-staged": "审查暂存",
    "/check-commit": "提交检查",
    "/branch": "当前分支",
    "/log": "提交记录",
    "/git-stage": "暂存文件",
    "/git-unstage": "取消暂存",
    "/git-commit": "提交改动",
    "/git-branch-create": "创建分支",
    "/test": "运行测试",
    "/tasks": "任务列表",
    "/task": "任务详情",
    "/task-next": "推进任务",
    "/task-history": "任务历史",
    "/task-search": "搜索任务",
    "/task-restore": "恢复任务",
    "/dashboard": "任务概览",
    "/durable-tasks": "持久任务",
    "/durable-task": "持久任务详情",
    "/auto": "自动执行任务",
    "/symbols": "符号列表",
    "/symbol": "符号详情",
    "/refs": "查找引用",
    "/outline": "文件大纲",
    "/repair": "修复循环",
    "/model": "模型设置",
    "/setup": "配置向导",
    "/config": "配置别名",
    "/workers": "A/B worker 状态",
    "/permissions": "权限策略",
    "/tools": "工具列表",
    "/doctor": "诊断环境",
    "/context": "上下文摘要",
    "/context-search": "搜索上下文",
    "/session-list": "会话列表",
    "/session-save": "保存会话",
    "/session-load": "恢复会话",
    "/traces": "Trace 列表",
    "/trace": "Trace 详情",
    "/logs": "工具日志",
    "/processes": "进程列表",
    "/process-start": "启动进程",
    "/process-stop": "停止进程",
    "/exit": "退出 Nora",
}
COMMAND_LAUNCHER_ORDER = [
    "/help",
    "/wake",
    "/status",
    "/diff",
    "/changes",
    "/test",
    "/tasks",
    "/auto",
    "/model",
    "/setup",
    "/workers",
    "/permissions",
    "/tools",
    "/doctor",
    "/exit",
]
COMMAND_PANEL_LIMIT = 8
SLASH_GROUPS = [
    ("Common", "常用操作", ["/help", "/wake", "/status", "/diff", "/changes", "/test", "/tasks", "/auto"]),
    ("Project", "项目与诊断", ["/wake", "/doctor", "/workers", "/model", "/setup", "/config"]),
    ("Git", "状态、改动、提交", ["/status", "/diff", "/staged", "/changes", "/git-stage", "/git-unstage", "/git-commit", "/git-branch-create", "/review-staged", "/check-commit", "/branch", "/log"]),
    ("Tasks", "任务与自动执行", ["/tasks", "/task", "/task-next", "/auto", "/task-history", "/task-search", "/task-restore", "/dashboard", "/durable-tasks", "/durable-task"]),
    ("Code", "代码浏览与测试", ["/symbols", "/symbol", "/refs", "/outline", "/test", "/repair"]),
    ("Session", "会话与上下文", ["/session-list", "/session-save", "/session-load", "/context", "/context-search", "/traces", "/trace"]),
    ("Tools", "工具、权限、日志", ["/tools", "/permissions", "/audit", "/logs"]),
    ("Processes", "后台进程", ["/processes", "/process-start", "/process-stop"]),
    ("Exit", "退出", ["/exit"]),
]
COMMAND_ARGUMENT_SPECS = {
    "/diff": [{"name": "path", "placeholder": "<path>", "meta": "可选文件路径", "type": "path"}],
    "/log": [{"name": "count", "placeholder": "<count>", "meta": "提交数量", "type": "limit"}],
    "/symbols": [{"name": "query", "placeholder": "<query>", "meta": "搜索符号", "type": "text"}],
    "/symbol": [{"name": "symbol", "placeholder": "<symbol>", "meta": "符号名称", "type": "text"}],
    "/refs": [{"name": "symbol", "placeholder": "<symbol>", "meta": "查找引用", "type": "text"}],
    "/outline": [{"name": "path", "placeholder": "<path>", "meta": "源码文件路径", "type": "path"}],
    "/test": [{"name": "command", "placeholder": "<command>", "meta": "测试命令，可留空", "type": "test_command"}],
    "/repair": [{"name": "attempts", "placeholder": "<attempts>", "meta": "最大修复轮数", "type": "attempts"}],
    "/auto": [
        {"name": "steps", "placeholder": "<steps>", "meta": "最大步骤数", "type": "steps"},
        {"name": "goal", "placeholder": "<goal>", "meta": "任务目标，直接输入", "type": "text"},
    ],
    "/task": [{"name": "id", "placeholder": "<task-id>", "meta": "任务 ID，可留空", "type": "task_id"}],
    "/task-history": [{"name": "limit", "placeholder": "<limit>", "meta": "结果数量", "type": "limit"}],
    "/task-search": [{"name": "query", "placeholder": "<query>", "meta": "搜索任务", "type": "text"}],
    "/task-restore": [{"name": "id", "placeholder": "<task-id>", "meta": "任务 ID", "type": "task_id"}],
    "/audit": [{"name": "limit", "placeholder": "<limit>", "meta": "结果数量", "type": "limit"}],
    "/context": [{"name": "limit", "placeholder": "<limit>", "meta": "摘要数量", "type": "limit"}],
    "/context-search": [{"name": "query", "placeholder": "<query>", "meta": "搜索上下文", "type": "text"}],
    "/git-stage": [{"name": "path", "placeholder": "<path>", "meta": "选择要暂存的文件", "type": "path"}],
    "/git-unstage": [{"name": "path", "placeholder": "<path>", "meta": "选择要取消暂存的文件", "type": "path"}],
    "/git-commit": [{"name": "message", "placeholder": "<message>", "meta": "提交信息，直接输入", "type": "text"}],
    "/git-branch-create": [{"name": "name", "placeholder": "<branch>", "meta": "新分支名", "type": "text"}],
    "/process-start": [{"name": "profile", "placeholder": "<profile>", "meta": "进程配置", "type": "process_profile"}],
    "/process-stop": [{"name": "id", "placeholder": "<process-id>", "meta": "进程 ID", "type": "process_id"}],
    "/session-save": [{"name": "name", "placeholder": "<name>", "meta": "会话名称", "type": "text"}],
    "/session-load": [{"name": "name", "placeholder": "<name>", "meta": "选择会话", "type": "session"}],
    "/logs": [{"name": "limit", "placeholder": "<limit>", "meta": "日志数量", "type": "limit"}],
    "/tasks": [{"name": "limit", "placeholder": "<limit>", "meta": "任务数量", "type": "limit"}],
    "/traces": [{"name": "limit", "placeholder": "<limit>", "meta": "Trace 数量", "type": "limit"}],
    "/trace": [{"name": "id", "placeholder": "<trace-id>", "meta": "Trace ID", "type": "trace_id"}],
    "/durable-tasks": [{"name": "limit", "placeholder": "<limit>", "meta": "结果数量", "type": "limit"}],
    "/durable-task": [{"name": "id", "placeholder": "<task-id>", "meta": "Durable task ID", "type": "task_id"}],
}

TTY_STYLE = Style.from_dict(
    {
        "nora.status": "#8f8577",
        "nora.accent": "#c7b17a",
        "nora.text": "#efe7d8",
        "nora.dim": "#b8ad9e",
        "nora.input": "bg:#171512 #efe7d8",
        "frame.border": "#6b5e4e",
        "frame.label": "#c7b17a",
        "completion-menu.completion": "bg:#252019 #b8ad9e",
        "completion-menu.completion.current": "bg:#3a3127 #efe7d8",
        "completion-menu.meta.completion": "bg:#252019 #9e9384",
        "completion-menu.meta.completion.current": "bg:#3a3127 #c7b17a",
    }
)


def _size_columns(size) -> int:
    columns = getattr(size, "columns", None)
    return columns if columns is not None else size[0]


def _size_lines(size) -> int:
    lines = getattr(size, "lines", None)
    return lines if lines is not None else size[1]


def _fit_line(text: str, width: Optional[int] = None) -> str:
    if width is None:
        columns = max(1, _size_columns(shutil.get_terminal_size(fallback=(100, 24))) - 1)
    else:
        columns = width
    if columns <= 0 or get_cwidth(text) <= columns:
        return text
    if columns <= 1:
        return ""
    clipped = []
    used = 0
    target = columns - 1
    for char in text:
        char_width = max(0, get_cwidth(char))
        if used + char_width > target:
            break
        clipped.append(char)
        used += char_width
    return "".join(clipped) + "…"


def _display_ljust(text: str, width: int) -> str:
    return text + (" " * max(0, width - get_cwidth(text)))


def _fixed_line(text: str, width: Optional[int] = None) -> str:
    if width is None:
        columns = max(1, _size_columns(shutil.get_terminal_size(fallback=(100, 24))) - 1)
    else:
        columns = max(1, width)
    return _display_ljust(_fit_line(text, columns), columns)


def _wrap_display_line(text: str, width: int) -> list[str]:
    width = max(1, width)
    if not text:
        return [""]
    lines = []
    current = []
    used = 0
    for char in text:
        char_width = max(0, get_cwidth(char))
        if current and used + char_width > width:
            lines.append("".join(current))
            current = []
            used = 0
        if char_width > width:
            lines.append(char)
            current = []
            used = 0
            continue
        current.append(char)
        used += char_width
    if current:
        lines.append("".join(current))
    return lines or [""]


def _wrap_display_lines(lines: list[str], width: int) -> list[str]:
    wrapped = []
    for line in lines:
        wrapped.extend(_wrap_display_line(line, width))
    return wrapped


def _pad_columns(left: str, right: str, width: int) -> str:
    available = max(1, width - get_cwidth(left) - 1)
    right = _fit_line(right, available)
    return f"{_display_ljust(left, 12)} {right}"


def _command_rows(prefix: str = "/") -> list[tuple[str, str]]:
    all_commands = MiniAgentCLI.slash_command_names()
    ordered = [command for command in COMMAND_LAUNCHER_ORDER if command in all_commands]
    ordered.extend(command for command in all_commands if command not in ordered and command != "/")
    matches = []
    for command in ordered:
        if command.lower().startswith(prefix.lower()):
            matches.append((command, COMMAND_META.get(command, "")))
    return matches


def _slash_launcher_rows(prefix: str = "/", group: Optional[str] = None) -> list[dict[str, str]]:
    if group:
        for group_label, _, commands in SLASH_GROUPS:
            if group_label == group:
                return [
                    {"kind": "command", "value": command, "label": command, "meta": COMMAND_META.get(command, "")}
                    for command in commands
                    if command in MiniAgentCLI.slash_command_names()
                ]
        return []
    if prefix == "/":
        return [
            {"kind": "group", "value": label, "label": label, "meta": meta}
            for label, meta, _ in SLASH_GROUPS
        ]
    return [
        {"kind": "command", "value": command, "label": command, "meta": meta}
        for command, meta in _command_rows(prefix)
    ]


def _argument_rows(
    command: Optional[str],
    step: int = 0,
    cli: Optional["InteractiveCLI"] = None,
) -> list[dict[str, str]]:
    if not command:
        return []
    specs = COMMAND_ARGUMENT_SPECS.get(command, [])
    if step >= len(specs):
        return []
    spec = specs[step]
    rows = []
    for value, meta in _argument_choices(command, spec, cli):
        rows.append({
            "kind": "argument",
            "value": value,
            "label": value,
            "meta": meta,
        })
    rows.append({
        "kind": "command",
        "value": command,
        "label": "直接运行",
        "meta": "不带参数执行",
    })
    return rows


def _argument_choices(command: str, spec: dict[str, str], cli: Optional["InteractiveCLI"]) -> list[tuple[str, str]]:
    placeholder = spec["placeholder"]
    arg_type = spec.get("type", "text")
    if arg_type == "steps":
        return [("3", "快速执行"), ("5", "均衡执行"), ("10", "更深入"), (placeholder, spec["meta"])]
    if arg_type == "attempts":
        return [("1", "单轮修复"), ("2", "默认修复"), ("3", "更深入"), (placeholder, spec["meta"])]
    if arg_type == "limit":
        return [("5", "少量结果"), ("10", "默认数量"), ("20", "更多结果"), (placeholder, spec["meta"])]
    if arg_type == "test_command":
        return [
            ("python3 -m unittest discover -s tests", "全量单测"),
            ("python3 evals/run_evals.py --filter tty_", "TTY eval"),
            ("git diff --check", "格式检查"),
            (placeholder, spec["meta"]),
        ]
    if arg_type == "path":
        return _path_choices(cli, fallback_meta=spec["meta"]) + [(placeholder, spec["meta"])]
    if arg_type == "task_id":
        return _task_choices(cli) + [(placeholder, spec["meta"])]
    if arg_type == "process_id":
        return _process_choices(cli) + [(placeholder, spec["meta"])]
    if arg_type == "process_profile":
        return _process_profile_choices(cli) + [(placeholder, spec["meta"])]
    if arg_type == "session":
        return _session_choices(cli) + [(placeholder, spec["meta"])]
    if arg_type == "trace_id":
        return _trace_choices(cli) + [(placeholder, spec["meta"])]
    return [(placeholder, spec["meta"])]


def _path_choices(cli: Optional["InteractiveCLI"], fallback_meta: str) -> list[tuple[str, str]]:
    if not cli:
        return []
    paths = []
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=cli.root,
            text=True,
            capture_output=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if len(line) >= 4:
                    path = line[3:].strip()
                    if " -> " in path:
                        path = path.split(" -> ", 1)[1]
                    if path:
                        paths.append((path, "changed file"))
    except Exception:
        pass
    if not paths:
        try:
            for path in cli.root.rglob("*"):
                if len(paths) >= 6:
                    break
                if _is_hidden_or_vendor_path(path.relative_to(cli.root)):
                    continue
                if path.is_file():
                    paths.append((str(path.relative_to(cli.root)), fallback_meta))
        except Exception:
            pass
    return paths[:6]


def _is_hidden_or_vendor_path(path: Path) -> bool:
    ignored = {".git", ".ccb", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules"}
    return any(part in ignored or part.startswith(".") for part in path.parts)


def _quote_arg(value: str) -> str:
    if value.startswith("<") and value.endswith(">"):
        return value
    if not value or any(char.isspace() for char in value):
        return "'" + value.replace("'", "'\"'\"'") + "'"
    return value


def _task_choices(cli: Optional["InteractiveCLI"]) -> list[tuple[str, str]]:
    store = getattr(getattr(cli, "registry", None), "durable_task_store", None)
    if not store:
        return []
    try:
        return [(task.task_id, f"{task.status} {task.goal[:24]}".strip()) for task in store.list_tasks(limit=6)]
    except Exception:
        return []


def _process_choices(cli: Optional["InteractiveCLI"]) -> list[tuple[str, str]]:
    manager = getattr(getattr(cli, "registry", None), "process_manager", None)
    if manager and hasattr(manager, "list_processes"):
        try:
            processes = manager.list_processes()
            rows = []
            for process in processes[:6]:
                process_id = str(process.get("id") or process.get("process_id") or "")
                if process_id:
                    rows.append((process_id, str(process.get("status") or "process")))
            return rows
        except Exception:
            return []
    return []


def _process_profile_choices(cli: Optional["InteractiveCLI"]) -> list[tuple[str, str]]:
    settings = getattr(cli, "settings", None)
    profiles = getattr(getattr(settings, "processes", None), "profiles", None)
    if isinstance(profiles, dict):
        return [(name, "configured profile") for name in list(profiles)[:6]]
    return []


def _session_choices(cli: Optional["InteractiveCLI"]) -> list[tuple[str, str]]:
    store = getattr(cli, "session_store", None)
    if store and hasattr(store, "list_sessions_structured"):
        try:
            return [(session["name"], f"{session.get('message_count', 0)} messages") for session in store.list_sessions_structured()[:6]]
        except Exception:
            return []
    return []


def _trace_choices(cli: Optional["InteractiveCLI"]) -> list[tuple[str, str]]:
    store = getattr(getattr(cli, "registry", None), "trace_store", None)
    if not store:
        return []
    try:
        return [(trace["trace_id"], trace.get("status", "trace")) for trace in store.list_traces(max_results=6)]
    except Exception:
        return []


def _command_template(command: str, args: Optional[list[str]] = None) -> str:
    specs = COMMAND_ARGUMENT_SPECS.get(command, [])
    if not specs:
        return command
    values = []
    args = args or []
    for index, spec in enumerate(specs):
        value = args[index] if index < len(args) else spec["placeholder"]
        values.append(_quote_arg(value))
    return f"{command} {' '.join(values)}"


def _is_exact_slash_command(text: str) -> bool:
    stripped = text.strip()
    return stripped != "/" and stripped in MiniAgentCLI.slash_command_names()


def _is_exact_argument_command(text: str) -> bool:
    stripped = text.strip()
    return stripped in COMMAND_ARGUMENT_SPECS and stripped in MiniAgentCLI.slash_command_names()


def _join_left_right(left: str, right: str, width: Optional[int] = None) -> str:
    columns = width if width is not None else max(1, _size_columns(shutil.get_terminal_size(fallback=(100, 24))) - 1)
    right_width = get_cwidth(right)
    if right_width + 2 >= columns:
        return _fit_line(right, columns)
    left_width = max(1, columns - right_width - 2)
    left = _fit_line(left, left_width)
    gap = max(2, columns - get_cwidth(left) - right_width)
    return f"{left}{' ' * gap}{right}"


def _light_panel(title: str, body_lines: list[str], width: int = 52) -> str:
    lines = [_fit_line(title, width)]
    for line in body_lines:
        lines.append(_fit_line(line, width))
    return "\n".join(lines)


def _render_fixed_lines(lines: list[str], style_for_line, width: Optional[int] = None):
    fragments = []
    columns = width if width is not None else _size_columns(shutil.get_terminal_size(fallback=(100, 24)))
    for line in lines:
        fragments.append((style_for_line(line), _fixed_line(line, columns) + "\n"))
    return fragments


class SlashCompleter(Completer):
    """Complete Nora slash commands for prefixes like /, /m, and /mo."""

    def __init__(self, commands: list[str]):
        preferred = [command for command in COMMAND_META if command in commands]
        remaining = sorted(command for command in commands if command not in COMMAND_META)
        self.commands = preferred + remaining

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        for command in self.match(text):
            yield Completion(
                command,
                start_position=-len(text),
                display=command,
                display_meta=COMMAND_META.get(command, ""),
                style="fg:#efe7d8",
                selected_style="bg:#3a3127 fg:#efe7d8",
            )

    def match(self, text: str) -> list[str]:
        if not text.startswith("/"):
            return []
        prefix = text.lower()
        return [
            command
            for command in self.commands
            if command.lower().startswith(prefix) and command.lower() != prefix
        ]


_SESSION_ALLOWED_TOOLS: set[str] = set()


def _parse_approval_prompt(prompt_text: str) -> dict[str, str]:
    tool_name = _tool_name_from_confirmation(prompt_text) or "tool"
    permission = ""
    reason = ""
    action = ""
    for line in prompt_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("权限:"):
            permission = stripped.replace("权限:", "", 1).strip()
        elif stripped.startswith("原因:"):
            reason = stripped.replace("原因:", "", 1).strip()
        elif stripped.startswith("动作:"):
            action = stripped.replace("动作:", "", 1).strip()
        elif stripped.startswith("执行命令:"):
            action = stripped.replace("执行命令:", "", 1).strip()
        elif ":" in stripped and not action:
            left, right = stripped.split(":", 1)
            if left in {"写入文件", "替换文件", "应用 patch", "应用多文件 patch"}:
                action = f"{left}: {right.strip()}"
    category, risk = _permission_parts(permission)
    return {
        "tool": tool_name,
        "permission": permission,
        "category": category,
        "risk": risk,
        "reason": reason,
        "action": action,
    }


def _approval_scope_key(prompt_text: str) -> str:
    details = _parse_approval_prompt(prompt_text)
    return "|".join([
        details["tool"],
        details["permission"],
        details["action"],
    ])


def _permission_parts(permission: str) -> tuple[str, str]:
    raw = permission.split(",", 1)[0].strip()
    if "/" in raw:
        category, risk = raw.split("/", 1)
        return category.strip(), risk.strip()
    return raw, ""


def _approval_default_index(prompt_text: str) -> int:
    details = _parse_approval_prompt(prompt_text)
    risk = details["risk"].lower()
    if risk in {"execute", "write", "delete", "commit", "network"}:
        return 1
    return 0


def _tool_name_from_confirmation(prompt_text: str) -> str:
    match = re.search(r"工具需要确认:\s*([^\n]+)", prompt_text)
    if match:
        return match.group(1).strip()
    match = re.search(r"Tool approval\s*:\s*([^\n]+)", prompt_text)
    if match:
        return match.group(1).strip()
    return ""


def selectable_confirm(prompt_text: str) -> bool:
    """TTY approval selector with non-TTY y/N fallback."""
    approval_scope = _approval_scope_key(prompt_text)
    if approval_scope and approval_scope in _SESSION_ALLOWED_TOOLS:
        return True
    if not sys.stdout.isatty():
        return confirm_in_terminal(prompt_text)
    try:
        result = _run_approval_card(prompt_text)
        if result == "session":
            if approval_scope:
                _SESSION_ALLOWED_TOOLS.add(approval_scope)
            return True
        return bool(result)
    except Exception:
        return confirm_in_terminal(prompt_text)


def _approval_text(prompt_text: str) -> str:
    details = _parse_approval_prompt(prompt_text)
    risk_label = details["risk"] or "confirm"
    category = details["category"] or "tool"
    body = [
        f"{details['tool']}  {risk_label}",
        f"scope: {category}",
    ]
    if details["action"]:
        body.append(f"action: {_fit_line(details['action'], 60)}")
    if details["reason"]:
        body.append(f"why: {_fit_line(details['reason'], 64)}")
    if risk_label in {"execute", "write", "delete", "commit", "network"}:
        body.append("risk: can change files, run commands, or affect external state")
    return _light_panel("Tool approval", body, width=72)


def _approval_lines(prompt_text: str, selected: int = 0) -> list[str]:
    choices = [
        ALLOW_ONCE.label,
        DENY.label,
        "Always allow this action this session",
    ]
    body = _approval_text(prompt_text).splitlines()
    for index, label in enumerate(choices):
        marker = ">" if index == selected else " "
        body.append(f"{marker} {label}")
    body.append("Esc/Ctrl-C deny   ↑↓ select   Enter confirm")
    return body


def _approval_panel_height() -> int:
    return 10


def _run_approval_card(prompt_text: str):
    selected = {"index": _approval_default_index(prompt_text)}
    choices = [ALLOW_ONCE.value, DENY.value, "session"]
    bindings = KeyBindings()

    def render():
        fragments = []
        for line in _approval_lines(prompt_text, selected["index"]):
            style = "class:nora.accent" if line.startswith("> ") else "class:nora.dim"
            if line.startswith("+") or line.startswith("|") or line.startswith("Esc"):
                style = "class:nora.status"
            fragments.append((style, line + "\n"))
        return fragments

    @bindings.add("up")
    def _(event):
        selected["index"] = (selected["index"] - 1) % len(choices)

    @bindings.add("down")
    @bindings.add("tab")
    def _(event):
        selected["index"] = (selected["index"] + 1) % len(choices)

    @bindings.add("enter")
    def _(event):
        event.app.exit(result=choices[selected["index"]])

    @bindings.add("escape")
    @bindings.add("c-c")
    def _(event):
        event.app.exit(result=False)

    app = Application(
        layout=Layout(HSplit([Window(FormattedTextControl(render), always_hide_cursor=True)])),
        key_bindings=bindings,
        style=TTY_STYLE,
        full_screen=False,
        erase_when_done=False,
    )
    return app.run()


class InteractiveCLI:
    """TTY-aware frontend that delegates command semantics to MiniAgentCLI."""

    def __init__(self, agent, registry, settings=None, root: Path = None, session_store=None):
        registry.confirm_action = self._confirm_action
        self._status_events: list[str] = []
        self.cli = MiniAgentCLI(
            agent,
            registry,
            settings=settings,
            root=root or Path.cwd(),
            output_func=self._status_output,
            session_store=session_store,
        )
        self.root = self.cli.root
        self.registry = registry
        self.session_store = session_store
        self.settings = settings
        self.completer = SlashCompleter(MiniAgentCLI.slash_command_names())
        self.app: Optional[Application] = None
        self._input_frame = None
        self._transcript: list[str] = []
        self._restored_session_notice: list[str] = []
        self._hydrate_transcript_from_memory()
        self._activity_lines: list[str] = []
        self._streaming_answer = ""
        self._current_input = ""
        self._status_message = ""
        self._approval_state = None
        self._worker_thread: Optional[threading.Thread] = None
        self._active_turn_id = 0
        self._next_turn_id = 0
        self._cancelled_turn_ids: set[int] = set()
        self._slash_selected = 0
        self._slash_group: Optional[str] = None
        self._slash_command: Optional[str] = None
        self._slash_arg_step = 0
        self._slash_args: list[str] = []
        self._body_scroll_offset = 0
        self._input_history: list[str] = []
        self._history_index: Optional[int] = None
        self._history_draft = ""
        self._is_working = False

    def _hydrate_transcript_from_memory(self, max_messages: int = 6, preview: bool = True) -> None:
        messages = []
        memory = getattr(getattr(self, "cli", None), "agent", None)
        memory = getattr(memory, "memory", None)
        if memory and hasattr(memory, "messages"):
            try:
                messages = memory.messages()[-max_messages:]
            except Exception:
                messages = []
        if not messages:
            return
        restored = getattr(self.cli, "restored_session_message_count", 0)
        if restored and preview:
            preview = self._restored_session_preview(messages, restored)
            if preview:
                self._restored_session_notice = preview
            return
        for message in messages:
            role = message.get("role")
            content = self._clip_restored_content(str(message.get("content") or "").strip())
            if not content:
                continue
            if role == "user":
                self._transcript.append(f"> {content}")
            elif role == "assistant":
                self._transcript.append(content)

    def _restored_session_preview(self, messages: list[dict], restored: int) -> list[str]:
        user_text = ""
        assistant_text = ""
        for index in range(len(messages) - 1, -1, -1):
            message = messages[index]
            if message.get("role") != "assistant":
                continue
            content = self._clip_restored_content(str(message.get("content") or "").strip())
            if not content or self._is_low_value_restored_content(content):
                continue
            assistant_text = content
            for user_index in range(index - 1, -1, -1):
                user_message = messages[user_index]
                if user_message.get("role") != "user":
                    continue
                user_content = self._clip_restored_content(str(user_message.get("content") or "").strip())
                if user_content and not self._is_low_value_restored_content(user_content):
                    user_text = user_content
                    break
            break
        return [
            f"restored previous session ({restored} messages) · /session-load to view"
        ]

    def _clip_restored_content(self, content: str, max_lines: int = 5, max_chars: int = 900) -> str:
        lines = [
            line
            for line in content.splitlines()
            if not self._is_internal_restored_line(line)
        ]
        clipped = False
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            clipped = True
        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars].rstrip()
            clipped = True
        if clipped:
            text = f"{text}\n... restored content truncated; use Ctrl-Up to scroll or /session-load for full session"
        return text

    def _is_internal_restored_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        return (
            "DSML" in stripped
            or stripped.startswith("<tool_")
            or stripped.startswith("</tool_")
            or stripped.startswith("<function")
            or stripped.startswith("</function")
        )

    def _is_low_value_restored_content(self, content: str) -> bool:
        text = content.strip()
        lower = text.lower()
        if not text:
            return True
        if text in {"/exit", "exit", "quit"}:
            return True
        if text.endswith("/exit") and text != "/exit":
            return True
        if text in {"好的，再见！", "好的，再见", "再见！", "再见"}:
            return True
        return (
            "codec can't decode" in lower
            or "traceback (most recent call last)" in lower
            or lower.startswith("error:")
            or lower.startswith("exception:")
        )

    def _one_line_preview(self, content: str, max_width: int) -> str:
        collapsed = re.sub(r"\s+", " ", content).strip()
        return _fit_line(collapsed, max_width)

    def _status_output(self, text: str) -> None:
        if text == "Working...":
            message = "status: thinking"
            if self.app:
                self._status_events.append(message)
                self._status_message = message
                self.app.invalidate()
            else:
                self._show_status(message)
        elif text == "Done.":
            if self.app:
                self._status_events.append("Done.")
                self._status_message = ""
                self.app.invalidate()
            else:
                self._clear_status()

    def _show_status(self, text: str) -> None:
        self._status_events.append(text)
        sys.stdout.write(f"\r{text}")
        sys.stdout.flush()

    def _clear_status(self) -> None:
        self._status_events.append("Done.")
        sys.stdout.write("\r" + (" " * 24) + "\r")
        sys.stdout.flush()

    def _make_bindings(self) -> KeyBindings:
        bindings = KeyBindings()
        approval_active = Condition(lambda: self._approval_state is not None)
        approval_inactive = ~approval_active
        slash_active = Condition(lambda: self._slash_active())

        @bindings.add("/", filter=approval_inactive)
        def _(event):
            event.app.current_buffer.insert_text("/")

        @bindings.add("up", filter=approval_active, eager=True)
        def _(event):
            self._move_approval(-1)

        @bindings.add("up", filter=slash_active, eager=True)
        def _(event):
            self._move_slash(-1)

        @bindings.add("down", filter=approval_active, eager=True)
        def _(event):
            self._move_approval(1)

        @bindings.add("down", filter=slash_active, eager=True)
        def _(event):
            self._move_slash(1)

        @bindings.add("tab", filter=approval_active, eager=True)
        def _(event):
            self._move_approval(1)

        @bindings.add("tab", filter=slash_active, eager=True)
        def _(event):
            self._move_slash(1)

        @bindings.add("tab", filter=approval_inactive & ~slash_active)
        def _(event):
            buffer = event.app.current_buffer
            text = buffer.document.text_before_cursor
            matches = self.completer.match(text)
            if len(matches) == 1:
                buffer.delete_before_cursor(count=len(text))
                buffer.insert_text(matches[0])
            elif matches:
                buffer.start_completion(select_first=True)
            else:
                buffer.insert_text("\t")

        @bindings.add("enter", filter=approval_active, eager=True)
        def _(event):
            self._resolve_approval()

        @bindings.add("enter", filter=slash_active, eager=True)
        def _(event):
            self._accept_slash_selection(event)

        @bindings.add("escape", filter=approval_active, eager=True)
        def _(event):
            self._resolve_approval(False)

        @bindings.add("c-c", filter=approval_active, eager=True)
        def _(event):
            self._resolve_approval(False)

        @bindings.add("escape", filter=approval_inactive)
        def _(event):
            self._handle_escape(event)

        @bindings.add("pageup", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("c-b", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("c-up", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("escape", "[", "5", "~", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("pagedown", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("c-f", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("c-down", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("escape", "[", "6", "~", filter=approval_inactive & ~slash_active, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("c-c", filter=approval_inactive)
        def _(event):
            self._handle_interrupt(event)

        @bindings.add("c-d", filter=approval_inactive)
        def _(event):
            self._handle_exit(event)

        return bindings

    def _make_input_bindings(self) -> KeyBindings:
        bindings = KeyBindings()
        approval_inactive = Condition(lambda: self._approval_state is None)
        slash_inactive = Condition(lambda: not self._slash_active())

        @bindings.add("pageup", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("escape", "[", "5", "~", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("c-b", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("c-up", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(-1)

        @bindings.add("pagedown", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("escape", "[", "6", "~", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("c-f", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("c-down", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._scroll_body(1)

        @bindings.add("up", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._move_input_history(event.app.current_buffer, -1)

        @bindings.add("down", filter=approval_inactive & slash_inactive, eager=True)
        def _(event):
            self._move_input_history(event.app.current_buffer, 1)

        @bindings.add("c-c", filter=approval_inactive, eager=True)
        def _(event):
            self._handle_interrupt(event)

        @bindings.add("c-d", filter=approval_inactive, eager=True)
        def _(event):
            self._handle_exit(event)

        return bindings

    def _reset_slash_context(self) -> None:
        self._slash_selected = 0
        self._slash_group = None
        self._slash_command = None
        self._slash_arg_step = 0
        self._slash_args = []

    def _slash_active(self) -> bool:
        if self._slash_command:
            return bool(_argument_rows(self._slash_command, self._slash_arg_step, self))
        if _is_exact_argument_command(self._current_input):
            return bool(_argument_rows(self._current_input, 0, self))
        return bool(_slash_launcher_rows(self._current_input, self._slash_group)) and not _is_exact_slash_command(self._current_input)

    def _move_slash(self, delta: int) -> None:
        rows = self._current_slash_rows()
        if not rows:
            return
        self._slash_selected = (self._slash_selected + delta) % len(rows)
        if self.app:
            self.app.invalidate()

    def _current_slash_rows(self) -> list[dict[str, str]]:
        if self._slash_command:
            return _argument_rows(self._slash_command, self._slash_arg_step, self)
        if _is_exact_argument_command(self._current_input):
            return _argument_rows(self._current_input, 0, self)
        return _slash_launcher_rows(self._current_input, self._slash_group)

    def _selected_slash_row(self) -> dict[str, str]:
        rows = self._current_slash_rows()
        if not rows:
            return {"kind": "command", "value": self._current_input, "label": self._current_input, "meta": ""}
        self._slash_selected = min(self._slash_selected, len(rows) - 1)
        return rows[self._slash_selected]

    def _accept_slash_selection(self, event) -> None:
        row = self._selected_slash_row()
        if row["kind"] == "group":
            self._slash_group = row["value"]
            self._slash_selected = 0
            self._status_message = f"{row['label']} - select an option"
            if self.app:
                self.app.invalidate()
            return
        if row["kind"] == "argument":
            command = self._slash_command or self._current_input
            specs = COMMAND_ARGUMENT_SPECS.get(command, [])
            self._slash_args = self._slash_args[: self._slash_arg_step]
            self._slash_args.append(row["value"])
            if self._slash_arg_step + 1 < len(specs):
                self._slash_arg_step += 1
                self._slash_selected = 0
                next_placeholder = specs[self._slash_arg_step]["placeholder"]
                self._status_message = f"{command}: choose {next_placeholder}"
                if self.app:
                    self.app.invalidate()
                return
            text = _command_template(command, self._slash_args)
            buffer = event.app.current_buffer
            buffer.text = text
            if hasattr(buffer, "cursor_position"):
                placeholder_match = re.search(r"<[^>]+>", text)
                buffer.cursor_position = placeholder_match.start() if placeholder_match else len(text)
            self._current_input = text
            self._reset_slash_context()
            self._status_message = f"{command}: replace {row['value']} then Enter"
            if self.app:
                self.app.invalidate()
            return
        command = row["value"]
        if command in COMMAND_ARGUMENT_SPECS and not self._slash_command:
            self._slash_command = command
            self._slash_arg_step = 0
            self._slash_args = []
            self._slash_selected = 0
            self._status_message = f"{command} - choose arguments"
            if self.app:
                self.app.invalidate()
            return
        buffer = event.app.current_buffer
        buffer.text = command
        if hasattr(buffer, "cursor_position"):
            buffer.cursor_position = len(command)
        self._current_input = command
        self._reset_slash_context()
        self._status_message = f"{command} ready - Enter to run"
        if self.app:
            self.app.invalidate()

    def _move_approval(self, delta: int) -> None:
        if not self._approval_state:
            return
        self._approval_state["selected"] = (self._approval_state["selected"] + delta) % 3
        if self.app:
            self.app.invalidate()

    def _resolve_approval(self, forced=None) -> None:
        if not self._approval_state:
            return
        choices = [ALLOW_ONCE.value, DENY.value, "session"]
        result = forced if forced is not None else choices[self._approval_state["selected"]]
        self._approval_state["result"] = result
        self._approval_state["event"].set()

    def _handle_escape(self, event) -> None:
        buffer = event.app.current_buffer
        if self._slash_group:
            self._reset_slash_context()
            buffer.text = "/"
            self._current_input = "/"
            self._status_message = ""
            event.app.invalidate()
            return
        if self._slash_command:
            self._slash_command = None
            self._slash_arg_step = 0
            self._slash_selected = 0
            self._slash_args = []
            self._status_message = ""
            event.app.invalidate()
            return
        if buffer.text:
            buffer.text = ""
            self._current_input = ""
            self._reset_slash_context()
            event.app.invalidate()
        else:
            self._status_message = "Use /exit or Ctrl-D to exit"
            event.app.invalidate()

    def _handle_exit(self, event) -> None:
        if self._is_working:
            self._cancelled_turn_ids.add(self._active_turn_id)
            self._is_working = False
        event.app.exit()

    def _model_name(self) -> str:
        if self.settings and getattr(self.settings, "is_llm_enabled", False):
            return getattr(self.settings, "model", "unknown")
        return "disabled"

    def _provider_name(self) -> str:
        if self.settings and getattr(self.settings, "is_llm_enabled", False):
            return getattr(self.settings, "provider", "model")
        return "local"

    def _short_root(self) -> str:
        return self.root.name or str(self.root)

    def _tty_banner(self) -> str:
        model = self._model_name()
        provider = self._provider_name()
        worker_summary = self.cli._worker_state_summary()
        header_left = f"nora  {self.root}"
        header_right = "TTY mode"
        lines = [
            _join_left_right(header_left, header_right),
            "",
            "[::]    Nora Code",
            f"        model: {provider} / {model}",
        ]
        if worker_summary:
            lines.append(f"        {worker_summary}")
        return "\n".join(lines)

    def _bottom_toolbar(self) -> HTML:
        text = _join_left_right(
            "Ready",
            "/ commands   Enter send   Esc clear   Ctrl-D exit",
        )
        return HTML(
            f"<style fg='#8f8577'>{text}</style>"
        )

    def _slash_launcher_panel(self, prefix: str = "/", selected: int = 0) -> str:
        rows = []
        matches = self._current_slash_rows()
        limit = 6 if self._is_compact_terminal() else COMMAND_PANEL_LIMIT
        if selected >= limit:
            start = selected - limit + 1
        else:
            start = 0
        visible = matches[start : start + limit]
        for offset, row in enumerate(visible):
            index = start + offset
            marker = ">" if index == selected else " "
            label = row["label"]
            if row["kind"] == "group":
                label = f"{label}/"
            rows.append(f"{marker} {_pad_columns(label, row['meta'], 42).rstrip()}")
        if not rows:
            rows.append("  no matching commands")
        elif len(matches) > limit:
            noun = "groups" if not self._slash_group and prefix == "/" else "commands"
            if noun == "groups":
                action = "Enter open"
            elif self._slash_group or self._slash_command:
                action = "Enter choose, Esc back"
            else:
                action = "type to filter"
            rows.append(f"  {len(matches)} {noun}, {action}")
        elif self._slash_group or self._slash_command:
            rows.append("  Enter choose, Esc back")
        title = "/ commands"
        if self._slash_group:
            title = f"{title} / {self._slash_group}"
        if self._slash_command:
            title = f"{title} / {self._slash_command}"
        return _light_panel(title, rows, width=self._panel_width())

    def _render_header(self):
        if self._is_compact_terminal():
            return [("class:nora.status", _fit_line(f"nora  {self._short_root()}", self._terminal_columns()))]
        header_left = f"nora  {self.root}"
        header_right = "TTY mode"
        return [("class:nora.status", _join_left_right(header_left, header_right))]

    def _terminal_columns(self) -> int:
        return max(20, _size_columns(shutil.get_terminal_size(fallback=(100, 24))) - 1)

    def _is_compact_terminal(self) -> bool:
        size = shutil.get_terminal_size(fallback=(100, 24))
        columns = _size_columns(size)
        lines = _size_lines(size)
        return columns < 72 or lines <= 24

    def _use_framed_input(self) -> bool:
        size = shutil.get_terminal_size(fallback=(100, 24))
        columns = _size_columns(size)
        lines = _size_lines(size)
        return columns >= 72 and lines >= 20

    def _panel_width(self) -> int:
        return min(72, max(36, self._terminal_columns()))

    def _slash_panel_height(self) -> int:
        rows = _size_lines(shutil.get_terminal_size(fallback=(100, 24)))
        if rows <= 24:
            return 8
        return 8 if self._is_compact_terminal() else 10

    def _approval_panel_height(self) -> int:
        return _approval_panel_height()

    def _body_visible_line_limit(self) -> int:
        rows = _size_lines(shutil.get_terminal_size(fallback=(100, 24)))
        reserved = 5 if self._is_compact_terminal() else 7
        if self._approval_state is not None:
            reserved += min(8, self._approval_panel_height())
        if self._slash_active():
            reserved += self._slash_panel_height()
        return max(3, rows - reserved)

    def _transcript_visual_lines(self, width: Optional[int] = None) -> list[str]:
        lines = []
        if not self._transcript:
            banner_lines = self._tty_banner().splitlines()[2:]
            if self._approval_state is not None and self._is_compact_terminal():
                banner_lines = banner_lines[:1]
            lines.extend(banner_lines)
            if self._restored_session_notice:
                lines.append("")
                lines.extend(self._restored_session_notice)
        else:
            for entry in self._transcript[-80:]:
                lines.extend(str(entry).splitlines())
        if self._streaming_answer:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(str(self._streaming_answer).splitlines())
        if self._activity_lines:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(self._activity_lines[-6:])
        if not lines:
            lines = [""]
        body_width = width or self._terminal_columns()
        return _wrap_display_lines(lines, body_width)

    def _scroll_body(self, direction: int, page_size: Optional[int] = None) -> None:
        page = page_size or self._body_visible_line_limit()
        max_offset = max(0, len(self._transcript_visual_lines()) - page)
        if direction < 0:
            self._body_scroll_offset = min(max_offset, self._body_scroll_offset + page)
        else:
            self._body_scroll_offset = max(0, self._body_scroll_offset - page)
        if self.app:
            self.app.invalidate()

    def _append_transcript(self, text: str) -> None:
        self._transcript.append(text)

    def _set_streaming_answer(self, text: str) -> None:
        self._streaming_answer = text
        if self.app:
            self.app.invalidate()

    def _clear_streaming_answer(self) -> None:
        self._streaming_answer = ""
        if self.app:
            self.app.invalidate()

    def _set_activity(self, *lines: str) -> None:
        self._activity_lines = [line for line in lines if line]
        if self.app:
            self.app.invalidate()

    def _clear_activity(self) -> None:
        self._activity_lines = []
        if self.app:
            self.app.invalidate()

    def _normalize_input_text(self, text: str) -> str:
        return re.sub(r"\s*[\r\n]+\s*", " ", text).strip()

    def _replace_buffer_text(self, buffer, text: str) -> None:
        buffer.text = text
        if hasattr(buffer, "cursor_position"):
            buffer.cursor_position = len(text)

    def _record_input_history(self, text: str) -> None:
        if not text:
            return
        if self._input_history and self._input_history[-1] == text:
            self._history_index = None
            self._history_draft = ""
            return
        self._input_history.append(text)
        self._input_history = self._input_history[-100:]
        self._history_index = None
        self._history_draft = ""

    def _move_input_history(self, buffer, direction: int) -> None:
        if not self._input_history:
            return
        if direction < 0:
            if self._history_index is None:
                self._history_draft = buffer.text
                self._history_index = len(self._input_history) - 1
            else:
                self._history_index = max(0, self._history_index - 1)
        else:
            if self._history_index is None:
                return
            if self._history_index >= len(self._input_history) - 1:
                self._history_index = None
                self._replace_buffer_text(buffer, self._history_draft)
                self._history_draft = ""
                return
            self._history_index += 1
        self._replace_buffer_text(buffer, self._input_history[self._history_index])

    def _render_body(self, max_lines: Optional[int] = None, width: Optional[int] = None):
        body_width = width or self._terminal_columns()
        lines = self._transcript_visual_lines(body_width)
        limit = max_lines or self._body_visible_line_limit()
        if len(lines) > limit:
            end = max(limit, len(lines) - self._body_scroll_offset)
            start = max(0, end - limit)
            lines = lines[start:end]
        return _render_fixed_lines(
            lines,
            lambda line: "class:nora.accent" if line.startswith("> ") else "class:nora.dim",
            width=body_width,
        )

    def _render_slash_panel(self):
        if not self._current_input.startswith("/"):
            return []
        rows = self._current_slash_rows()
        if rows:
            self._slash_selected = min(self._slash_selected, len(rows) - 1)
        lines = self._slash_launcher_panel(self._current_input, self._slash_selected).splitlines()
        return _render_fixed_lines(
            lines,
            lambda line: "class:nora.accent" if line.startswith("> ") else "class:nora.dim",
            width=self._terminal_columns(),
        )

    def _render_approval_panel(self):
        if not self._approval_state:
            return []
        lines = _approval_lines(self._approval_state["prompt"], self._approval_state["selected"])
        return _render_fixed_lines(
            lines,
            lambda line: (
                "class:nora.accent"
                if line.startswith("> ")
                else "class:nora.status" if line.startswith("Esc") else "class:nora.dim"
            ),
            width=self._terminal_columns(),
        )

    def _render_status(self):
        if self._status_message:
            message = self._status_message
        elif self._is_compact_terminal():
            message = "Ready  / commands   Enter send   Ctrl-Up/Down scroll   Esc clear   Ctrl-D exit"
        else:
            message = _join_left_right(
                "Ready",
                "/ commands   Enter send   Ctrl-Up/Down scroll   Esc clear   Ctrl-D exit",
            )
        return [("class:nora.status", _fixed_line(message, self._terminal_columns()))]

    def _worker_is_running(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def _handle_app_input(self, buffer):
        user_input = self._normalize_input_text(buffer.text)
        if not user_input:
            buffer.text = ""
            self._current_input = ""
            return True
        if self._is_working or self._worker_is_running():
            self._status_message = "Cancelling current turn..." if self._worker_is_running() else "Still working..."
            if self.app:
                self.app.invalidate()
            return True
        self._clear_activity()
        self._clear_streaming_answer()
        buffer.text = ""
        self._current_input = ""
        self._status_message = ""
        if user_input == "/":
            buffer.text = "/"
            self._current_input = "/"
            self._reset_slash_context()
            if self.app:
                self.app.invalidate()
            return True
        self._record_input_history(user_input)
        self._execute_cli_input(user_input, echo=not user_input.startswith("/"))
        return True

    def _execute_cli_input(self, user_input: str, echo: bool = True) -> None:
        if echo:
            self._append_transcript(f"> {user_input}")
        self._next_turn_id += 1
        turn_id = self._next_turn_id
        self._active_turn_id = turn_id
        self._is_working = True
        self._worker_thread = threading.Thread(target=self._run_cli_input, args=(user_input, turn_id), daemon=True)
        self._worker_thread.start()
        if self.app:
            self.app.invalidate()

    def _turn_is_current(self, turn_id: int) -> bool:
        return self._active_turn_id == turn_id and turn_id not in self._cancelled_turn_ids

    def _run_cli_input(self, user_input: str, turn_id: Optional[int] = None) -> None:
        turn_id = self._active_turn_id if turn_id is None else turn_id
        try:
            if not user_input.strip().startswith("/") and hasattr(self.cli.agent, "run_events"):
                self._run_agent_events_input(user_input, turn_id)
                return
            result = self.cli.handle_input(user_input)
            if not self._turn_is_current(turn_id):
                return
            if result is None:
                if self.app:
                    self.app.exit()
                return
            if result:
                self._status_message = ""
                self._append_transcript(result)
                if user_input.strip().startswith("/session-load"):
                    self._transcript = []
                    self._hydrate_transcript_from_memory(preview=False)
                    self._append_transcript(result)
        except Exception as error:
            if not self._turn_is_current(turn_id):
                return
            self._status_message = ""
            self._append_transcript(f"error: {error}")
        finally:
            if self._active_turn_id == turn_id:
                self._is_working = False
                if turn_id in self._cancelled_turn_ids:
                    self._clear_activity()
                    self._status_message = "Cancelled"
                elif self._status_message == "status: thinking":
                    self._status_message = ""
                if self._worker_thread is threading.current_thread():
                    self._worker_thread = None
                if self.app:
                    self.app.invalidate()

    def _run_agent_events_input(self, user_input: str, turn_id: int) -> None:
        answer = ""
        last_activity = ""
        self._status_message = "thinking"
        self._set_activity("thinking")
        for event in self.cli.agent.run_events(user_input):
            if not self._turn_is_current(turn_id):
                return
            event_type = event.get("type")
            if event_type == "typing":
                self._status_message = "thinking"
                self._set_activity("thinking")
            elif event_type == "tool_call_start":
                name = str(event.get("name") or "tool")
                last_activity = f"tool: {name}"
                self._status_message = f"tool: {name}"
                self._set_activity("thinking", f"tool: {name}")
            elif event_type == "tool_call_result":
                name = str(event.get("name") or "tool")
                status = str(event.get("status") or "ok")
                last_activity = f"tool: {name} {status}"
                self._status_message = f"tool: {name} {status}"
                self._set_activity("thinking", f"tool: {name} {status}")
            elif event_type == "delta":
                answer += str(event.get("content") or "")
                if answer:
                    self._set_streaming_answer(answer)
            elif event_type == "error":
                answer = answer or str(event.get("error") or "")
                if answer:
                    self._set_streaming_answer(answer)
            elif event_type == "done":
                self._status_message = f"done · {last_activity}" if last_activity else "done"
        if not self._turn_is_current(turn_id):
            return
        response = self.cli._format_agent_response(answer)
        response = self.cli._append_recovery_hint(response)
        self.cli._autosave_conversation()
        self._clear_streaming_answer()
        if response:
            self._append_transcript(response)
        if last_activity:
            self._set_activity(f"done · {last_activity}")

    def _confirm_action(self, prompt_text: str) -> bool:
        approval_scope = _approval_scope_key(prompt_text)
        if approval_scope and approval_scope in _SESSION_ALLOWED_TOOLS:
            return True
        if not self.app or not getattr(self.app, "_is_running", False):
            return selectable_confirm(prompt_text)
        event = threading.Event()
        self._approval_state = {
            "prompt": prompt_text,
            "selected": _approval_default_index(prompt_text),
            "event": event,
            "result": False,
        }
        self._status_message = "Approval required"
        self.app.invalidate()
        event.wait()
        result = self._approval_state["result"] if self._approval_state else False
        self._approval_state = None
        self._status_message = ""
        if result == "session":
            if approval_scope:
                _SESSION_ALLOWED_TOOLS.add(approval_scope)
            result = True
        if self.app:
            self.app.invalidate()
        return bool(result)

    def _handle_interrupt(self, event) -> None:
        buffer = event.app.current_buffer
        if self._is_working:
            self._cancelled_turn_ids.add(self._active_turn_id)
            self._is_working = False
            self._status_message = "Cancelled"
            event.app.invalidate()
            return
        if buffer.text:
            buffer.text = ""
            self._current_input = ""
            self._reset_slash_context()
            event.app.invalidate()
            return
        event.app.exit()

    def _make_application(self) -> Application:
        input_box = TextArea(
            height=1,
            multiline=False,
            prompt="> ",
            completer=self.completer,
            complete_while_typing=False,
            accept_handler=self._handle_app_input,
            style="class:nora.text",
        )
        input_box.control.key_bindings = self._make_input_bindings()

        def on_input_change(_):
            self._current_input = input_box.text
            if self._current_input and self._status_message in {
                "Use /exit or Ctrl-D to exit",
                "Cancelled",
            }:
                self._status_message = ""
            if self._current_input != "/" and not self._slash_command:
                self._reset_slash_context()
            rows = self._current_slash_rows() if self._current_input.startswith("/") else []
            if rows:
                self._slash_selected = min(self._slash_selected, len(rows) - 1)
            else:
                self._slash_selected = 0
            if self.app:
                self.app.invalidate()

        input_box.buffer.on_text_changed += on_input_change

        bindings = self._make_bindings()
        compact = self._is_compact_terminal()
        framed_input = self._use_framed_input()
        if not framed_input:
            self._input_frame = None
            input_container = input_box
            slash_height = self._slash_panel_height()
            approval_height = self._approval_panel_height()
            spacer_height = 0
        else:
            self._input_frame = Frame(input_box, title="Nora", style="class:nora.input")
            input_container = self._input_frame
            slash_height = self._slash_panel_height()
            approval_height = self._approval_panel_height()
            rows = _size_lines(shutil.get_terminal_size(fallback=(100, 24)))
            spacer_height = 0 if rows <= 24 else 1
        slash_panel = ConditionalContainer(
            Window(
                FormattedTextControl(self._render_slash_panel),
                height=slash_height,
                always_hide_cursor=True,
            ),
            filter=Condition(lambda: self._slash_active()),
        )
        approval_panel = ConditionalContainer(
            Window(
                FormattedTextControl(self._render_approval_panel),
                height=approval_height,
                always_hide_cursor=True,
            ),
            filter=Condition(lambda: self._approval_state is not None),
        )
        children = [
            Window(FormattedTextControl(self._render_header), height=1),
        ]
        if not compact:
            children.append(Window(height=1, char="-", style="class:nora.status"))
        children.extend([
            Window(
                FormattedTextControl(self._render_body),
                wrap_lines=False,
                height=Dimension(weight=1),
                always_hide_cursor=True,
            ),
            approval_panel,
            slash_panel,
        ])
        if spacer_height:
            children.append(Window(height=spacer_height, char=" ", style="class:nora.status"))
        children.extend([
            input_container,
            Window(FormattedTextControl(self._render_status), height=1, dont_extend_height=True),
        ])
        root = HSplit(children)
        app = Application(
            layout=Layout(root, focused_element=input_box),
            key_bindings=bindings,
            style=TTY_STYLE,
            full_screen=True,
            mouse_support=False,
        )
        self.app = app
        return app

    def run(self) -> None:
        with patch_stdout():
            self._make_application().run()


def is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()
