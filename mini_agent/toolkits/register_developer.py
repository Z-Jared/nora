from mini_agent.registry import ToolPermission, ToolRegistry


def register_developer_tools(
    registry: ToolRegistry,
    workspace_files,
    diagnostics,
    repair_loop,
    symbol_index,
    shell_runner,
    process_manager,
) -> None:
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
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要运行项目测试",
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
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要运行受控修复测试循环",
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
