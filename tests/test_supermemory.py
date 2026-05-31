"""Tests for optional Supermemory toolkit (TASK-036)."""

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from mini_agent.database import NoraDB
from mini_agent.toolkits.supermemory import SupermemoryClient, DEFAULT_BASE_URL, CONTAINER_TAG
from mini_agent.toolkits.register_supermemory import (
    register_supermemory_tools,
    _bound_search_output,
    _bound_profile_output,
    _bound_metadata,
)
from mini_agent.registry import ToolPermission, ToolRegistry


def _fake_response(body: dict, status: int = 200):
    data = json.dumps(body).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = data
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.status = status
    return resp


class SupermemoryClientTests(unittest.TestCase):
    def test_from_env_returns_none_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(SupermemoryClient.from_env())

    def test_from_env_creates_client_with_key(self):
        env = {"SUPERMEMORY_API_KEY": "sk-test-123"}
        with patch.dict("os.environ", env, clear=True):
            client = SupermemoryClient.from_env()
            self.assertIsNotNone(client)
            self.assertEqual(client.api_key, "sk-test-123")
            self.assertEqual(client.base_url, DEFAULT_BASE_URL)

    def test_from_env_custom_base_url(self):
        env = {"SUPERMEMORY_API_KEY": "sk-test", "SUPERMEMORY_BASE_URL": "https://custom.example.com"}
        with patch.dict("os.environ", env, clear=True):
            client = SupermemoryClient.from_env()
            self.assertEqual(client.base_url, "https://custom.example.com")

    def test_from_env_custom_container_tag(self):
        env = {"SUPERMEMORY_API_KEY": "sk-test", "SUPERMEMORY_CONTAINER_TAG": "my_project"}
        with patch.dict("os.environ", env, clear=True):
            client = SupermemoryClient.from_env()
            self.assertEqual(client.container_tag, "my_project")

    def test_from_env_default_container_tag(self):
        env = {"SUPERMEMORY_API_KEY": "sk-test"}
        with patch.dict("os.environ", env, clear=True):
            client = SupermemoryClient.from_env()
            self.assertEqual(client.container_tag, CONTAINER_TAG)

    def test_save_calls_correct_endpoint(self):
        client = SupermemoryClient(api_key="sk-test", container_tag="test_tag")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"id": "doc_1", "status": "processing"})
            result = client.save(content="hello world")
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.full_url, f"{DEFAULT_BASE_URL}/v3/documents")
            self.assertEqual(req.get_header("Authorization"), "Bearer sk-test")
            body = json.loads(req.data)
            self.assertEqual(body["content"], "hello world")
            self.assertEqual(body["containerTag"], "test_tag")
            self.assertEqual(body["taskType"], "memory")
            self.assertEqual(result["id"], "doc_1")

    def test_save_truncates_long_content(self):
        client = SupermemoryClient(api_key="sk-test")
        long_content = "x" + "y" * 20000
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"id": "doc_1", "status": "done"})
            client.save(content=long_content)
            body = json.loads(mock_urlopen.call_args[0][0].data)
            self.assertLessEqual(len(body["content"]), 10000)

    def test_search_calls_correct_endpoint(self):
        client = SupermemoryClient(api_key="sk-test", container_tag="nora")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"results": [], "total": 0})
            client.search(query="test query", limit=3, threshold=0.7)
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.full_url, f"{DEFAULT_BASE_URL}/v4/search")
            body = json.loads(req.data)
            self.assertEqual(body["q"], "test query")
            self.assertEqual(body["containerTag"], "nora")
            self.assertEqual(body["limit"], 3)
            self.assertEqual(body["threshold"], 0.7)

    def test_search_clamps_limit(self):
        client = SupermemoryClient(api_key="sk-test")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"results": [], "total": 0})
            client.search(query="q", limit=999)
            body = json.loads(mock_urlopen.call_args[0][0].data)
            self.assertEqual(body["limit"], 20)

            client.search(query="q", limit=0)
            body = json.loads(mock_urlopen.call_args[0][0].data)
            self.assertEqual(body["limit"], 1)

    def test_profile_calls_correct_endpoint(self):
        client = SupermemoryClient(api_key="sk-test", container_tag="proj")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"profile": {"static": [], "dynamic": []}})
            client.profile(query="interests")
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.full_url, f"{DEFAULT_BASE_URL}/v4/profile")
            body = json.loads(req.data)
            self.assertEqual(body["containerTag"], "proj")
            self.assertEqual(body["q"], "interests")

    def test_profile_without_query(self):
        client = SupermemoryClient(api_key="sk-test")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _fake_response({"profile": {"static": [], "dynamic": []}})
            client.profile()
            body = json.loads(mock_urlopen.call_args[0][0].data)
            self.assertNotIn("q", body)

    def test_network_error_propagates(self):
        import urllib.error
        client = SupermemoryClient(api_key="sk-test")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            with self.assertRaises(urllib.error.URLError):
                client.save(content="test")


