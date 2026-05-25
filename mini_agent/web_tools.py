import html
import re
import urllib.parse
import urllib.request


MAX_WEB_CHARS = 12000


class WebTools:
    def __init__(self, fetcher=None, timeout_seconds: int = 15):
        self.fetcher = fetcher or _fetch_url
        self.timeout_seconds = timeout_seconds

    def fetch_url(self, url: str, max_chars: int = MAX_WEB_CHARS) -> str:
        if not _is_allowed_url(url):
            return "拒绝访问: 只允许 HTTP/HTTPS URL。"

        max_chars = max(200, min(max_chars, MAX_WEB_CHARS))
        try:
            raw = self.fetcher(url, self.timeout_seconds)
        except Exception as error:
            return f"网页读取失败: {error}"

        return _html_to_text(raw)[:max_chars].strip()

    def web_search(self, query: str, max_results: int = 5) -> str:
        query = query.strip()
        if not query:
            return "请提供搜索关键词。"

        max_results = max(1, min(max_results, 10))
        url = "https://duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        try:
            raw = self.fetcher(url, self.timeout_seconds)
        except Exception as error:
            return f"网页搜索失败: {error}"

        results = _extract_duckduckgo_results(raw, max_results)
        if not results:
            return "没有找到搜索结果。"

        return "\n".join(f"{title} - {link}" for title, link in results)


def _fetch_url(url: str, timeout: int) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Nora/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/" not in content_type and "html" not in content_type and "json" not in content_type:
            raise ValueError(f"unsupported content type: {content_type}")

        data = response.read(MAX_WEB_CHARS * 4)
        return data.decode("utf-8", errors="replace")


def _is_allowed_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _html_to_text(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _extract_duckduckgo_results(text: str, max_results: int) -> list[tuple[str, str]]:
    pattern = re.compile(r'<a[^>]+class=["\']result__a["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    matches = pattern.findall(text)
    results = []
    for href, title in matches:
        clean_title = _html_to_text(title)
        clean_href = html.unescape(href)
        parsed = urllib.parse.urlparse(clean_href)
        query = urllib.parse.parse_qs(parsed.query)
        if "uddg" in query:
            clean_href = query["uddg"][0]
        results.append((clean_title, clean_href))
        if len(results) >= max_results:
            break
    return results
