"""Skill manifest v1 schema, parser, and inspection helpers (TASK-116).

Provides read-only inspection of skill-pack metadata without loading files,
importing skill modules, executing hooks, or calling external services.

Mirrors the structure of mini_agent.plugins plugin manifest surface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILL_MANIFEST_VERSION = "1"

_SECRET_PATTERNS = (
    "sk-", "secret", "token", "api_key", "password", "credential",
    "bearer", "auth", "key-",
)

MAX_STRING_LENGTH = 200
MAX_LIST_ITEMS = 20
MAX_LIST_ITEM_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    description: str = ""
    domains: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    workflows: tuple[str, ...] = ()
    deliverables: tuple[str, ...] = ()
    required_plugins: tuple[str, ...] = ()
    risk_boundaries: tuple[str, ...] = ()
    evals: tuple[str, ...] = ()


@dataclass
class SkillManifestValidationResult:
    valid: bool
    manifest: Optional[SkillManifest] = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_secret_like(value: str) -> bool:
    """Check if a string looks like a secret/token/key."""
    lower = value.lower()
    return any(pat in lower for pat in _SECRET_PATTERNS)


def _safe_str(value: str) -> str:
    """Redact secret-like string values."""
    if _is_secret_like(value):
        return "<redacted>"
    return value


def _parse_string_list(
    value: Any,
    field_name: str,
    warnings: list[str],
    max_items: int = MAX_LIST_ITEMS,
    max_item_len: int = MAX_LIST_ITEM_LENGTH,
) -> list[str]:
    """Parse an optional list of strings, normalizing and bounding safely."""
    if value is None:
        return []
    if not isinstance(value, list):
        warnings.append(f"{field_name} must be a list")
        return []
    result: list[str] = []
    for item in value[:max_items]:
        if not isinstance(item, str):
            warnings.append(f"{field_name} item must be a string")
            continue
        item_stripped = item.strip()
        if not item_stripped:
            continue
        if _is_secret_like(item_stripped):
            warnings.append(f"{field_name} item looks secret-like, omitted")
            continue
        result.append(item_stripped[:max_item_len])
    return result


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_skill_manifest(data: Any) -> SkillManifestValidationResult:
    """Parse and validate a skill manifest v1 dict.

    Returns a SkillManifestValidationResult with parsed manifest or errors.
    Never raises on malformed input — always returns bounded safe result.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return SkillManifestValidationResult(
            valid=False, errors=("manifest must be a JSON object",),
        )

    # --- Required identity fields ---
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("missing or empty required field: name")
        name = ""
    else:
        name = name.strip()[:MAX_STRING_LENGTH]
        if _is_secret_like(name):
            errors.append("name looks secret-like")
            name = "<redacted>"

    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("missing or empty required field: version")
        version = ""
    else:
        version = version.strip()[:MAX_STRING_LENGTH]
        if _is_secret_like(version):
            errors.append("version looks secret-like")
            version = "<redacted>"

    # --- Optional description ---
    description = data.get("description", "")
    if not isinstance(description, str):
        description = ""
        warnings.append("description must be a string")
    description = description.strip()[:MAX_DESCRIPTION_LENGTH]
    if _is_secret_like(description):
        warnings.append("description looks secret-like, redacted")
        description = "<redacted>"

    # --- Optional list fields ---
    domains = _parse_string_list(data.get("domains"), "domains", warnings)
    capabilities = _parse_string_list(data.get("capabilities"), "capabilities", warnings)
    workflows = _parse_string_list(data.get("workflows"), "workflows", warnings)
    deliverables = _parse_string_list(data.get("deliverables"), "deliverables", warnings)
    required_plugins = _parse_string_list(data.get("required_plugins"), "required_plugins", warnings)
    risk_boundaries = _parse_string_list(data.get("risk_boundaries"), "risk_boundaries", warnings)
    evals = _parse_string_list(data.get("evals"), "evals", warnings)

    # --- Warn on unknown top-level keys ---
    known_keys = {
        "name", "version", "description", "domains", "capabilities",
        "workflows", "deliverables", "required_plugins", "risk_boundaries", "evals",
    }
    unknown_keys = sorted(set(data.keys()) - known_keys)
    for k in unknown_keys:
        if not _is_secret_like(k):
            warnings.append(f"unknown field ignored: {k}")

    if errors:
        return SkillManifestValidationResult(
            valid=False, errors=tuple(errors), warnings=tuple(warnings),
        )

    manifest = SkillManifest(
        name=name,
        version=version,
        description=description,
        domains=tuple(domains),
        capabilities=tuple(capabilities),
        workflows=tuple(workflows),
        deliverables=tuple(deliverables),
        required_plugins=tuple(required_plugins),
        risk_boundaries=tuple(risk_boundaries),
        evals=tuple(evals),
    )
    return SkillManifestValidationResult(
        valid=True, manifest=manifest, warnings=tuple(warnings),
    )


def parse_skill_manifest_json(text: Any) -> SkillManifestValidationResult:
    """Parse a skill manifest from a JSON string.

    Returns bounded safe errors on malformed JSON or non-string input.
    """
    if not isinstance(text, str):
        return SkillManifestValidationResult(
            valid=False, errors=("manifest_json must be a string",),
        )
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return SkillManifestValidationResult(
            valid=False, errors=(f"invalid JSON: {exc}",),
        )
    return parse_skill_manifest(data)


# ---------------------------------------------------------------------------
# Inspection / safe output
# ---------------------------------------------------------------------------

def manifest_to_safe_dict(manifest: SkillManifest) -> dict[str, Any]:
    """Convert a SkillManifest to a safe bounded dict for inspection output.

    Never echoes raw secrets, tokens, API keys, or env-like values.
    """
    return {
        "name": _safe_str(manifest.name),
        "version": _safe_str(manifest.version),
        "description": manifest.description,
        "domains": [_safe_str(d) for d in manifest.domains],
        "capabilities": [_safe_str(c) for c in manifest.capabilities],
        "workflows": [_safe_str(w) for w in manifest.workflows],
        "deliverables": [_safe_str(d) for d in manifest.deliverables],
        "required_plugins": [_safe_str(p) for p in manifest.required_plugins],
        "risk_boundaries": [_safe_str(r) for r in manifest.risk_boundaries],
        "evals": [_safe_str(e) for e in manifest.evals],
    }


def inspect_skill_manifest(data: Any) -> dict[str, Any]:
    """Inspect a skill manifest dict and return bounded safe metadata + validation info."""
    result = parse_skill_manifest(data)
    out: dict[str, Any] = {
        "valid": result.valid,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
    }
    if result.manifest:
        out["manifest"] = manifest_to_safe_dict(result.manifest)
    return out


def inspect_skill_manifest_json(text: Any) -> dict[str, Any]:
    """Inspect a skill manifest from a JSON string. Returns bounded safe result."""
    result = parse_skill_manifest_json(text)
    out: dict[str, Any] = {
        "valid": result.valid,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
    }
    if result.manifest:
        out["manifest"] = manifest_to_safe_dict(result.manifest)
    return out