class BoundingFunctionTests(unittest.TestCase):
    def test_bound_search_output_drops_raw_chunks(self):
        result = {
            "results": [
                {"id": "m1", "memory": "fact one", "similarity": 0.9},
                {"id": "c1", "chunk": "A" * 3000, "similarity": 0.8},
            ],
            "total": 2,
        }
        bounded = _bound_search_output(result)
        self.assertEqual(len(bounded["results"]), 2)
        self.assertEqual(bounded["results"][0]["memory"], "fact one")
        self.assertNotIn("chunk", bounded["results"][1])
        self.assertIn("chunk_preview", bounded["results"][1])
        self.assertLessEqual(len(bounded["results"][1]["chunk_preview"]), 500)

    def test_bound_search_output_truncates_long_memory(self):
        result = {"results": [{"id": "m1", "memory": "x" * 5000}], "total": 1}
        bounded = _bound_search_output(result)
        self.assertLessEqual(len(bounded["results"][0]["memory"]), 2000)

    def test_bound_profile_output_limits_items(self):
        result = {
            "profile": {
                "static": [f"fact {i}" for i in range(50)],
                "dynamic": [f"dyn {i}" for i in range(50)],
            }
        }
        bounded = _bound_profile_output(result)
        self.assertLessEqual(len(bounded["profile"]["static"]), 20)
        self.assertLessEqual(len(bounded["profile"]["dynamic"]), 20)


class MetadataBoundingTests(unittest.TestCase):
    def test_keeps_scalar_strings(self):
        meta = {"category": "research", "source": "user"}
        bounded = _bound_metadata(meta)
        self.assertEqual(bounded, meta)

    def test_keeps_numbers_and_bools(self):
        meta = {"count": 42, "ratio": 3.14, "active": True}
        bounded = _bound_metadata(meta)
        self.assertEqual(bounded["count"], 42)
        self.assertEqual(bounded["ratio"], 3.14)
        self.assertEqual(bounded["active"], True)

    def test_truncates_long_strings(self):
        meta = {"long": "x" * 1000}
        bounded = _bound_metadata(meta)
        self.assertEqual(len(bounded["long"]), 300)

    def test_drops_nested_dicts(self):
        meta = {"safe": "ok", "nested": {"secret": "DATA"}}
        bounded = _bound_metadata(meta)
        self.assertEqual(bounded, {"safe": "ok"})

    def test_drops_lists(self):
        meta = {"safe": "ok", "items": ["a", "b", "c"]}
        bounded = _bound_metadata(meta)
        self.assertEqual(bounded, {"safe": "ok"})

    def test_drops_secret_like_metadata(self):
        meta = {
            "safe": "ok",
            "token": "sk-secret",
            "api_key": "value",
            "note": "Bearer secret",
        }
        bounded = _bound_metadata(meta)
        self.assertEqual(bounded, {"safe": "ok"})

    def test_limits_field_count(self):
        meta = {f"key_{i}": f"val_{i}" for i in range(50)}
        bounded = _bound_metadata(meta)
        self.assertEqual(len(bounded), 20)

    def test_empty_metadata(self):
        self.assertEqual(_bound_metadata({}), {})

    def test_search_output_uses_bounded_metadata(self):
        result = {
            "results": [
                {
                    "id": "m1",
                    "memory": "fact",
                    "metadata": {
                        "category": "test",
                        "nested": {"leak": "SECRET"},
                        "long_val": "y" * 500,
                        "token": "sk-leak",
                    },
                }
            ],
            "total": 1,
        }
        bounded = _bound_search_output(result)
        meta = bounded["results"][0]["metadata"]
        self.assertEqual(meta["category"], "test")
        self.assertNotIn("nested", meta)
        self.assertNotIn("token", meta)
        self.assertEqual(len(meta["long_val"]), 300)


class SupermemoryRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.db = NoraDB(self.root / "test.db")
        self.registry = ToolRegistry()

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_tools_registered_when_client_provided(self):
        client = SupermemoryClient(api_key="sk-test")
        register_supermemory_tools(self.registry, client)
        tools = {t.name for t in self.registry._tools.values()}
        self.assertIn("supermemory_save", tools)
        self.assertIn("supermemory_search", tools)
        self.assertIn("supermemory_profile", tools)

    def test_tools_registered_when_client_none(self):
        register_supermemory_tools(self.registry, None)
        tools = {t.name for t in self.registry._tools.values()}
        self.assertIn("supermemory_save", tools)
        self.assertIn("supermemory_search", tools)
        self.assertIn("supermemory_profile", tools)

    def test_save_returns_error_without_key(self):
        register_supermemory_tools(self.registry, None)
        result = self.registry.call("supermemory_save", content="test")
        parsed = json.loads(result)
        self.assertIn("error", parsed)
        self.assertIn("SUPERMEMORY_API_KEY", parsed["error"])

    def test_search_returns_error_without_key(self):
        register_supermemory_tools(self.registry, None)
        result = self.registry.call("supermemory_search", query="test")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_profile_returns_error_without_key(self):
        register_supermemory_tools(self.registry, None)
        result = self.registry.call("supermemory_profile")
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_save_sends_only_user_content(self):
        client = SupermemoryClient(api_key="sk-test")
        register_supermemory_tools(self.registry, client)
        with patch.object(client, "save", return_value={"id": "d1", "status": "done"}) as mock_save:
            self.registry.call("supermemory_save", content="my important note")
            mock_save.assert_called_once()
            call_kwargs = mock_save.call_args[1]
            self.assertEqual(call_kwargs["content"], "my important note")
            # metadata should be None when not provided
            self.assertIsNone(call_kwargs.get("metadata"))

    def test_save_with_metadata_json(self):
        client = SupermemoryClient(api_key="sk-test")
        register_supermemory_tools(self.registry, client)
        with patch.object(client, "save", return_value={"id": "d1"}) as mock_save:
            self.registry.call("supermemory_save", content="note", metadata='{"cat": "test"}')
            call_kwargs = mock_save.call_args[1]
            self.assertEqual(call_kwargs["metadata"], {"cat": "test"})

    def test_save_with_invalid_metadata_string(self):
        client = SupermemoryClient(api_key="sk-test")
        register_supermemory_tools(self.registry, client)
        with patch.object(client, "save", return_value={"id": "d1"}) as mock_save:
            self.registry.call("supermemory_save", content="note", metadata="not json")
            call_kwargs = mock_save.call_args[1]
            self.assertEqual(call_kwargs["metadata"], {"value": "not json"})

    def test_search_returns_bounded_output(self):
        client = SupermemoryClient(api_key="sk-test")
        register_supermemory_tools(self.registry, client)
        raw_result = {
            "results": [
                {"id": "m1", "memory": "fact", "similarity": 0.9, "metadata": {}},
            ],
            "total": 1,
        }
        with patch.object(client, "search", return_value=raw_result):
            result = self.registry.call("supermemory_search", query="test")
            parsed = json.loads(result)
            self.assertIn("results", parsed)
            self.assertEqual(len(parsed["results"]), 1)
            self.assertEqual(parsed["results"][0]["memory"], "fact")

    def test_search_bounded_does_not_leak_raw_chunks(self):
        client = SupermemoryClient(api_key="sk-test")
        register_supermemory_tools(self.registry, client)
        raw_chunk = "X" * 3000  # large raw chunk
        raw_result = {
            "results": [{"id": "c1", "chunk": raw_chunk, "similarity": 0.7}],
            "total": 1,
        }
        with patch.object(client, "search", return_value=raw_result):
            result = self.registry.call("supermemory_search", query="test")
            # Full raw chunk must not appear — only a 500-char preview
            self.assertNotIn(raw_chunk, result)
            self.assertIn("chunk_preview", result)

    def test_api_error_returns_json(self):
        client = SupermemoryClient(api_key="sk-test")
        register_supermemory_tools(self.registry, client)
        with patch.object(client, "save", side_effect=RuntimeError("network down")):
            result = self.registry.call("supermemory_save", content="test")
            parsed = json.loads(result)
            self.assertIn("error", parsed)
            self.assertIn("network down", parsed["error"])

    def test_registry_wiring_does_not_break_existing_memory_tools(self):
        """Build a full registry and verify local memory tools still work."""
        from mini_agent.toolkits import build_default_registry
        full_registry = build_default_registry(
            db=self.db, workspace_root=self.root,
            confirm_action=lambda _: True,
        )
        # Save and search should work on local memory
        full_registry.call("save_memory", text="test local memory", tags="test")
        result = full_registry.call("search_memory", query="local memory")
        # search_memory may return JSON list or plain text — should not raise
        self.assertTrue(len(result) > 0)

    def test_no_key_keeps_full_offline_suite_passing(self):
        """With no API key configured, all tools return errors but don't crash."""
        env = {k: v for k, v in __import__("os").environ.items() if "SUPERMEMORY" not in k}
        with patch.dict("os.environ", env, clear=True):
            from mini_agent.toolkits import build_default_registry
            full_registry = build_default_registry(
                db=self.db, workspace_root=self.root,
                confirm_action=lambda _: True,
            )
            # supermemory tools should exist and return errors gracefully
            result = full_registry.call("supermemory_save", content="x")
            parsed = json.loads(result)
            self.assertIn("error", parsed)

            result = full_registry.call("supermemory_search", query="x")
            parsed = json.loads(result)
            self.assertIn("error", parsed)

            result = full_registry.call("supermemory_profile")
            parsed = json.loads(result)
            self.assertIn("error", parsed)


if __name__ == "__main__":
    unittest.main()
