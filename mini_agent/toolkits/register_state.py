from mini_agent.registry import ToolPermission, ToolRegistry


def register_state_tools(
    registry: ToolRegistry,
    logger,
    tool_results,
    context_summaries,
    long_term_memory,
    task_manager,
) -> None:
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
        long_term_memory.save_str,
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
        "restore_task",
        "从已完成任务历史恢复一个任务为当前 active 任务，便于继续 blocked 或 pending 步骤。",
        task_manager.restore,
        parameters={
            "type": "object",
            "properties": {
                "history_id": {
                    "type": "string",
                    "description": "任务历史 id，例如 task_1",
                }
            },
            "required": ["history_id"],
        },
        permission=ToolPermission(category="task", risk="write"),
    )
