from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.toolkits.basic import calculate, current_time, make_plan


def register_core_tools(registry: ToolRegistry, notes, workspace_files) -> None:
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
