import tempfile
import unittest
import json
from pathlib import Path

from mini_agent.controller import MiniAgent
from mini_agent.llm import ChatMessage, LLMResponse, OpenAICompatibleClient, ToolCall
from mini_agent.logs import JsonlToolLogger
from mini_agent.memory import ConversationMemory, LongTermMemory
from mini_agent.providers.anthropic import AnthropicClient
from mini_agent.providers.factory import build_llm_client
from mini_agent.providers.gemini import GeminiClient
from mini_agent.providers.openai_compatible import OpenAICompatibleClient
from mini_agent.rag import ProjectRAG
from mini_agent.registry import ToolPermission, ToolRegistry
from mini_agent.shell import ShellRunner
from mini_agent.settings import load_settings
from mini_agent.task_runner import TaskManager
from mini_agent.toolkits.browser import BrowserTools
from mini_agent.tools import WorkspaceFiles, build_default_registry, make_plan
from mini_agent.web_tools import WebTools


class ToolRegistryTests(unittest.TestCase):
    def test_calls_registered_tool_by_name(self):
        registry = ToolRegistry()
        registry.register("echo", "Echo input", lambda text: text)

        self.assertEqual(registry.call("echo", text="hello"), "hello")

    def test_rejects_unknown_tool(self):
        registry = ToolRegistry()

        with self.assertRaises(KeyError):
            registry.call("missing")

    def test_exports_openai_tool_schema(self):
        registry = ToolRegistry()
        registry.register(
            "echo",
            "Echo input",
            lambda text: text,
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )

        self.assertEqual(
            registry.to_openai_tools(),
            [
                {
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "description": "Echo input",
                        "parameters": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    },
                }
            ],
        )

    def test_logs_tool_calls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "tools.jsonl"
            registry = ToolRegistry(logger=JsonlToolLogger(log_path))
            registry.register("echo", "Echo input", lambda text: text)

            registry.call("echo", text="hello")

            entry = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(entry["tool"], "echo")
            self.assertEqual(entry["status"], "ok")
            self.assertEqual(entry["arguments"], {"text": "hello"})

    def test_cancels_permissioned_tool_before_calling_handler(self):
        called = []
        registry = ToolRegistry(confirm_action=lambda prompt: False)
        registry.register(
            "write_file",
            "Write file",
            lambda reason="": called.append(reason) or "wrote",
            permission=ToolPermission(
                category="workspace",
                risk="write",
                requires_confirmation=True,
            ),
        )

        result = registry.call("write_file", reason="测试权限")

        self.assertEqual(result, "已取消操作。")
        self.assertEqual(called, [])

    def test_describes_tool_permissions(self):
        registry = ToolRegistry()
        registry.register(
            "read_file",
            "Read file",
            lambda: "ok",
            permission=ToolPermission(category="workspace", risk="read"),
        )
        registry.register(
            "run_command",
            "Run command",
            lambda: "ok",
            permission=ToolPermission(
                category="terminal",
                risk="execute",
                requires_confirmation=True,
            ),
        )

        description = registry.describe_permissions()

        self.assertIn("read_file: workspace/read", description)
        self.assertIn("run_command: terminal/execute, 需要确认", description)


