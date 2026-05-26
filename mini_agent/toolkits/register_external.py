from mini_agent.registry import ToolPermission, ToolRegistry


def register_external_tools(registry: ToolRegistry, project_rag, web_tools, browser_tools) -> None:
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
        "保存当前浏览器页面截图到项目目录内的非敏感路径。需要用户确认。",
        browser_tools.screenshot,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对于项目根目录的截图路径，例如 screenshots/page.png",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要保存当前浏览器截图",
                },
            },
        },
        permission=ToolPermission(category="browser", risk="write", requires_confirmation=True),
    )
