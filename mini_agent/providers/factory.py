from typing import Optional

from mini_agent.providers.anthropic import AnthropicClient
from mini_agent.providers.gemini import GeminiClient
from mini_agent.providers.openai_compatible import OpenAICompatibleClient
from mini_agent.settings import LLMSettings


def build_llm_client(settings: LLMSettings):
    if not settings.is_llm_enabled:
        return None

    if settings.provider == "openai-compatible":
        return OpenAICompatibleClient(
            base_url=settings.base_url,
            api_key=settings.api_key,
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
        )

    if settings.provider == "anthropic":
        return AnthropicClient(
            base_url=settings.base_url,
            api_key=settings.api_key,
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
        )

    if settings.provider == "gemini":
        return GeminiClient(
            base_url=settings.base_url,
            api_key=settings.api_key,
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.provider}")