class MiniAgentTests(unittest.TestCase):
    def test_calculates_math_expression(self):
        agent = MiniAgent(build_default_registry())

        self.assertEqual(agent.run("计算 2 + 3 * 4"), "计算结果: 14")

    def test_handles_current_time_request(self):
        agent = MiniAgent(build_default_registry())

        answer = agent.run("现在几点")

        self.assertTrue(answer.startswith("当前时间: "))

    def test_saves_and_reads_notes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = build_default_registry(notes_path=Path(tmpdir) / "notes.txt")
            agent = MiniAgent(registry)

            self.assertEqual(agent.run("保存笔记 今天学习 agent 架构"), "笔记已保存。")
            self.assertEqual(agent.run("读取笔记"), "笔记:\n1. 今天学习 agent 架构")

    def test_returns_help_for_unknown_task(self):
        agent = MiniAgent(build_default_registry())

        self.assertIn("我还不会处理这个任务", agent.run("帮我订机票"))

    def test_uses_llm_for_unknown_task_when_configured(self):
        class FakeLLM:
            def complete(self, user_input):
                return f"LLM: {user_input}"

        agent = MiniAgent(build_default_registry(), llm=FakeLLM())

        self.assertEqual(agent.run("解释一下 agent 架构"), "LLM: 解释一下 agent 架构")

    def test_llm_can_call_tools(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="calculate",
                                arguments={"expression": "2 + 3 * 4"},
                            )
                        ],
                    )

                return LLMResponse(content="2 + 3 * 4 的结果是 14。")

        llm = FakeToolCallingLLM()
        agent = MiniAgent(build_default_registry(), llm=llm)

        self.assertEqual(agent.run("帮我算一下 2 + 3 * 4"), "2 + 3 * 4 的结果是 14。")
        self.assertEqual(llm.calls[0]["tools"][0]["function"]["name"], "calculate")
        self.assertEqual(llm.calls[1]["messages"][-1]["role"], "tool")
        self.assertEqual(llm.calls[1]["messages"][-1]["content"], "14")

    def test_llm_can_read_project_file(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="read_project_file",
                                arguments={"path": "README.md"},
                            )
                        ],
                    )

                return LLMResponse(content=f"读到了: {messages[-1]['content']}")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            registry = build_default_registry(workspace_root=root)
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            self.assertEqual(agent.run("读取 README"), "读到了: # Demo\n")

    def test_llm_can_list_project_files(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="list_project_files",
                                arguments={"max_files": 10},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / ".env").write_text("secret", encoding="utf-8")
            registry = build_default_registry(workspace_root=root)
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            answer = agent.run("列出项目文件")

        self.assertIn("README.md", answer)
        self.assertNotIn(".env", answer)

    def test_llm_can_make_plan(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="make_plan",
                                arguments={"goal": "给 agent 增加文件写入能力"},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        agent = MiniAgent(build_default_registry(), llm=FakeToolCallingLLM())

        self.assertIn("给 agent 增加文件写入能力", agent.run("规划下一步"))

    def test_llm_can_write_project_file_after_confirmation(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="write_project_file",
                                arguments={
                                    "path": "notes/dev.md",
                                    "content": "hello",
                                    "reason": "测试写文件",
                                },
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = build_default_registry(
                workspace_root=root,
                confirm_action=lambda prompt: True,
            )
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            self.assertIn("已写入文件", agent.run("创建 notes/dev.md"))
            self.assertEqual((root / "notes" / "dev.md").read_text(encoding="utf-8"), "hello")

    def test_llm_can_run_safe_shell_command_after_confirmation(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="run_shell_command",
                                arguments={
                                    "command": "pwd",
                                    "reason": "确认当前目录",
                                },
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = build_default_registry(
                workspace_root=root,
                confirm_action=lambda prompt: True,
            )
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            self.assertIn(str(root), agent.run("运行 pwd"))

    def test_llm_can_search_project_context(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="search_project_context",
                                arguments={"query": "tool calling", "max_results": 3},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("tool calling demo", encoding="utf-8")
            registry = build_default_registry(workspace_root=root)
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            self.assertIn("tool calling demo", agent.run("搜索项目里的 tool calling"))

    def test_llm_can_fetch_url(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="fetch_url",
                                arguments={"url": "https://example.com/docs"},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        def fake_fetch(url, timeout):
            return "<html><body><h1>Docs</h1><p>Hello web</p></body></html>"

        registry = build_default_registry(web_fetch=fake_fetch)
        agent = MiniAgent(registry, llm=FakeToolCallingLLM())

        self.assertIn("Hello web", agent.run("读取网页"))

    def test_llm_can_use_browser_tools(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="browser_open_url",
                                arguments={"url": "https://example.com"},
                            )
                        ],
                    )
                if len(self.calls) == 2:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_2",
                                name="browser_page_text",
                                arguments={"max_chars": 1000},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        registry = build_default_registry(browser_backend=FakeBrowserBackend())
        agent = MiniAgent(registry, llm=FakeToolCallingLLM())

        self.assertIn("Hello browser page", agent.run("用浏览器读取 example.com"))

    def test_llm_can_save_and_search_long_term_memory(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="save_memory",
                                arguments={
                                    "text": "项目偏好: 先写测试再实现",
                                    "tags": "preference,tdd",
                                },
                            )
                        ],
                    )
                if len(self.calls) == 2:
                    return LLMResponse(content=messages[-1]["content"])
                if len(self.calls) == 3:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_2",
                                name="search_memory",
                                arguments={"query": "测试", "max_results": 5},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.jsonl"
            registry = build_default_registry(long_term_memory_path=memory_path)
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            self.assertIn("已保存记忆", agent.run("记住我的偏好"))
            self.assertIn("先写测试再实现", agent.run("搜索长期记忆里的测试偏好"))

    def test_llm_can_start_and_list_task(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="start_task",
                                arguments={
                                    "goal": "给 agent 增加新工具",
                                    "steps": "读代码\n写测试\n实现\n运行测试",
                                },
                            )
                        ],
                    )
                if len(self.calls) == 2:
                    return LLMResponse(content=messages[-1]["content"])
                if len(self.calls) == 3:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_2",
                                name="list_task",
                                arguments={},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "task.json"
            registry = build_default_registry(task_state_path=task_path)
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            self.assertIn("已创建任务", agent.run("创建任务"))
            self.assertIn("给 agent 增加新工具", agent.run("查看任务"))

    def test_llm_can_run_task_once(self):
        class FakeToolCallingLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append({"messages": messages, "tools": tools})
                if len(self.calls) == 1:
                    return LLMResponse(
                        content="",
                        tool_calls=[
                            ToolCall(
                                call_id="call_1",
                                name="run_task_once",
                                arguments={},
                            )
                        ],
                    )

                return LLMResponse(content=messages[-1]["content"])

        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "task.json"
            manager = TaskManager(task_path)
            manager.start("给 agent 增加新工具", "读代码\n写测试")
            registry = build_default_registry(task_state_path=task_path)
            agent = MiniAgent(registry, llm=FakeToolCallingLLM())

            answer = agent.run("执行当前任务下一步")

        self.assertIn("下一步: 1. 读代码", answer)

    def test_llm_receives_previous_conversation_messages(self):
        class FakeMemoryLLM:
            def __init__(self):
                self.calls = []

            def chat(self, messages, tools=None):
                self.calls.append(messages)
                return LLMResponse(content=f"第 {len(self.calls)} 次回复")

        llm = FakeMemoryLLM()
        agent = MiniAgent(
            build_default_registry(),
            llm=llm,
            memory=ConversationMemory(max_messages=10),
        )

        agent.run("第一轮")
        agent.run("第二轮")

        second_call_messages = llm.calls[1]
        self.assertEqual(second_call_messages[0], {"role": "user", "content": "第一轮"})
        self.assertEqual(second_call_messages[1], {"role": "assistant", "content": "第 1 次回复"})
        self.assertEqual(second_call_messages[2], {"role": "user", "content": "第二轮"})

    def test_records_local_rule_responses_in_memory(self):
        memory = ConversationMemory(max_messages=10)
        agent = MiniAgent(build_default_registry(), memory=memory)

        agent.run("计算 1 + 2")

        self.assertEqual(
            memory.messages(),
            [
                {"role": "user", "content": "计算 1 + 2"},
                {"role": "assistant", "content": "计算结果: 3"},
            ],
        )


