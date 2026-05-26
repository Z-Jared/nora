import ast
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from mini_agent.process_manager import DEFAULT_PROFILES
from mini_agent.settings import LLMSettings


SHELL_EXECUTE_TOOLS = {
    "run_shell_command",
    "run_project_tests",
    "run_repair_loop",
    "start_background_process",
    "stop_background_process",
}
GIT_WRITE_TOOLS = {
    "git_create_branch",
    "git_stage_paths",
    "git_unstage_paths",
    "git_commit_staged",
}
BROWSER_INTERACT_TOOLS = {"browser_click", "browser_fill"}
BROWSER_WRITE_TOOLS = {"browser_screenshot"}
AUTONOMOUS_WRITE_TOOLS = {
    "save_note",
    "write_project_file",
    "replace_in_project_file",
    "apply_project_patch",
    "apply_project_multi_patch",
    "save_context_summary",
    "save_memory",
    "delete_memory",
    "start_task",
    "update_task_step",
    "finish_task",
    "run_task_once",
} | SHELL_EXECUTE_TOOLS | GIT_WRITE_TOOLS | BROWSER_INTERACT_TOOLS | BROWSER_WRITE_TOOLS


@dataclass(frozen=True)
class LLMConfig:
    provider: str = ""
    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 0


@dataclass(frozen=True)
class PathsConfig:
    notes: Path = Path("data/notes.txt")
    long_term_memory: Path = Path("data/long_term_memory.jsonl")
    task_state: Path = Path("data/current_task.json")
    task_history: Path = Path("data/task_history.jsonl")
    context_summaries: Path = Path("data/context_summaries.jsonl")
    tool_logs: Path = Path("logs/tool_calls.jsonl")


@dataclass(frozen=True)
class ContextWindowConfig:
    max_tool_result_chars: int = 8000
    head_chars: int = 3000
    tail_chars: int = 2000


@dataclass(frozen=True)
class BudgetsConfig:
    max_tool_calls_per_turn: int = 8


@dataclass(frozen=True)
class RAGConfig:
    include_paths: list[str]
    exclude_dirs: list[str]
    max_file_bytes: int = 64 * 1024
    chunk_size: int = 80
    chunk_overlap: int = 20


@dataclass(frozen=True)
class ProcessesConfig:
    profiles: dict[str, list[str]]


@dataclass(frozen=True)
class ToolsConfig:
    disabled: set[str]


@dataclass(frozen=True)
class PermissionsConfig:
    deny: set[str]
    confirmation_overrides: dict[str, bool]


@dataclass(frozen=True)
class SafetyConfig:
    mode: str = "normal"
    allow_autonomous_write: bool = True
    allow_shell_execute: bool = True
    allow_git_write: bool = True
    allow_browser_interact: bool = True


