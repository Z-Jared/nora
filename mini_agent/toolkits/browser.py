from pathlib import Path
from typing import Optional, Protocol

from mini_agent.url_safety import is_public_http_url


MAX_PAGE_TEXT_CHARS = 12000
DENIED_SCREENSHOT_NAMES = {".env", ".env.local", ".env.production"}
DENIED_SCREENSHOT_DIRS = {".git", "__pycache__", ".pytest_cache", "data"}


class BrowserBackend(Protocol):
    def open_url(self, url: str) -> None:
        ...

    def page_title(self) -> str:
        ...

    def page_text(self) -> str:
        ...

    def click(self, selector: str) -> None:
        ...

    def fill(self, selector: str, text: str) -> None:
        ...

    def wait_for_selector(self, selector: str, timeout_ms: int) -> None:
        ...

    def page_elements(self, max_items: int) -> dict:
        ...

    def screenshot(self, path: Path) -> None:
        ...


class BrowserTools:
    def __init__(
        self,
        root: Optional[Path] = None,
        backend: Optional[BrowserBackend] = None,
    ):
        self.root = (root or Path.cwd()).resolve()
        self.backend = backend or PlaywrightBrowserBackend()
        self._validate_dns = backend is None

    def open_url(self, url: str) -> str:
        if not is_public_http_url(url, resolve_host=self._validate_dns):
            return "拒绝打开: 只允许公开 HTTP/HTTPS URL。"

        try:
            self.backend.open_url(url)
        except Exception as error:
            return f"打开页面失败: {error}"

        return f"已打开页面: {url}"

    def page_title(self) -> str:
        try:
            title = self.backend.page_title()
        except Exception as error:
            return f"读取页面标题失败: {error}"

        return f"页面标题: {title}"

    def page_text(self, max_chars: int = 4000) -> str:
        max_chars = max(200, min(max_chars, MAX_PAGE_TEXT_CHARS))
        try:
            return self.backend.page_text()[:max_chars].strip()
        except Exception as error:
            return f"读取页面文本失败: {error}"

    def click(self, selector: str) -> str:
        selector = selector.strip()
        if not selector:
            return "请提供 CSS selector。"

        try:
            self.backend.click(selector)
        except Exception as error:
            return f"点击失败: {error}"

        return f"已点击: {selector}"

    def fill(self, selector: str, text: str) -> str:
        selector = selector.strip()
        if not selector:
            return "请提供 CSS selector。"

        try:
            self.backend.fill(selector, text)
        except Exception as error:
            return f"输入失败: {error}"

        return f"已输入文本: {selector}"

    def wait_for_selector(self, selector: str, timeout_seconds: int = 5) -> str:
        selector = selector.strip()
        if not selector:
            return "请提供 CSS selector。"

        timeout_ms = max(1, min(timeout_seconds, 30)) * 1000
        try:
            self.backend.wait_for_selector(selector, timeout_ms)
        except Exception as error:
            return f"等待元素失败: {error}"

        return f"已找到元素: {selector}"

    def page_elements(self, max_items: int = 30) -> str:
        max_items = max(1, min(max_items, 100))
        try:
            elements = self.backend.page_elements(max_items)
        except Exception as error:
            return f"读取页面元素失败: {error}"

        return _format_elements(elements)

    def page_summary(self, max_text_chars: int = 1000, max_elements: int = 20) -> str:
        max_text_chars = max(200, min(max_text_chars, MAX_PAGE_TEXT_CHARS))
        sections = []
        title = self.page_title()
        if title.startswith("页面标题: "):
            sections.append("title: " + title.removeprefix("页面标题: "))
        else:
            sections.append(title)
        text = self.page_text(max_chars=max_text_chars)
        sections.append("text:\n" + text)
        sections.append("elements:\n" + self.page_elements(max_items=max_elements))
        return "\n\n".join(sections)

    def screenshot(self, path: str = "screenshots/browser.png") -> str:
        target = self._resolve_screenshot_path(path)
        if not target:
            return "拒绝截图: 只能保存到项目目录内的非敏感路径。"

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            self.backend.screenshot(target)
        except Exception as error:
            return f"截图失败: {error}"

        return f"已保存截图: {target.relative_to(self.root).as_posix()}"

    def _resolve_screenshot_path(self, path: str) -> Optional[Path]:
        try:
            target = (self.root / path).resolve()
            relative = target.relative_to(self.root)
        except (OSError, ValueError):
            return None

        if target.name in DENIED_SCREENSHOT_NAMES:
            return None

        if any(part in DENIED_SCREENSHOT_DIRS for part in relative.parts):
            return None

        return target