class WorkspaceFilesTests(unittest.TestCase):
    def test_reads_text_file_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs").mkdir()
            (root / "docs" / "note.txt").write_text("hello", encoding="utf-8")

            files = WorkspaceFiles(root)

            self.assertEqual(files.read("docs/note.txt"), "hello")

    def test_rejects_paths_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir))

            self.assertIn("拒绝读取", files.read("../secret.txt"))

    def test_rejects_env_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env").write_text("LLM_API_KEY=secret", encoding="utf-8")

            files = WorkspaceFiles(root)

            self.assertIn("拒绝读取", files.read(".env"))

    def test_lists_workspace_files_without_sensitive_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / ".env").write_text("secret", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "notes.txt").write_text("private note", encoding="utf-8")

            files = WorkspaceFiles(root)

            listing = files.list(max_files=10)

        self.assertIn("README.md", listing)
        self.assertNotIn(".env", listing)
        self.assertNotIn("data/notes.txt", listing)

    def test_write_file_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root, confirm_action=lambda prompt: False)

            result = files.write("docs/new.md", "hello", reason="test")

        self.assertIn("已取消", result)
        self.assertFalse((root / "docs" / "new.md").exists())

    def test_writes_file_inside_workspace_when_confirmed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)

            result = files.write("docs/new.md", "hello", reason="test")

            self.assertIn("已写入文件", result)
            self.assertEqual((root / "docs" / "new.md").read_text(encoding="utf-8"), "hello")

    def test_write_rejects_sensitive_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = WorkspaceFiles(Path(tmpdir), confirm_action=lambda prompt: True)

            result = files.write(".env", "LLM_API_KEY=secret", reason="test")

        self.assertIn("拒绝写入", result)

    def test_replace_file_text_when_confirmed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "README.md"
            target.write_text("hello old", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)

            result = files.replace("README.md", "old", "new", reason="test")

            self.assertIn("已修改文件", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello new")

    def test_replace_file_text_requires_existing_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "README.md"
            target.write_text("hello", encoding="utf-8")
            files = WorkspaceFiles(root, confirm_action=lambda prompt: True)

            result = files.replace("README.md", "missing", "new", reason="test")

            self.assertIn("没有找到要替换的文本", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello")


class PlannerTests(unittest.TestCase):
    def test_make_plan_returns_numbered_steps(self):
        plan = make_plan("给 agent 增加文件写入能力")

        self.assertIn("目标: 给 agent 增加文件写入能力", plan)
        self.assertIn("1. 明确", plan)


class ConversationMemoryTests(unittest.TestCase):
    def test_keeps_recent_messages_only(self):
        memory = ConversationMemory(max_messages=3)

        memory.add_user("one")
        memory.add_assistant("two")
        memory.add_user("three")
        memory.add_assistant("four")

        self.assertEqual(
            memory.messages(),
            [
                {"role": "assistant", "content": "two"},
                {"role": "user", "content": "three"},
                {"role": "assistant", "content": "four"},
            ],
        )

    def test_skips_sensitive_content(self):
        memory = ConversationMemory(max_messages=10)

        memory.add_user("LLM_API_KEY=secret")

        self.assertEqual(memory.messages(), [])


class LongTermMemoryTests(unittest.TestCase):
    def test_saves_and_searches_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.jsonl")

            result = memory.save("项目偏好: 先写测试再实现", tags="preference,tdd")
            search = memory.search("测试", max_results=5)

        self.assertIn("已保存记忆", result)
        self.assertIn("先写测试再实现", search)
        self.assertIn("preference", search)

    def test_rejects_sensitive_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.jsonl")

            result = memory.save("OPENAI_API_KEY=secret")

            self.assertIn("拒绝保存", result)
            self.assertFalse((Path(tmpdir) / "memory.jsonl").exists())

    def test_lists_and_deletes_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.jsonl")
            memory.save("第一条记忆", tags="one")
            memory.save("第二条记忆", tags="two")

            listing = memory.list(max_results=10)
            delete_result = memory.delete("mem_1")
            after_delete = memory.list(max_results=10)

        self.assertIn("mem_1", listing)
        self.assertIn("mem_2", listing)
        self.assertIn("已删除记忆: mem_1", delete_result)
        self.assertNotIn("第一条记忆", after_delete)
        self.assertIn("第二条记忆", after_delete)


class TaskManagerTests(unittest.TestCase):
    def test_starts_updates_lists_and_finishes_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")

            started = manager.start("给 agent 增加新工具", "读代码\n写测试\n实现")
            updated = manager.update_step(2, "done", "测试已写好")
            listing = manager.list()
            finished = manager.finish("实现完成并通过测试")
            finished_listing = manager.list()

        self.assertIn("已创建任务", started)
        self.assertIn("2. [done] 写测试 - 测试已写好", listing)
        self.assertIn("已完成任务", finished)
        self.assertIn("status=finished", finished_listing)

    def test_rejects_invalid_step_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")

            result = manager.update_step(1, "bad", "nope")

        self.assertIn("无效状态", result)

    def test_reports_no_active_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")

            self.assertEqual(manager.list(), "暂无任务。")

    def test_run_once_marks_next_pending_step_in_progress(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("给 agent 增加新工具", "读代码\n写测试")

            result = manager.run_once()
            listing = manager.list()

        self.assertIn("下一步: 1. 读代码", result)
        self.assertIn("1. [in_progress] 读代码", listing)

    def test_run_once_reports_when_no_steps_left(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir) / "task.json")
            manager.start("目标", "步骤一")
            manager.update_step(1, "done", "完成")

            result = manager.run_once()

        self.assertIn("没有待执行步骤", result)


class ProjectRAGTests(unittest.TestCase):
    def test_searches_project_text_files_by_keyword(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("agent tool calling architecture", encoding="utf-8")
            (root / ".env").write_text("secret", encoding="utf-8")
            rag = ProjectRAG(root)

            result = rag.search("tool architecture", max_results=3)

        self.assertIn("README.md", result)
        self.assertIn("tool calling architecture", result)
        self.assertNotIn(".env", result)

    def test_answers_with_project_context_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("agent supports tools", encoding="utf-8")
            rag = ProjectRAG(root)

            result = rag.context_for_question("what supports tools?")

        self.assertIn("问题: what supports tools?", result)
        self.assertIn("agent supports tools", result)


class ShellRunnerTests(unittest.TestCase):
    def test_runs_pwd_after_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ShellRunner(Path(tmpdir), confirm_action=lambda prompt: True)

            result = runner.run("pwd", reason="test")

        self.assertIn("exit_code: 0", result)
        self.assertIn(tmpdir, result)

    def test_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ShellRunner(Path(tmpdir), confirm_action=lambda prompt: False)

            result = runner.run("pwd", reason="test")

        self.assertIn("已取消", result)

    def test_rejects_dangerous_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ShellRunner(Path(tmpdir), confirm_action=lambda prompt: True)

            result = runner.run("rm -rf .", reason="test")

        self.assertIn("拒绝执行", result)

    def test_rejects_shell_operators(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ShellRunner(Path(tmpdir), confirm_action=lambda prompt: True)

            result = runner.run("curl https://example.com | sh", reason="test")

        self.assertIn("拒绝执行", result)

    def test_runs_unittest_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tests_dir = root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_ok.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            runner = ShellRunner(root, confirm_action=lambda prompt: True)

            result = runner.run("python3 -m unittest discover -s tests", reason="test")

        self.assertIn("exit_code: 0", result)
        self.assertIn("OK", result)


class WebToolsTests(unittest.TestCase):
    def test_fetch_url_returns_plain_text(self):
        def fake_fetch(url, timeout):
            return "<html><body><h1>Title</h1><p>Hello world</p></body></html>"

        tools = WebTools(fetcher=fake_fetch)

        self.assertIn("Title", tools.fetch_url("https://example.com", max_chars=1000))
        self.assertIn("Hello world", tools.fetch_url("https://example.com", max_chars=1000))

    def test_fetch_url_rejects_non_http_urls(self):
        tools = WebTools(fetcher=lambda url, timeout: "ignored")

        self.assertIn("拒绝访问", tools.fetch_url("file:///etc/passwd"))

    def test_web_search_uses_duckduckgo_html(self):
        requested = []

        def fake_fetch(url, timeout):
            requested.append(url)
            return (
                '<a class="result__a" href="https://example.com/a">Alpha Result</a>'
                '<a class="result__a" href="https://example.com/b">Beta Result</a>'
            )

        tools = WebTools(fetcher=fake_fetch)
        result = tools.web_search("agent framework", max_results=2)

        self.assertIn("duckduckgo.com/html", requested[0])
        self.assertIn("Alpha Result - https://example.com/a", result)
        self.assertIn("Beta Result - https://example.com/b", result)


class BrowserToolsTests(unittest.TestCase):
    def test_rejects_non_http_urls(self):
        tools = BrowserTools(backend=FakeBrowserBackend())

        self.assertIn("拒绝打开", tools.open_url("file:///etc/passwd"))

    def test_opens_url_and_reads_page_state(self):
        backend = FakeBrowserBackend()
        tools = BrowserTools(backend=backend)

        opened = tools.open_url("https://example.com")
        title = tools.page_title()
        text = tools.page_text(max_chars=20)

        self.assertEqual(opened, "已打开页面: https://example.com")
        self.assertEqual(backend.opened_url, "https://example.com")
        self.assertEqual(title, "页面标题: Demo Page")
        self.assertEqual(text, "Hello browser page")

    def test_click_and_fill_require_selectors(self):
        backend = FakeBrowserBackend()
        tools = BrowserTools(backend=backend)

        self.assertIn("请提供 CSS selector", tools.click(""))
        self.assertIn("请提供 CSS selector", tools.fill("", "hello"))
        self.assertEqual(tools.click("#submit"), "已点击: #submit")
        self.assertEqual(tools.fill("#q", "hello"), "已输入文本: #q")
        self.assertEqual(backend.clicked, ["#submit"])
        self.assertEqual(backend.filled, [("#q", "hello")])

    def test_screenshot_writes_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backend = FakeBrowserBackend()
            tools = BrowserTools(root=root, backend=backend)

            result = tools.screenshot("screenshots/page.png")

            self.assertEqual(result, "已保存截图: screenshots/page.png")
            self.assertTrue((root / "screenshots" / "page.png").exists())

    def test_screenshot_rejects_paths_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = BrowserTools(root=Path(tmpdir), backend=FakeBrowserBackend())

            result = tools.screenshot("../page.png")

        self.assertIn("拒绝截图", result)

    def test_default_registry_includes_browser_tools(self):
        registry = build_default_registry()
        tool_names = [tool["function"]["name"] for tool in registry.to_openai_tools()]

        self.assertIn("browser_open_url", tool_names)
        self.assertIn("browser_page_text", tool_names)
        self.assertIn("browser_click", tool_names)


class FakeBrowserBackend:
    def __init__(self):
        self.opened_url = ""
        self.clicked = []
        self.filled = []

    def open_url(self, url: str) -> None:
        self.opened_url = url

    def page_title(self) -> str:
        return "Demo Page"

    def page_text(self) -> str:
        return "Hello browser page"

    def click(self, selector: str) -> None:
        self.clicked.append(selector)

    def fill(self, selector: str, text: str) -> None:
        self.filled.append((selector, text))

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake png")


class SettingsTests(unittest.TestCase):
    def test_loads_provider_settings_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "LLM_PROVIDER=openai-compatible",
                        "LLM_BASE_URL=https://example.com/v1",
                        "LLM_API_KEY=test-key",
                        "LLM_MODEL=test-model",
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_settings(env_path=env_path, environ={})

        self.assertTrue(settings.is_llm_enabled)
        self.assertEqual(settings.base_url, "https://example.com/v1")
        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.model, "test-model")


class ProviderFactoryTests(unittest.TestCase):
    def test_builds_openai_compatible_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "LLM_PROVIDER=openai-compatible",
                        "LLM_BASE_URL=https://example.com/v1",
                        "LLM_API_KEY=test-key",
                        "LLM_MODEL=test-model",
                    ]
                ),
                encoding="utf-8",
            )
            settings = load_settings(env_path=env_path, environ={})

        client = build_llm_client(settings)

        self.assertIsInstance(client, OpenAICompatibleClient)

    def test_builds_anthropic_provider(self):
        settings = load_settings(
            environ={
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "anthropic-key",
                "ANTHROPIC_MODEL": "claude-test",
            }
        )

        client = build_llm_client(settings)

        self.assertIsInstance(client, AnthropicClient)

    def test_builds_gemini_provider(self):
        settings = load_settings(
            environ={
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "gemini-key",
                "GEMINI_MODEL": "gemini-test",
            }
        )

        client = build_llm_client(settings)

        self.assertIsInstance(client, GeminiClient)


