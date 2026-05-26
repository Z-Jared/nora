import tempfile
import unittest
from pathlib import Path

from mini_agent.toolkits.browser import BrowserTools, _format_elements, _clean


class ErrorBackend:
    def open_url(self, url):
        raise RuntimeError("browser crashed")

    def page_title(self):
        raise RuntimeError("no page")

    def page_text(self):
        raise RuntimeError("no page")

    def click(self, selector):
        raise RuntimeError("element not found")

    def fill(self, selector, text):
        raise RuntimeError("input not found")

    def wait_for_selector(self, selector, timeout_ms):
        raise RuntimeError("timeout")

    def page_elements(self, max_items):
        raise RuntimeError("no page")

    def screenshot(self, path):
        raise RuntimeError("screenshot failed")


class BrowserErrorHandlingTests(unittest.TestCase):
    def test_open_url_handles_backend_error(self):
        tools = BrowserTools(backend=ErrorBackend())

        result = tools.open_url("https://example.com")

        self.assertIn("打开页面失败", result)

    def test_page_title_handles_backend_error(self):
        tools = BrowserTools(backend=ErrorBackend())

        result = tools.page_title()

        self.assertIn("读取页面标题失败", result)

    def test_page_text_handles_backend_error(self):
        tools = BrowserTools(backend=ErrorBackend())

        result = tools.page_text()

        self.assertIn("读取页面文本失败", result)

    def test_click_handles_backend_error(self):
        tools = BrowserTools(backend=ErrorBackend())

        result = tools.click("#btn")

        self.assertIn("点击失败", result)

    def test_fill_handles_backend_error(self):
        tools = BrowserTools(backend=ErrorBackend())

        result = tools.fill("#input", "text")

        self.assertIn("输入失败", result)

    def test_wait_for_selector_handles_backend_error(self):
        tools = BrowserTools(backend=ErrorBackend())

        result = tools.wait_for_selector("#el")

        self.assertIn("等待元素失败", result)

    def test_page_elements_handles_backend_error(self):
        tools = BrowserTools(backend=ErrorBackend())

        result = tools.page_elements()

        self.assertIn("读取页面元素失败", result)

    def test_screenshot_handles_backend_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = BrowserTools(root=Path(tmpdir), backend=ErrorBackend())

            result = tools.screenshot("test.png")

            self.assertIn("截图失败", result)

    def test_screenshot_rejects_sensitive_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = BrowserTools(root=Path(tmpdir), backend=ErrorBackend())

            result = tools.screenshot(".env")

            self.assertIn("拒绝截图", result)

    def test_screenshot_rejects_sensitive_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = BrowserTools(root=Path(tmpdir), backend=ErrorBackend())

            result = tools.screenshot(".git/shot.png")

            self.assertIn("拒绝截图", result)


class FormatElementsTests(unittest.TestCase):
    def test_formats_empty_elements(self):
        result = _format_elements({"links": [], "buttons": [], "inputs": []})

        self.assertIn("links:", result)
        self.assertIn("buttons:", result)
        self.assertIn("inputs:", result)

    def test_formats_elements_with_data(self):
        elements = {
            "links": [{"text": "Home", "href": "/"}],
            "buttons": [{"text": "OK", "selector": "#ok"}],
            "inputs": [{"selector": "#q", "type": "text", "name": "q", "placeholder": "Search"}],
        }

        result = _format_elements(elements)

        self.assertIn("Home", result)
        self.assertIn("OK", result)
        self.assertIn("#q", result)


class CleanTests(unittest.TestCase):
    def test_strips_whitespace(self):
        self.assertEqual(_clean("  hello  "), "hello")

    def test_collapses_whitespace(self):
        self.assertEqual(_clean("hello  world"), "hello world")

    def test_handles_empty(self):
        self.assertEqual(_clean(""), "")

    def test_handles_non_string(self):
        self.assertEqual(_clean(None), "")


class PageTextTruncationTests(unittest.TestCase):
    def test_page_text_truncated(self):
        class LongTextBackend:
            def open_url(self, url): pass
            def page_title(self): return "T"
            def page_text(self): return "x" * 10000
            def click(self, s): pass
            def fill(self, s, t): pass
            def wait_for_selector(self, s, ms): pass
            def page_elements(self, m): return {}
            def screenshot(self, p): pass

        tools = BrowserTools(backend=LongTextBackend())

        result = tools.page_text(max_chars=300)

        self.assertLessEqual(len(result), 300)


class WaitSelectorEdgeCasesTests(unittest.TestCase):
    def test_wait_empty_selector(self):
        tools = BrowserTools(backend=None)

        result = tools.wait_for_selector("")

        self.assertIn("请提供 CSS selector", result)


if __name__ == "__main__":
    unittest.main()
