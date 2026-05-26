import tempfile
import unittest
from pathlib import Path

from mini_agent.toolkits.browser import BrowserTools
from mini_agent.tools import build_default_registry


class BrowserToolsTests(unittest.TestCase):
    def test_rejects_non_http_urls(self):
        tools = BrowserTools(backend=FakeBrowserBackend())

        self.assertIn("拒绝打开", tools.open_url("file:///etc/passwd"))

    def test_rejects_private_and_local_network_urls(self):
        backend = FakeBrowserBackend()
        tools = BrowserTools(backend=backend)

        for url in [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://192.168.1.1",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]:8000",
        ]:
            self.assertIn("拒绝打开", tools.open_url(url), url)

        self.assertEqual(backend.opened_url, "")

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

    def test_wait_for_selector_and_page_elements(self):
        backend = FakeBrowserBackend()
        tools = BrowserTools(backend=backend)

        waited = tools.wait_for_selector("#submit", timeout_seconds=3)
        elements = tools.page_elements(max_items=10)
        summary = tools.page_summary(max_text_chars=50, max_elements=10)

        self.assertEqual(waited, "已找到元素: #submit")
        self.assertEqual(backend.waited, [("#submit", 3000)])
        self.assertIn("links:", elements)
        self.assertIn("Example - https://example.com/docs", elements)
        self.assertIn("buttons:", elements)
        self.assertIn("#submit text=Submit", elements)
        self.assertIn("inputs:", elements)
        self.assertIn("#q type=text", elements)
        self.assertIn("title: Demo Page", summary)
        self.assertIn("Hello browser page", summary)

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
        self.assertIn("browser_wait_for_selector", tool_names)
        self.assertIn("browser_page_elements", tool_names)
        self.assertIn("browser_page_summary", tool_names)

    def test_default_registry_requires_confirmation_for_browser_screenshot(self):
        registry = build_default_registry(confirm_action=lambda prompt: False)

        result = registry.call("browser_screenshot", path="screenshots/page.png")

        self.assertEqual(result, "已取消操作。")
        self.assertIn("browser_screenshot: browser/write, 需要确认", registry.describe_permissions())


class FakeBrowserBackend:
    def __init__(self):
        self.opened_url = ""
        self.clicked = []
        self.filled = []
        self.waited = []

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

    def wait_for_selector(self, selector: str, timeout_ms: int) -> None:
        self.waited.append((selector, timeout_ms))

    def page_elements(self, max_items: int):
        return {
            "links": [{"text": "Example", "href": "https://example.com/docs"}],
            "buttons": [{"text": "Submit", "selector": "#submit"}],
            "inputs": [{"selector": "#q", "type": "text", "name": "q", "placeholder": "Search"}],
        }

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake png")


if __name__ == "__main__":
    unittest.main()
