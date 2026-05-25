import json
import urllib.error
import urllib.request

from mini_agent.providers.base import LLMError


def post_json(url: str, headers: dict[str, str], payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise LLMError(f"LLM HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise LLMError(f"LLM request failed: {error}") from error