class PlaywrightBrowserBackend:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None

    def open_url(self, url: str) -> None:
        page = self._ensure_page()
        page.goto(url, wait_until="domcontentloaded")

    def page_title(self) -> str:
        return self._ensure_page().title()

    def page_text(self) -> str:
        return self._ensure_page().locator("body").inner_text(timeout=5000)

    def click(self, selector: str) -> None:
        self._ensure_page().click(selector, timeout=5000)

    def fill(self, selector: str, text: str) -> None:
        self._ensure_page().fill(selector, text, timeout=5000)

    def wait_for_selector(self, selector: str, timeout_ms: int) -> None:
        self._ensure_page().wait_for_selector(selector, timeout=timeout_ms)

    def page_elements(self, max_items: int) -> dict:
        page = self._ensure_page()
        return page.evaluate(
            """
            (maxItems) => {
              const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const selectorFor = (el) => {
                if (el.id) return '#' + CSS.escape(el.id);
                const name = el.getAttribute('name');
                if (name) return el.tagName.toLowerCase() + '[name="' + name.replace(/"/g, '\\\\"') + '"]';
                return el.tagName.toLowerCase();
              };
              return {
                links: Array.from(document.querySelectorAll('a[href]')).slice(0, maxItems).map((el) => ({
                  text: clean(el.innerText || el.textContent),
                  href: el.href,
                })),
                buttons: Array.from(document.querySelectorAll('button, input[type=button], input[type=submit], [role=button]')).slice(0, maxItems).map((el) => ({
                  text: clean(el.innerText || el.value || el.getAttribute('aria-label')),
                  selector: selectorFor(el),
                })),
                inputs: Array.from(document.querySelectorAll('input, textarea, select')).slice(0, maxItems).map((el) => ({
                  selector: selectorFor(el),
                  type: el.getAttribute('type') || el.tagName.toLowerCase(),
                  name: el.getAttribute('name') || '',
                  placeholder: el.getAttribute('placeholder') || '',
                })),
              };
            }
            """,
            max_items,
        )

    def screenshot(self, path: Path) -> None:
        self._ensure_page().screenshot(path=str(path), full_page=True)

    def _ensure_page(self):
        if self._page:
            return self._page

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError(
                "Playwright 未安装。先运行: python3 -m pip install playwright && python3 -m playwright install chromium"
            ) from error

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        return self._page


def _format_elements(elements: dict) -> str:
    lines = ["links:"]
    for item in elements.get("links", []):
        lines.append(f"- {_clean(item.get('text'))} - {_clean(item.get('href'))}")
    lines.append("buttons:")
    for item in elements.get("buttons", []):
        text = _clean(item.get("text"))
        selector = _clean(item.get("selector"))
        lines.append(f"- {selector} text={text}")
    lines.append("inputs:")
    for item in elements.get("inputs", []):
        selector = _clean(item.get("selector"))
        input_type = _clean(item.get("type"))
        name = _clean(item.get("name"))
        placeholder = _clean(item.get("placeholder"))
        details = f"{selector} type={input_type}"
        if name:
            details += f" name={name}"
        if placeholder:
            details += f" placeholder={placeholder}"
        lines.append(f"- {details}")
    return "\n".join(lines)


def _clean(value) -> str:
    return " ".join(str(value or "").split())
