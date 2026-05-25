import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 60

    @property
    def is_llm_enabled(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)


def load_settings(
    env_path: Path = Path(".env"),
    environ: Optional[Mapping[str, str]] = None,
) -> LLMSettings:
    env_values = _read_env_file(env_path)
    runtime_env = dict(os.environ if environ is None else environ)

    def get(name: str, default: str = "") -> str:
        return runtime_env.get(name) or env_values.get(name) or default

    provider = get("LLM_PROVIDER", "openai-compatible")

    if provider == "anthropic":
        return LLMSettings(
            provider=provider,
            base_url=get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            api_key=get("ANTHROPIC_API_KEY"),
            model=get("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
            timeout_seconds=int(get("LLM_TIMEOUT_SECONDS", "60")),
        )

    if provider == "gemini":
        return LLMSettings(
            provider=provider,
            base_url=get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
            api_key=get("GEMINI_API_KEY"),
            model=get("GEMINI_MODEL", "gemini-2.5-pro"),
            timeout_seconds=int(get("LLM_TIMEOUT_SECONDS", "60")),
        )

    return LLMSettings(
        provider=provider,
        base_url=get("LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=get("LLM_API_KEY") or get("OPENAI_API_KEY"),
        model=get("LLM_MODEL", "gpt-4.1-mini"),
        timeout_seconds=int(get("LLM_TIMEOUT_SECONDS", "60")),
    )


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = _strip_quotes(value.strip())

    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