@dataclass(frozen=True)
class AgentConfig:
    llm: LLMConfig
    paths: PathsConfig
    context_window: ContextWindowConfig
    budgets: BudgetsConfig
    rag: RAGConfig
    processes: ProcessesConfig
    tools: ToolsConfig
    permissions: PermissionsConfig
    safety: SafetyConfig

    @classmethod
    def defaults(cls) -> "AgentConfig":
        return cls(
            llm=LLMConfig(),
            paths=PathsConfig(),
            context_window=ContextWindowConfig(),
            budgets=BudgetsConfig(),
            rag=RAGConfig(include_paths=[], exclude_dirs=[]),
            processes=ProcessesConfig(profiles=dict(DEFAULT_PROFILES)),
            tools=ToolsConfig(disabled=set()),
            permissions=PermissionsConfig(deny=set(), confirmation_overrides={}),
            safety=SafetyConfig(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        defaults = cls.defaults()
        llm_data = _as_dict(data.get("llm"))
        paths_data = _as_dict(data.get("paths"))
        context_data = _as_dict(data.get("context_window"))
        budgets_data = _as_dict(data.get("budgets"))
        rag_data = _as_dict(data.get("rag"))
        process_data = _as_dict(data.get("processes"))
        profile_data = _as_dict(process_data.get("profiles"))
        tools_data = _as_dict(data.get("tools"))
        permissions_data = _as_dict(data.get("permissions"))
        safety_data = _as_dict(data.get("safety"))
        safety_mode = str(safety_data.get("mode") or defaults.safety.mode)
        strict_mode = safety_mode == "strict"

        return cls(
            llm=LLMConfig(
                provider=str(llm_data.get("provider") or defaults.llm.provider),
                base_url=str(llm_data.get("base_url") or defaults.llm.base_url),
                model=str(llm_data.get("model") or defaults.llm.model),
                timeout_seconds=_int(llm_data.get("timeout_seconds"), defaults.llm.timeout_seconds),
            ),
            paths=PathsConfig(
                notes=Path(str(paths_data.get("notes") or defaults.paths.notes)),
                long_term_memory=Path(str(paths_data.get("long_term_memory") or defaults.paths.long_term_memory)),
                task_state=Path(str(paths_data.get("task_state") or defaults.paths.task_state)),
                task_history=Path(str(paths_data.get("task_history") or defaults.paths.task_history)),
                context_summaries=Path(str(paths_data.get("context_summaries") or defaults.paths.context_summaries)),
                tool_logs=Path(str(paths_data.get("tool_logs") or defaults.paths.tool_logs)),
            ),
            context_window=ContextWindowConfig(
                max_tool_result_chars=_int(
                    context_data.get("max_tool_result_chars"),
                    defaults.context_window.max_tool_result_chars,
                ),
                head_chars=_int(context_data.get("head_chars"), defaults.context_window.head_chars),
                tail_chars=_int(context_data.get("tail_chars"), defaults.context_window.tail_chars),
            ),
            budgets=BudgetsConfig(
                max_tool_calls_per_turn=_int(
                    budgets_data.get("max_tool_calls_per_turn"),
                    defaults.budgets.max_tool_calls_per_turn,
                ),
            ),
            rag=RAGConfig(
                include_paths=_string_list(rag_data.get("include_paths")),
                exclude_dirs=_string_list(rag_data.get("exclude_dirs")),
                max_file_bytes=_int(rag_data.get("max_file_bytes"), defaults.rag.max_file_bytes),
                chunk_size=_int(rag_data.get("chunk_size"), defaults.rag.chunk_size),
                chunk_overlap=_int(rag_data.get("chunk_overlap"), defaults.rag.chunk_overlap),
            ),
            processes=ProcessesConfig(profiles=_profiles(profile_data, defaults.processes.profiles)),
            tools=ToolsConfig(disabled=_string_set(tools_data.get("disabled"))),
            permissions=PermissionsConfig(
                deny=_string_set(permissions_data.get("deny")),
                confirmation_overrides=_bool_map(permissions_data.get("confirmation_overrides")),
            ),
            safety=SafetyConfig(
                mode=safety_mode,
                allow_autonomous_write=_bool(
                    safety_data.get("allow_autonomous_write"),
                    defaults.safety.allow_autonomous_write and not strict_mode,
                ),
                allow_shell_execute=_bool(
                    safety_data.get("allow_shell_execute"),
                    defaults.safety.allow_shell_execute and not strict_mode,
                ),
                allow_git_write=_bool(
                    safety_data.get("allow_git_write"),
                    defaults.safety.allow_git_write and not strict_mode,
                ),
                allow_browser_interact=_bool(
                    safety_data.get("allow_browser_interact"),
                    defaults.safety.allow_browser_interact and not strict_mode,
                ),
            ),
        )

    def apply_to_llm_settings(self, settings: LLMSettings) -> LLMSettings:
        updates = {}
        if self.llm.provider:
            updates["provider"] = self.llm.provider
        if self.llm.base_url:
            updates["base_url"] = self.llm.base_url
        if self.llm.model:
            updates["model"] = self.llm.model
        if self.llm.timeout_seconds:
            updates["timeout_seconds"] = self.llm.timeout_seconds
        return replace(settings, **updates) if updates else settings

    def resolve_path(self, root: Path, path: Path) -> Path:
        resolved_root = root.resolve()
        raw_target = path if path.is_absolute() else root / path
        target = raw_target.resolve()
        try:
            target.relative_to(resolved_root)
        except ValueError as error:
            raise ValueError(f"配置路径必须位于项目目录内: {path}") from error
        return raw_target

    def disabled_tools(self) -> set[str]:
        disabled = set(self.tools.disabled) | set(self.permissions.deny)
        if not self.safety.allow_shell_execute:
            disabled |= SHELL_EXECUTE_TOOLS
        if not self.safety.allow_git_write:
            disabled |= GIT_WRITE_TOOLS
        if not self.safety.allow_browser_interact:
            disabled |= BROWSER_INTERACT_TOOLS
        return disabled

    def permission_overrides(self) -> dict[str, bool]:
        return dict(self.permissions.confirmation_overrides)

    def autonomous_disabled_tools(self) -> set[str]:
        if self.safety.allow_autonomous_write:
            return set()
        return set(AUTONOMOUS_WRITE_TOOLS)


def load_agent_config(path: Path = Path("agent.yaml")) -> AgentConfig:
    if not path.exists():
        return AgentConfig.defaults()
    return AgentConfig.from_dict(_parse_yaml_subset(path.read_text(encoding="utf-8")))


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        line_without_comment = raw_line
        if " #" in raw_line:
            line_without_comment = raw_line.split(" #", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        indent = len(line_without_comment) - len(line_without_comment.lstrip(" "))
        line = line_without_comment.strip()
        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if not raw_value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(raw_value)

    return root


def _parse_scalar(value: str):
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "None"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value
        return parsed if isinstance(parsed, list) else value
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool(value, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _profiles(data: dict, defaults: dict[str, list[str]]) -> dict[str, list[str]]:
    if not data:
        return dict(defaults)

    profiles = {}
    for name, value in data.items():
        if isinstance(value, dict):
            command = value.get("command")
        else:
            command = value
        if isinstance(command, list) and command and all(isinstance(part, str) for part in command):
            profiles[str(name)] = list(command)
    return profiles or dict(defaults)


def _string_set(value) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _bool_map(value) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, item in value.items():
        if isinstance(item, bool):
            result[str(key)] = item
    return result
