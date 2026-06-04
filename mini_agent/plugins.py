from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from mini_agent.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Manifest v1 constants
# ---------------------------------------------------------------------------

MANIFEST_VERSION = "1"

VALID_AUTH_METHODS = frozenset({
    "none", "oauth", "api_key", "local_token", "enterprise_connector",
})

VALID_PERMISSION_CATEGORIES = frozenset({
    "task", "shell", "git", "file", "network",
    "plugin", "model", "test", "local", "unknown",
})

VALID_RISKS = frozenset({
    "read", "write", "destructive", "external_send", "high", "unknown",
})

VALID_DATA_SENSITIVITY = frozenset({
    "none", "low", "medium", "high", "secret",
})

VALID_EVENT_LOG_MODES = frozenset({
    "none", "metadata_only", "full",
})

HIGH_RISK_RISKS = frozenset({"destructive", "external_send", "high"})


# ---------------------------------------------------------------------------
# Manifest data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginToolMeta:
    name: str
    description: str = ""
    permission_category: str = "unknown"
    risk: str = "unknown"
    requires_confirmation: bool = False
    data_sensitivity: str = "none"
    event_log: str = "metadata_only"


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    description: str = ""
    auth: str = "none"
    domains: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    tools: tuple[PluginToolMeta, ...] = ()


@dataclass
class ManifestValidationResult:
    valid: bool
    manifest: Optional[PluginManifest] = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Parser / Validator
# ---------------------------------------------------------------------------


def parse_manifest(data: dict[str, Any]) -> ManifestValidationResult:
    """Parse and validate a manifest v1 dict.

    Returns a ManifestValidationResult with parsed manifest or errors.
    Never raises on malformed input — always returns bounded safe result.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return ManifestValidationResult(valid=False, errors=("manifest must be a JSON object",))

    # --- Identity ---
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("missing or empty required field: name")
        name = ""
    else:
        name = name.strip()

    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("missing or empty required field: version")
        version = ""
    else:
        version = version.strip()

    description = data.get("description", "")
    if not isinstance(description, str):
        description = ""
    description = description[:500]

    # --- Auth ---
    auth = data.get("auth", "none")
    if not isinstance(auth, str):
        auth = "unknown"
        errors.append("auth must be a string")
    else:
        auth = auth.strip()
        if auth not in VALID_AUTH_METHODS:
            warnings.append("unknown auth method")
            auth = "unknown"

    # --- Optional routing metadata ---
    domains = _parse_string_list(data.get("domains"), "domains", warnings)
    capabilities = _parse_string_list(data.get("capabilities"), "capabilities", warnings)

    # --- Tools ---
    raw_tools = data.get("tools")
    tools: list[PluginToolMeta] = []
    if raw_tools is not None:
        if not isinstance(raw_tools, list):
            errors.append("tools must be a list")
        else:
            seen_names: set[str] = set()
            for i, raw_tool in enumerate(raw_tools):
                tool, tool_errors, tool_warnings = _parse_tool(raw_tool, i)
                errors.extend(tool_errors)
                warnings.extend(tool_warnings)
                if tool is not None:
                    if tool.name in seen_names:
                        errors.append(f"duplicate tool name: {tool.name}")
                    else:
                        seen_names.add(tool.name)
                        tools.append(tool)

    if errors:
        return ManifestValidationResult(valid=False, errors=tuple(errors), warnings=tuple(warnings))

    manifest = PluginManifest(
        name=name,
        version=version,
        description=description,
        auth=auth,
        domains=tuple(domains),
        capabilities=tuple(capabilities),
        tools=tuple(tools),
    )
    return ManifestValidationResult(valid=True, manifest=manifest, warnings=tuple(warnings))


def parse_manifest_json(text: str) -> ManifestValidationResult:
    """Parse manifest from JSON text. Returns bounded safe errors on malformed JSON."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return ManifestValidationResult(valid=False, errors=(f"invalid JSON: {exc}",))
    return parse_manifest(data)


_SECRET_PATTERNS = (
    "sk-", "secret", "token", "api_key", "password", "credential",
    "bearer", "auth", "key-",
)


def _is_secret_like(value: str) -> bool:
    """Check if a string looks like a secret/token/key."""
    lower = value.lower()
    return any(pat in lower for pat in _SECRET_PATTERNS)


