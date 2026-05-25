from pathlib import Path
from typing import Callable, Optional

from mini_agent.context_summary import ContextSummaryStore
from mini_agent.diagnostics import Diagnostics
from mini_agent.git_tools import GitTools
from mini_agent.logs import JsonlToolLogger
from mini_agent.memory import LongTermMemory
from mini_agent.process_manager import ProcessManager
from mini_agent.rag import ProjectRAG
from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.repair_loop import RepairLoop
from mini_agent.shell import ShellRunner
from mini_agent.symbols import PythonSymbolIndex
from mini_agent.task_runner import TaskManager
from mini_agent.toolkits.basic import calculate, current_time, make_plan
from mini_agent.toolkits.browser import BrowserBackend, BrowserTools
from mini_agent.toolkits.notes import NotesStore
from mini_agent.tool_results import ToolResultStore
from mini_agent.toolkits.workspace import WorkspaceFiles
from mini_agent.web_tools import WebTools


def build_default_registry(
    notes_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
    log_path: Optional[Path] = None,
    confirm_action: Optional[Callable[[str], bool]] = None,
    web_fetch: Optional[Callable[[str, int], str]] = None,
    browser_backend: Optional[BrowserBackend] = None,
    long_term_memory_path: Optional[Path] = None,
    task_state_path: Optional[Path] = None,
    task_history_path: Optional[Path] = None,
    context_summary_path: Optional[Path] = None,
    process_profiles: Optional[dict[str, list[str]]] = None,
    disabled_tools: Optional[set[str]] = None,
    permission_overrides: Optional[dict[str, bool]] = None,
    tool_results_path: Optional[Path] = None,
    rag_include_paths: Optional[list[str]] = None,
    rag_exclude_dirs: Optional[list[str]] = None,
    rag_max_file_bytes: int = 64 * 1024,
    rag_chunk_size: int = 80,
    rag_chunk_overlap: int = 20,
) -> ToolRegistry:
    root = workspace_root or Path.cwd()
    notes = NotesStore(notes_path or Path("data/notes.txt"))
    workspace_files = WorkspaceFiles(root, require_confirmation=False)
    shell_runner = ShellRunner(root, require_confirmation=False)
    git_tools = GitTools(root)
    diagnostics = Diagnostics(root)
    repair_loop = RepairLoop(diagnostics)
    symbol_index = PythonSymbolIndex(root)
    project_rag = ProjectRAG(
        root,
        max_file_bytes=rag_max_file_bytes,
        include_paths=rag_include_paths,
        exclude_dirs=rag_exclude_dirs,
        chunk_size=rag_chunk_size,
        chunk_overlap=rag_chunk_overlap,
    )
    web_tools = WebTools(fetcher=web_fetch)
    browser_tools = BrowserTools(root=root, backend=browser_backend)
    process_manager = ProcessManager(root, profiles=process_profiles)
    long_term_memory = LongTermMemory(long_term_memory_path or Path("data/long_term_memory.jsonl"))
    task_manager = TaskManager(
        task_state_path or Path("data/current_task.json"),
        task_history_path or Path("data/task_history.jsonl"),
    )
    context_summaries = ContextSummaryStore(context_summary_path or Path("data/context_summaries.jsonl"))
    tool_results = ToolResultStore(tool_results_path or Path("data/tool_results.jsonl"))
    logger = JsonlToolLogger(log_path or Path("logs/tool_calls.jsonl"))
    registry = ToolRegistry(
        logger=logger,
        confirm_action=confirm_action,
        disabled_tools=disabled_tools,
        permission_overrides=permission_overrides,
    )

    registry.register(
        "calculate",
        "计算数学表达式。只接受纯数学表达式，例如 2 + 3 * 4。",
        calculate,
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式，例如 2 + 3 * 4",
                }
            },
            "required": ["expression"],
        },
        permission=ToolPermission(category="local", risk="read"),
    )
    registry.register(
        "current_time",
        "查看当前时间。",
        current_time,
        parameters={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA 时区名称，例如 Asia/Shanghai",
                }
            },
        },
        permission=ToolPermission(category="local", risk="read"),
    )
    registry.register(
        "save_note",
        "保存一条笔记。",
        notes.save,
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要保存的笔记内容",
                }
            },
            "required": ["text"],
        },
        permission=ToolPermission(category="notes", risk="write"),
    )
    registry.register(
        "read_notes",
        "读取已保存的笔记。",
        notes.read,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="notes", risk="read"),
    )
    registry.register(
        "read_project_file",
        "读取当前项目目录内的 UTF-8 文本文件。不能读取 .env 等敏感文件。",
        workspace_files.read,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的文件路径，例如 README.md",
                }
            },
            "required": ["path"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "list_project_files",
        "列出当前项目目录内可读取的文件。不会列出 .env、data、.git 等敏感或内部目录。",
        workspace_files.list,
        parameters={
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "description": "最多返回多少个文件，默认 50，最大 200",
                }
            },
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "make_plan",
        "为一个开发目标生成简洁的分步计划。",
        make_plan,
        parameters={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "要规划的开发目标",
                }
            },
            "required": ["goal"],
        },
        permission=ToolPermission(category="planning", risk="read"),
    )
    registry.register(
        "git_status",
        "查看当前仓库的 Git 工作区状态。只读，不会修改仓库。",
        git_tools.status,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_diff",
        "查看当前仓库的 Git diff。可指定项目内路径；只读，不会修改仓库。",
        git_tools.diff,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "可选，相对于项目根目录的路径，例如 README.md",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                },
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_log",
        "查看最近 Git 提交。只读，不会修改仓库。",
        git_tools.log,
        parameters={
            "type": "object",
            "properties": {
                "max_count": {
                    "type": "integer",
                    "description": "最多返回多少个提交，默认 5，最大 50",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_current_branch",
        "查看当前 Git 分支。只读，不会修改仓库。",
        git_tools.current_branch,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_branches",
        "列出本地 Git 分支。只读，不会修改仓库。",
        git_tools.branches,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_staged_diff",
        "查看已暂存改动的 Git diff。只读，不会修改仓库。",
        git_tools.staged_diff,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_summarize_changes",
        "汇总当前分支、status、staged/unstaged stat 和最近提交。只读，不会修改仓库。",
        git_tools.summarize_changes,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_review_staged_diff",
        "审查 staged diff 的文件列表、统计和敏感路径提示。只读，不会修改仓库。",
        git_tools.review_staged_diff,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_check_before_commit",
        "提交前检查 staged、unstaged/untracked 和敏感路径状态。只读，不会修改仓库。",
        git_tools.check_before_commit,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_create_branch",
        "创建本地 Git 分支但不切换。需要用户确认；不会 push、pull、fetch 或修改远程。",
        git_tools.create_branch,
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要创建的本地分支名",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要创建这个分支",
                },
            },
            "required": ["name"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
    registry.register(
        "git_stage_paths",
        "暂存显式指定的项目内路径。需要用户确认；拒绝敏感路径，不支持 git add . 或 git add -A。",
        git_tools.stage_paths,
        parameters={
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要暂存的项目内相对路径列表",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要暂存这些路径",
                },
            },
            "required": ["paths"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
    registry.register(
        "git_unstage_paths",
        "取消暂存显式指定的项目内路径。需要用户确认；拒绝敏感路径。",
        git_tools.unstage_paths,
        parameters={
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要取消暂存的项目内相对路径列表",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要取消暂存这些路径",
                },
            },
            "required": ["paths"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
    registry.register(
        "git_commit_staged",
        "提交已暂存的 Git 改动。需要用户确认；不会自动暂存、不会创建空提交、不会 push。",
        git_tools.commit_staged,
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "本地 commit message",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要创建这个本地提交",
                },
            },
            "required": ["message"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
    registry.register(
        "preview_write_project_file",
        "预览写入或覆盖项目文件会产生的 unified diff。只读，不会修改文件。",
        workspace_files.preview_write,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的文件路径，例如 docs/notes.md",
                },
                "content": {
                    "type": "string",
                    "description": "要预览写入的完整文件内容",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "diff 上下文行数，默认 3，最大 20",
                },
            },
            "required": ["path", "content"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "preview_replace_in_project_file",
        "预览在项目文件中执行一次精确文本替换会产生的 unified diff。只读，不会修改文件。",
        workspace_files.preview_replace,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的文件路径，例如 README.md",
                },
                "old_text": {
                    "type": "string",
                    "description": "要替换的原文本，必须完整匹配",
                },
                "new_text": {
                    "type": "string",
                    "description": "替换后的文本",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "diff 上下文行数，默认 3，最大 20",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "write_project_file",
        "写入或覆盖当前项目目录内的 UTF-8 文本文件。需要用户确认，不能写入 .env、data、.git 等敏感路径。",
        workspace_files.write,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的文件路径，例如 docs/notes.md",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的完整文件内容",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要写入或覆盖这个文件",
                },
            },
            "required": ["path", "content"],
        },
        permission=ToolPermission(
            category="workspace",
            risk="write",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "replace_in_project_file",
        "在当前项目目录内的 UTF-8 文本文件中执行一次精确文本替换。需要用户确认，不能修改 .env、data、.git 等敏感路径。",
        workspace_files.replace,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的文件路径，例如 README.md",
                },
                "old_text": {
                    "type": "string",
                    "description": "要替换的原文本，必须完整匹配",
                },
                "new_text": {
                    "type": "string",
                    "description": "替换后的文本",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要修改这个文件",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
        permission=ToolPermission(
            category="workspace",
            risk="write",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "apply_project_patch",
        "应用单文件 unified diff patch。需要用户确认；只支持项目目录内非敏感文本文件。",
        workspace_files.apply_unified_diff,
        parameters={
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "要应用的 unified diff patch",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要应用这个 patch",
                },
            },
            "required": ["patch"],
        },
        permission=ToolPermission(
            category="workspace",
            risk="write",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "preview_project_multi_patch",
        "预览多文件 unified diff patch；只读，不会修改文件，不支持创建、删除或重命名。",
        workspace_files.preview_multi_file_patch,
        parameters={
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "要预览的 unified diff patch",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "diff 上下文行数，默认 3，最大 20",
                },
            },
            "required": ["patch"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "apply_project_multi_patch",
        "应用多文件 unified diff patch。写入前全量校验，失败时尽力回滚；需要用户确认。",
        workspace_files.apply_multi_file_patch,
        parameters={
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "要应用的 unified diff patch",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要应用这个 patch",
                },
            },
            "required": ["patch"],
        },
        permission=ToolPermission(
            category="workspace",
            risk="write",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "run_project_tests",
        "运行项目测试并返回失败摘要。需要用户确认；当前只允许 python3 -m unittest discover -s tests。",
        diagnostics.run_tests,
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "测试命令，默认 python3 -m unittest discover -s tests",
                },
                "max_output_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                },
            },
        },
        permission=ToolPermission(
            category="test",
            risk="execute",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "diagnose_test_failure",
        "从测试输出中提取 FAIL、ERROR、traceback、断言和文件行号，给出下一步定位建议。",
        diagnostics.diagnose_test_failure,
        parameters={
            "type": "object",
            "properties": {
                "output": {
                    "type": "string",
                    "description": "测试输出文本",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 4000",
                },
            },
            "required": ["output"],
        },
        permission=ToolPermission(category="test", risk="read"),
    )
    registry.register(
        "run_repair_loop",
        "运行受控修复测试循环：最多 3 轮运行白名单测试并提取失败诊断；不会自动应用 patch 或提交。需要用户确认。",
        repair_loop.run,
        parameters={
            "type": "object",
            "properties": {
                "max_attempts": {
                    "type": "integer",
                    "description": "最多尝试轮数，默认 2，硬上限 3",
                },
                "test_command": {
                    "type": "string",
                    "description": "测试命令，当前只允许 python3 -m unittest discover -s tests",
                },
            },
        },
        permission=ToolPermission(category="test", risk="execute", requires_confirmation=True),
    )
    registry.register(
        "list_python_symbols",
        "列出项目中的 Python 类、函数和方法符号，可按名称或路径过滤。",
        symbol_index.list_symbols,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "可选过滤关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个符号，默认 50，最大 200",
                },
            },
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "find_python_symbol",
        "按名称查找 Python 类、函数或方法，并返回文件和行号。",
        symbol_index.find_symbol,
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要查找的符号名称，例如 ToolRegistry",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个符号，默认 20，最大 100",
                },
            },
            "required": ["name"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "outline_python_file",
        "生成单个 Python 文件的 class、function、method 结构 outline。",
        symbol_index.outline_file,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的 Python 文件路径，例如 mini_agent/registry.py",
                },
                "max_symbols": {
                    "type": "integer",
                    "description": "最多返回多少个符号，默认 100，最大 300",
                },
            },
            "required": ["path"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "describe_python_symbol",
        "查看 Python 符号的路径、行号范围、签名、docstring 和附近源码。",
        symbol_index.describe_symbol,
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要描述的符号名称，例如 ToolRegistry.call",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个匹配符号，默认 5，最大 20",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "源码上下文行数，默认 8，最大 30",
                },
            },
            "required": ["name"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "find_python_references",
        "用 AST 查找 Python Name 和 Attribute 的可能引用；不是语义级精确引用。",
        symbol_index.find_references,
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要查找引用的名称，例如 ToolRegistry 或 call",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个可能引用，默认 100，最大 300",
                },
            },
            "required": ["name"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "python_module_imports",
        "列出单个 Python 文件中的 import 依赖。",
        symbol_index.module_imports,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的 Python 文件路径，例如 main.py",
                }
            },
            "required": ["path"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "run_shell_command",
        "在项目目录内执行安全白名单命令。需要用户确认；支持 pwd、ls、find、rg、python3 -m unittest、python3 -m py_compile、python3 main.py。",
        shell_runner.run,
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的命令，例如 python3 -m unittest discover -s tests",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要执行这个命令",
                },
            },
            "required": ["command"],
        },
        permission=ToolPermission(
            category="terminal",
            risk="execute",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "start_background_process",
        "启动内置 profile 的后台进程。需要用户确认；不支持任意 shell 命令。",
        process_manager.start,
        parameters={
            "type": "object",
            "properties": {
                "profile": {
                    "type": "string",
                    "description": "后台进程 profile，例如 static_server_8000",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要启动这个后台进程",
                },
            },
            "required": ["profile"],
        },
        permission=ToolPermission(category="process", risk="execute", requires_confirmation=True),
    )
    registry.register(
        "list_background_processes",
        "列出当前 agent 管理的后台进程。只读。",
        process_manager.list_processes,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="process", risk="read"),
    )
    registry.register(
        "background_process_status",
        "查看指定后台进程状态。只读。",
        process_manager.status,
        parameters={
            "type": "object",
            "properties": {
                "process_id": {
                    "type": "string",
                    "description": "后台进程 id，例如 proc_1",
                }
            },
            "required": ["process_id"],
        },
        permission=ToolPermission(category="process", risk="read"),
    )
    registry.register(
        "read_background_process_output",
        "读取指定后台进程的最近输出。只读。",
        process_manager.read_output,
        parameters={
            "type": "object",
            "properties": {
                "process_id": {
                    "type": "string",
                    "description": "后台进程 id，例如 proc_1",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 4000",
                },
            },
            "required": ["process_id"],
        },
        permission=ToolPermission(category="process", risk="read"),
    )
    registry.register(
        "wait_for_background_process_output",
        "等待后台进程输出出现指定文本。只读，有超时上限。",
        process_manager.wait_for_output,
        parameters={
            "type": "object",
            "properties": {
                "process_id": {
                    "type": "string",
                    "description": "后台进程 id，例如 proc_1",
                },
                "pattern": {
                    "type": "string",
                    "description": "要等待出现的输出文本",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "最多等待多少秒，默认 10，最大 30",
                },
            },
            "required": ["process_id", "pattern"],
        },
        permission=ToolPermission(category="process", risk="read"),
    )
    registry.register(
        "stop_background_process",
        "停止当前 agent 管理的后台进程。需要用户确认。",
        process_manager.stop,
        parameters={
            "type": "object",
            "properties": {
                "process_id": {
                    "type": "string",
                    "description": "后台进程 id，例如 proc_1",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要停止这个后台进程",
                },
            },
            "required": ["process_id"],
        },
        permission=ToolPermission(category="process", risk="execute", requires_confirmation=True),
    )
    registry.register(
        "search_project_context",
        "在当前项目的文本文件中做轻量关键词检索，返回相关代码或文档片段。不会检索 .env、data、.git、logs 等敏感或内部路径。",
        project_rag.search,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要检索的关键词或问题",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个片段，默认 5，最大 10",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "answer_with_project_context",
        "为项目问题准备 RAG 上下文。工具返回问题和相关项目片段，模型必须基于这些片段回答。",
        project_rag.context_for_question,
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "关于当前项目的问题",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个片段，默认 5，最大 10",
                },
            },
            "required": ["question"],
        },
        permission=ToolPermission(category="workspace", risk="read"),
    )
    registry.register(
        "web_search",
        "联网搜索公开网页。只执行 GET 请求，不提交表单，不执行脚本。",
        web_tools.web_search,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条结果，默认 5，最大 10",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="network", risk="read"),
    )
    registry.register(
        "fetch_url",
        "读取公开 HTTP/HTTPS URL 的文本内容。只执行 GET 请求，不提交表单，不执行脚本。",
        web_tools.fetch_url,
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要读取的 HTTP/HTTPS URL",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                },
            },
            "required": ["url"],
        },
        permission=ToolPermission(category="network", risk="read"),
    )
    registry.register(
        "browser_open_url",
        "用浏览器打开 HTTP/HTTPS 页面。适合需要页面渲染、点击或输入的任务。",
        browser_tools.open_url,
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要打开的 HTTP/HTTPS URL",
                }
            },
            "required": ["url"],
        },
        permission=ToolPermission(category="browser", risk="read"),
    )
    registry.register(
        "browser_page_title",
        "读取当前浏览器页面标题。",
        browser_tools.page_title,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="browser", risk="read"),
    )
    registry.register(
        "browser_page_text",
        "读取当前浏览器页面正文文本。",
        browser_tools.page_text,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 4000，最大 12000",
                }
            },
        },
        permission=ToolPermission(category="browser", risk="read"),
    )
    registry.register(
        "browser_click",
        "点击当前浏览器页面上的 CSS selector。需要用户确认。",
        browser_tools.click,
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "要点击元素的 CSS selector，例如 button[type=submit]",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要点击",
                },
            },
            "required": ["selector"],
        },
        permission=ToolPermission(
            category="browser",
            risk="interact",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "browser_fill",
        "向当前浏览器页面上的 CSS selector 输入文本。需要用户确认。",
        browser_tools.fill,
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "要输入文本的元素 CSS selector，例如 input[name=q]",
                },
                "text": {
                    "type": "string",
                    "description": "要输入的文本",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要输入",
                },
            },
            "required": ["selector", "text"],
        },
        permission=ToolPermission(
            category="browser",
            risk="interact",
            requires_confirmation=True,
        ),
    )
    registry.register(
        "browser_wait_for_selector",
        "等待当前浏览器页面出现指定 CSS selector。只读，有超时上限。",
        browser_tools.wait_for_selector,
        parameters={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "要等待出现的 CSS selector，例如 #submit",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "最多等待多少秒，默认 5，最大 30",
                },
            },
            "required": ["selector"],
        },
        permission=ToolPermission(category="browser", risk="read"),
    )
    registry.register(
        "browser_page_elements",
        "提取当前页面的链接、按钮和输入框摘要，便于选择下一步操作。",
        browser_tools.page_elements,
        parameters={
            "type": "object",
            "properties": {
                "max_items": {
                    "type": "integer",
                    "description": "每类最多返回多少个元素，默认 30，最大 100",
                }
            },
        },
        permission=ToolPermission(category="browser", risk="read"),
    )
    registry.register(
        "browser_page_summary",
        "读取当前浏览器页面标题、正文摘要和可交互元素摘要。",
        browser_tools.page_summary,
        parameters={
            "type": "object",
            "properties": {
                "max_text_chars": {
                    "type": "integer",
                    "description": "页面正文最多返回多少字符，默认 1000，最大 12000",
                },
                "max_elements": {
                    "type": "integer",
                    "description": "每类最多返回多少个元素，默认 20，最大 100",
                },
            },
        },
        permission=ToolPermission(category="browser", risk="read"),
    )
    registry.register(
        "browser_screenshot",
        "保存当前浏览器页面截图到项目目录内的非敏感路径。",
        browser_tools.screenshot,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的截图路径，例如 screenshots/page.png",
                }
            },
        },
        permission=ToolPermission(category="browser", risk="read"),
    )
    registry.register(
        "generate_audit_report",
        "基于最近工具调用日志生成脱敏安全审计摘要，包括工具、状态、高风险类别和拒绝/取消情况。",
        logger.generate_audit_report,
        parameters={
            "type": "object",
            "properties": {
                "max_entries": {
                    "type": "integer",
                    "description": "最多审计多少条最近日志，默认 50，最大 200",
                }
            },
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "view_tool_logs",
        "查看最近的工具调用日志。默认不展示工具参数，可按工具名或状态过滤。",
        logger.list_recent,
        parameters={
            "type": "object",
            "properties": {
                "max_entries": {
                    "type": "integer",
                    "description": "最多返回多少条日志，默认 20，最大 100",
                },
                "tool": {
                    "type": "string",
                    "description": "只查看指定工具名的日志，可留空",
                },
                "status": {
                    "type": "string",
                    "description": "只查看指定状态的日志，例如 ok、error、cancelled，可留空",
                },
                "include_arguments": {
                    "type": "boolean",
                    "description": "是否展示截断后的工具参数，默认 false",
                },
            },
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "list_tool_results",
        "列出已缓存的长工具结果 result_id。只读，不展示完整内容。",
        tool_results.list,
        parameters={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条缓存记录，默认 20，最大 100",
                }
            },
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "read_tool_result",
        "按 result_id 分段读取缓存的长工具结果，有 offset/limit 上限。",
        tool_results.read,
        parameters={
            "type": "object",
            "properties": {
                "result_id": {
                    "type": "string",
                    "description": "工具结果 id，例如 tr_1",
                },
                "offset": {
                    "type": "integer",
                    "description": "读取起始字符偏移，默认 0",
                },
                "limit": {
                    "type": "integer",
                    "description": "最多读取多少字符，默认 4000，最大 20000",
                },
            },
            "required": ["result_id"],
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "search_tool_results",
        "搜索缓存的长工具结果，可限定 result_id。",
        tool_results.search,
        parameters={
            "type": "object",
            "properties": {
                "result_id": {
                    "type": "string",
                    "description": "可选，只搜索指定 result_id",
                },
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个匹配行，默认 10，最大 20",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="logs", risk="read"),
    )
    registry.register(
        "save_context_summary",
        "保存一条项目上下文摘要。不能保存 API key、.env、密钥等敏感内容。",
        context_summaries.save_summary,
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "摘要主题，例如 测试失败诊断",
                },
                "summary": {
                    "type": "string",
                    "description": "上下文摘要内容",
                },
                "source": {
                    "type": "string",
                    "description": "可选来源，例如 tests/test_mini_agent.py",
                },
            },
            "required": ["topic", "summary"],
        },
        permission=ToolPermission(category="context", risk="write"),
    )
    registry.register(
        "search_context_summaries",
        "按关键词搜索项目上下文摘要。",
        context_summaries.search_summaries,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条，默认 10，最大 50",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="context", risk="read"),
    )
    registry.register(
        "list_context_summaries",
        "列出最近保存的项目上下文摘要。",
        context_summaries.list_summaries,
        parameters={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条，默认 20，最大 100",
                }
            },
        },
        permission=ToolPermission(category="context", risk="read"),
    )
    registry.register(
        "save_memory",
        "保存一条长期记忆到本地 JSONL。不能保存 API key、.env、密钥等敏感内容。",
        long_term_memory.save,
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要保存的长期记忆内容",
                },
                "tags": {
                    "type": "string",
                    "description": "逗号分隔标签，例如 preference,project",
                },
            },
            "required": ["text"],
        },
        permission=ToolPermission(category="memory", risk="write"),
    )
    registry.register(
        "search_memory",
        "按关键词搜索长期记忆。",
        long_term_memory.search,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条，默认 5，最大 20",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="memory", risk="read"),
    )
    registry.register(
        "list_memory",
        "列出长期记忆。",
        long_term_memory.list,
        parameters={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条，默认 20，最大 100",
                }
            },
        },
        permission=ToolPermission(category="memory", risk="read"),
    )
    registry.register(
        "delete_memory",
        "按 id 删除一条长期记忆。",
        long_term_memory.delete,
        parameters={
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "要删除的记忆 id，例如 mem_1",
                }
            },
            "required": ["memory_id"],
        },
        permission=ToolPermission(category="memory", risk="delete"),
    )
    registry.register(
        "start_task",
        "创建一个多步骤任务计划。只管理任务状态，不会自动执行步骤。",
        task_manager.start,
        parameters={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "任务目标",
                },
                "steps": {
                    "type": "string",
                    "description": "任务步骤，每行一个步骤",
                },
            },
            "required": ["goal", "steps"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "update_task_step",
        "更新当前任务中的一个步骤状态。状态只能是 pending、in_progress、done、blocked。",
        task_manager.update_step,
        parameters={
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "integer",
                    "description": "步骤 id",
                },
                "status": {
                    "type": "string",
                    "description": "步骤状态: pending / in_progress / done / blocked",
                },
                "note": {
                    "type": "string",
                    "description": "步骤备注",
                },
                "summary": {
                    "type": "string",
                    "description": "步骤完成或阻塞时的简短总结",
                },
            },
            "required": ["step_id", "status"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "list_task",
        "查看当前任务状态。",
        task_manager.list,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="task", risk="read"),
    )
    registry.register(
        "finish_task",
        "完成当前任务并记录总结。",
        task_manager.finish,
        parameters={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "任务完成总结",
                }
            },
            "required": ["summary"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "run_task_once",
        "受控推进当前任务的一步。只选择一个待执行步骤并标记为 in_progress，不会自动无限执行工具。",
        task_manager.run_once,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="task", risk="write"),
    )
    registry.register(
        "list_task_history",
        "列出最近完成的任务历史摘要。",
        task_manager.list_history,
        parameters={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条历史，默认 20，最大 100",
                }
            },
        },
        permission=ToolPermission(category="task", risk="read"),
    )
    registry.register(
        "search_task_history",
        "按关键词搜索已完成任务历史。",
        task_manager.search_history,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少条匹配历史，默认 10，最大 50",
                },
            },
            "required": ["query"],
        },
        permission=ToolPermission(category="task", risk="read"),
    )
    registry.register(
        "list_tool_permissions",
        "查看所有工具的权限分类和哪些工具需要确认。",
        registry.describe_permissions,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="local", risk="read"),
    )
    return registry
