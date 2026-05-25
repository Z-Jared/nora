from pathlib import Path
from typing import Callable, Optional

from mini_agent.logs import JsonlToolLogger
from mini_agent.memory import LongTermMemory
from mini_agent.rag import ProjectRAG
from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.shell import ShellRunner
from mini_agent.task_runner import TaskManager
from mini_agent.toolkits.basic import calculate, current_time, make_plan
from mini_agent.toolkits.browser import BrowserBackend, BrowserTools
from mini_agent.toolkits.notes import NotesStore
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
) -> ToolRegistry:
    root = workspace_root or Path.cwd()
    notes = NotesStore(notes_path or Path("data/notes.txt"))
    workspace_files = WorkspaceFiles(root, confirm_action=lambda prompt: True)
    shell_runner = ShellRunner(root, confirm_action=lambda prompt: True)
    project_rag = ProjectRAG(root)
    web_tools = WebTools(fetcher=web_fetch)
    browser_tools = BrowserTools(root=root, backend=browser_backend)
    long_term_memory = LongTermMemory(long_term_memory_path or Path("data/long_term_memory.jsonl"))
    task_manager = TaskManager(task_state_path or Path("data/current_task.json"))
    logger = JsonlToolLogger(log_path or Path("logs/tool_calls.jsonl"))
    registry = ToolRegistry(logger=logger, confirm_action=confirm_action)

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
        "list_tool_permissions",
        "查看所有工具的权限分类和哪些工具需要确认。",
        registry.describe_permissions,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="local", risk="read"),
    )
    return registry
