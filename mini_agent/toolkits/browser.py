from pathlib import Path
from typing import Optional, Protocol
import urllib.parse


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

    def open_url(self, url: str) -> str:
        if not _is_allowed_url(url):
            return "拒绝打开: 只允许 HTTP/HTTPS URL。"

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


def _is_allowed_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
