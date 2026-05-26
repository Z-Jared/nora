import json
import urllib.error
import urllib.request

from mini_agent.memory import is_sensitive_text
from mini_agent.providers.base import LLMError

MAX_ERROR_DETAIL_CHARS = 1000


def post_json(url: str, headers: dict[str, str], payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise LLMError(f"LLM HTTP {error.code}: {sanitize_error_detail(detail)}") from error
    except urllib.error.URLError as error:
        raise LLMError(f"LLM request failed: {error}") from error


def sanitize_error_detail(detail: str) -> str:
    if is_sensitive_text(detail):
        return "[redacted]"
    return detail[:MAX_ERROR_DETAIL_CHARS]