def _parse_string_list(value: Any, field_name: str, warnings: list[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        warnings.append(f"{field_name} must be a list")
        return []
    result = []
    for item in value:
        if isinstance(item, str) and item.strip():
            item_stripped = item.strip()[:100]
            if _is_secret_like(item_stripped):
                warnings.append(f"{field_name} item looks secret-like, omitted")
            else:
                result.append(item_stripped)
    return result


def _parse_tool(raw: Any, index: int) -> tuple[Optional[PluginToolMeta], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    prefix = f"tools[{index}]"

    if not isinstance(raw, dict):
        errors.append(f"{prefix}: must be an object")
        return None, errors, warnings

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{prefix}: missing or empty name")
        return None, errors, warnings
    name = name.strip()

    # Use safe label in warnings to avoid echoing secret-like tool names
    safe_name = name if not _is_secret_like(name) else "<redacted>"
    prefix_label = f"{prefix} ({safe_name})"

    description = raw.get("description", "")
    if not isinstance(description, str):
        description = ""
    description = description[:300]

    permission_category = raw.get("permission_category", "unknown")
    if not isinstance(permission_category, str):
        permission_category = "unknown"
        errors.append(f"{prefix_label}: permission_category must be a string")
    else:
        permission_category = permission_category.strip()
        if permission_category not in VALID_PERMISSION_CATEGORIES:
            warnings.append(f"{prefix_label}: unknown permission_category")
            permission_category = "unknown"

    risk = raw.get("risk", "unknown")
    if not isinstance(risk, str):
        risk = "unknown"
        errors.append(f"{prefix_label}: risk must be a string")
    else:
        risk = risk.strip()
        if risk not in VALID_RISKS:
            warnings.append(f"{prefix_label}: unknown risk")
            risk = "unknown"

    requires_confirmation = raw.get("requires_confirmation", False)
    if not isinstance(requires_confirmation, bool):
        requires_confirmation = bool(requires_confirmation)

    data_sensitivity = raw.get("data_sensitivity", "none")
    if not isinstance(data_sensitivity, str):
        data_sensitivity = "none"
        errors.append(f"{prefix_label}: data_sensitivity must be a string")
    else:
        data_sensitivity = data_sensitivity.strip()
        if data_sensitivity not in VALID_DATA_SENSITIVITY:
            warnings.append(f"{prefix_label}: unknown data_sensitivity")
            data_sensitivity = "unknown"

    event_log = raw.get("event_log", "metadata_only")
    if not isinstance(event_log, str):
        event_log = "metadata_only"
        errors.append(f"{prefix_label}: event_log must be a string")
    else:
        event_log = event_log.strip()
        if event_log not in VALID_EVENT_LOG_MODES:
            warnings.append(f"{prefix_label}: unknown event_log mode")
            event_log = "unknown"

    # High-risk tools require confirmation
    if risk in HIGH_RISK_RISKS and not requires_confirmation:
        errors.append(
            f"{prefix_label}: high-risk/external-send/destructive tool must require confirmation"
        )

    if errors:
        return None, errors, warnings

    return PluginToolMeta(
        name=name,
        description=description,
        permission_category=permission_category,
        risk=risk,
        requires_confirmation=requires_confirmation,
        data_sensitivity=data_sensitivity,
        event_log=event_log,
    ), errors, warnings


def _safe_str(value: str) -> str:
    """Redact secret-like string values."""
    if _is_secret_like(value):
        return "<redacted>"
    return value


def manifest_to_safe_dict(manifest: PluginManifest) -> dict[str, Any]:
    """Convert manifest to a safe bounded dict for inspection output.

    Never echoes raw secrets, tokens, API keys, or env-like values.
    """
    tools_out = []
    for t in manifest.tools:
        tools_out.append({
            "name": _safe_str(t.name),
            "description": t.description,
            "permission_category": t.permission_category,
            "risk": t.risk,
            "requires_confirmation": t.requires_confirmation,
            "data_sensitivity": t.data_sensitivity,
            "event_log": t.event_log,
        })
    return {
        "name": manifest.name,
        "version": manifest.version,
        "description": manifest.description,
        "auth": manifest.auth,
        "domains": list(manifest.domains),
        "capabilities": list(manifest.capabilities),
        "tools": tools_out,
    }


def inspect_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Inspect a manifest dict and return bounded safe metadata + validation info."""
    result = parse_manifest(data)
    out: dict[str, Any] = {
        "valid": result.valid,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
    }
    if result.manifest:
        out["manifest"] = manifest_to_safe_dict(result.manifest)
    return out


def inspect_manifest_json(text: str) -> dict[str, Any]:
    """Inspect a manifest JSON string and return bounded safe metadata + validation info."""
    result = parse_manifest_json(text)
    out: dict[str, Any] = {
        "valid": result.valid,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
    }
    if result.manifest:
        out["manifest"] = manifest_to_safe_dict(result.manifest)
    return out


# ---------------------------------------------------------------------------
# Existing plugin loader (preserved)
# ---------------------------------------------------------------------------


def load_plugins(registry: ToolRegistry, plugins_dir: Path) -> list[str]:
    if not plugins_dir.is_dir():
        return []

    loaded = []
    for plugin_path in sorted(plugins_dir.glob("*.py")):
        if plugin_path.name.startswith("_"):
            continue
        try:
            _load_plugin(registry, plugin_path)
            loaded.append(plugin_path.stem)
        except Exception as error:
            print(f"Warning: failed to load plugin {plugin_path.name}: {error}")

    return loaded


def _load_plugin(registry: ToolRegistry, path: Path) -> None:
    spec = importlib.util.spec_from_file_location(f"nora_plugin_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    register_fn = getattr(module, "register", None)
    if not callable(register_fn):
        raise AttributeError(f"plugin {path.name} must export a callable 'register' function")

    register_fn(registry)
