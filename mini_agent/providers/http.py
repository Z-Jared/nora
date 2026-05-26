import json
import time
import urllib.error
import urllib.request

from mini_agent.memory import is_sensitive_text
from mini_agent.providers.base import LLMError

MAX_ERROR_DETAIL_CHARS = 1000
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0


def post_json(url: str, headers: dict[str, str], payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_STATUS_CODES or attempt >= MAX_RETRIES:
                detail = error.read().decode("utf-8", errors="replace")
                raise LLMError(f"LLM HTTP {error.code}: {sanitize_error_detail(detail)}") from error
            delay = BASE_DELAY_SECONDS * (2 ** attempt)
            retry_after = error.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    pass
            time.sleep(delay)
        except urllib.error.URLError as error:
            last_error = error
            if attempt >= MAX_RETRIES:
                raise LLMError(f"LLM request failed: {error}") from error
            time.sleep(BASE_DELAY_SECONDS * (2 ** attempt))

    raise LLMError(f"LLM request failed after {MAX_RETRIES} retries: {last_error}")


def sanitize_error_detail(detail: str) -> str:
    if is_sensitive_text(detail):
        return "[redacted]"
    return detail[:MAX_ERROR_DETAIL_CHARS]
