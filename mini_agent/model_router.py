"""Minimal model routing inspection scaffold.

Read-only, deterministic model routing explanation layer. It returns safe
metadata about what model Nora would use and why, without changing live model
execution behavior.
"""

from __future__ import annotations

import json as _json
from typing import Any, Optional

from mini_agent.settings import LLMSettings


POLICY_VERSION = "v1"

SUPPORTED_PROVIDER_ORDER = ("openai-compatible", "anthropic", "gemini")
SUPPORTED_PROVIDERS = frozenset(SUPPORTED_PROVIDER_ORDER)

PROVIDER_CAPABILITIES: dict[str, dict[str, Any]] = {
    "openai-compatible": {
        "supports_tools": True,
        "supports_vision": True,
        "max_context_hint": "large",
    },
    "anthropic": {
        "supports_tools": True,
        "supports_vision": True,
        "max_context_hint": "large",
    },
    "gemini": {
        "supports_tools": True,
        "supports_vision": True,
        "max_context_hint": "large",
    },
}

TASK_TYPE_NORMALIZE: dict[str, str] = {
    "code": "code_generation",
    "coding": "code_generation",
    "generate": "code_generation",
    "review": "code_review",
    "test": "testing",
    "debug": "debugging",
    "fix": "debugging",
    "research": "research",
    "search": "research",
    "explain": "explanation",
    "document": "documentation",
    "docs": "documentation",
    "plan": "planning",
    "design": "planning",
    "chat": "general",
    "general": "general",
}

RISK_LEVELS = frozenset({"low", "medium", "high", "critical"})


def _normalize_task_type(task_type: str) -> str:
    if not task_type:
        return "general"
    key = task_type.strip().lower()
    return TASK_TYPE_NORMALIZE.get(key, "general")


def _normalize_risk_level(risk_level: str) -> str:
    if not risk_level:
        return "low"
    key = risk_level.strip().lower()
    return key if key in RISK_LEVELS else "low"


def _determine_route_type(
    task_type: str,
    risk_level: str,
    context_tokens: int,
    requires_tools: bool,
    requires_review: bool,
) -> str:
    if risk_level in ("high", "critical"):
        return "high_risk"
    if requires_review:
        return "review_required"
    if context_tokens > 100_000:
        return "long_context"
    if requires_tools:
        return "tool_use"
    return "standard"


def _select_fallback(settings: LLMSettings) -> tuple[bool, Optional[str]]:
    for provider in SUPPORTED_PROVIDER_ORDER:
        if provider != settings.provider:
            return True, provider
    return False, None


def inspect_model_routing(
    settings: LLMSettings,
    task_type: str = "",
    risk_level: str = "",
    context_tokens: int = 0,
    requires_tools: bool = False,
    requires_review: bool = False,
) -> dict[str, Any]:
    """Inspect what model Nora would use and why, without executing anything."""
    warnings: list[str] = []
    errors: list[str] = []

    if not isinstance(settings, LLMSettings):
        return _build_error_result(["invalid_settings"])

    if not isinstance(context_tokens, int) or context_tokens < 0:
        context_tokens = 0
        warnings.append("invalid_context_tokens_defaulted")

    raw_provider = settings.provider or ""
    provider_supported = raw_provider in SUPPORTED_PROVIDERS
    selected_provider = raw_provider if provider_supported else "unsupported"
    selected_model = settings.model if provider_supported else ""
    is_enabled = settings.is_llm_enabled and provider_supported

    norm_task_type = _normalize_task_type(task_type)
    norm_risk_level = _normalize_risk_level(risk_level)
    route_type = _determine_route_type(
        norm_task_type,
        norm_risk_level,
        context_tokens,
        requires_tools,
        requires_review,
    )

    capabilities = PROVIDER_CAPABILITIES.get(raw_provider, {
        "supports_tools": False,
        "supports_vision": False,
        "max_context_hint": "unknown",
    }).copy()
    capabilities["provider_known"] = provider_supported

    reason_labels: list[str] = []
    if not provider_supported:
        reason_labels.append("unsupported_provider")
    elif is_enabled:
        reason_labels.append("provider_configured")
    else:
        reason_labels.append("provider_disabled")
    if norm_task_type != "general":
        reason_labels.append(f"task_type:{norm_task_type}")
    if norm_risk_level != "low":
        reason_labels.append(f"risk_level:{norm_risk_level}")
    if requires_tools:
        reason_labels.append("requires_tools")
    if requires_review:
        reason_labels.append("requires_review")
    if context_tokens > 100_000:
        reason_labels.append("long_context")

    if not provider_supported:
        warnings.append("unsupported_provider")
        errors.append("unsupported_provider")
    if provider_supported and not settings.is_llm_enabled:
        warnings.append("provider_disabled_or_not_fully_configured")
    if provider_supported and not settings.model:
        warnings.append("no_model_configured")

    fallback_available, fallback_provider = _select_fallback(settings)

    return {
        "selected_provider": selected_provider,
        "selected_model": selected_model,
        "route_type": route_type,
        "policy_version": POLICY_VERSION,
        "task_type": norm_task_type,
        "risk_level": norm_risk_level,
        "reason_labels": reason_labels,
        "capabilities": capabilities,
        "fallback_available": fallback_available,
        "fallback_provider": fallback_provider,
        "warnings": warnings,
        "errors": errors,
        "is_llm_enabled": is_enabled,
    }


def _build_error_result(errors: list[str]) -> dict[str, Any]:
    return {
        "selected_provider": "",
        "selected_model": "",
        "route_type": "error",
        "policy_version": POLICY_VERSION,
        "task_type": "general",
        "risk_level": "low",
        "reason_labels": ["error"],
        "capabilities": {},
        "fallback_available": False,
        "fallback_provider": None,
        "warnings": [],
        "errors": errors,
        "is_llm_enabled": False,
    }


def inspect_model_routing_json(**kwargs: Any) -> str:
    result = inspect_model_routing(**kwargs)
    return _json.dumps(result, ensure_ascii=False, indent=2)