class AnthropicClientTests(unittest.TestCase):
    def test_posts_messages_request_and_parses_tool_use(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {
                "content": [
                    {"type": "text", "text": "我需要计算。"},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "calculate",
                        "input": {"expression": "1 + 2"},
                    },
                ]
            }

        client = AnthropicClient(
            base_url="https://api.anthropic.test/v1",
            api_key="anthropic-key",
            model="claude-test",
            transport=fake_transport,
        )

        result = client.chat(
            [{"role": "user", "content": "算一下 1 + 2"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "description": "计算数学表达式",
                        "parameters": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                            "required": ["expression"],
                        },
                    },
                }
            ],
        )

        self.assertEqual(requests[0]["url"], "https://api.anthropic.test/v1/messages")
        self.assertEqual(requests[0]["headers"]["x-api-key"], "anthropic-key")
        self.assertEqual(requests[0]["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(requests[0]["payload"]["model"], "claude-test")
        self.assertEqual(requests[0]["payload"]["tools"][0]["name"], "calculate")
        self.assertEqual(result.content, "我需要计算。")
        self.assertEqual(result.tool_calls[0].call_id, "toolu_1")
        self.assertEqual(result.tool_calls[0].name, "calculate")
        self.assertEqual(result.tool_calls[0].arguments, {"expression": "1 + 2"})


class GeminiClientTests(unittest.TestCase):
    def test_posts_generate_content_request_and_parses_function_call(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "我需要计算。"},
                                {
                                    "functionCall": {
                                        "name": "calculate",
                                        "args": {"expression": "1 + 2"},
                                    }
                                },
                            ]
                        }
                    }
                ]
            }

        client = GeminiClient(
            base_url="https://generativelanguage.googleapis.test/v1beta",
            api_key="gemini-key",
            model="gemini-test",
            transport=fake_transport,
        )

        result = client.chat(
            [{"role": "user", "content": "算一下 1 + 2"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "description": "计算数学表达式",
                        "parameters": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                            "required": ["expression"],
                        },
                    },
                }
            ],
        )

        self.assertEqual(
            requests[0]["url"],
            "https://generativelanguage.googleapis.test/v1beta/models/gemini-test:generateContent",
        )
        self.assertEqual(requests[0]["headers"]["x-goog-api-key"], "gemini-key")
        self.assertEqual(
            requests[0]["payload"]["tools"][0]["functionDeclarations"][0]["name"],
            "calculate",
        )
        self.assertEqual(result.content, "我需要计算。")
        self.assertEqual(result.tool_calls[0].name, "calculate")
        self.assertEqual(result.tool_calls[0].arguments, {"expression": "1 + 2"})


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_posts_chat_completion_request(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {"choices": [{"message": {"content": "模型回复"}}]}

        client = OpenAICompatibleClient(
            base_url="https://relay.example.com/v1",
            api_key="relay-key",
            model="gpt-test",
            transport=fake_transport,
        )

        result = client.complete("你好")

        self.assertEqual(result, "模型回复")
        self.assertEqual(requests[0]["url"], "https://relay.example.com/v1/chat/completions")
        self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer relay-key")
        self.assertEqual(requests[0]["payload"]["model"], "gpt-test")
        self.assertEqual(
            requests[0]["payload"]["messages"],
            [
                ChatMessage(role="system", content=client.system_prompt).to_dict(),
                ChatMessage(role="user", content="你好").to_dict(),
            ],
        )

    def test_posts_tools_and_parses_tool_calls(self):
        requests = []

        def fake_transport(url, headers, payload, timeout):
            requests.append(payload)
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "reasoning_content": "需要计算。",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "calculate",
                                        "arguments": '{"expression": "1 + 2"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }

        client = OpenAICompatibleClient(
            base_url="https://relay.example.com/v1",
            api_key="relay-key",
            model="gpt-test",
            transport=fake_transport,
        )

        result = client.chat(
            [{"role": "user", "content": "算一下 1 + 2"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "description": "计算数学表达式",
                        "parameters": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                            "required": ["expression"],
                        },
                    },
                }
            ],
        )

        self.assertEqual(requests[0]["tools"][0]["function"]["name"], "calculate")
        self.assertEqual(result.tool_calls[0].call_id, "call_123")
        self.assertEqual(result.tool_calls[0].name, "calculate")
        self.assertEqual(result.tool_calls[0].arguments, {"expression": "1 + 2"})
        self.assertEqual(result.reasoning_content, "需要计算。")
        self.assertEqual(result.to_assistant_message()["reasoning_content"], "需要计算。")
        self.assertEqual(result.to_assistant_message()["content"], "")


if __name__ == "__main__":
    unittest.main()
