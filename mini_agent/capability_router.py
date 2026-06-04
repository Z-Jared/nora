"""Minimal read-only capability routing scaffold (TASK-115).

Inspects user goals and declared plugin manifest metadata to return
candidate capabilities, risk level, required confirmations, and
expected deliverables. Does NOT load plugins, execute plugin code,
call external services, or mutate durable state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from mini_agent.plugins import (
    HIGH_RISK_RISKS,
    PluginManifest,
    PluginToolMeta,
    _is_secret_like,
    _safe_str,
    parse_manifest,
    parse_manifest_json,
)


# ---------------------------------------------------------------------------
# Routing result models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CandidatePlugin:
    name: str
    version: str
    matched_domains: tuple[str, ...] = ()
    matched_capabilities: tuple[str, ...] = ()
    risk_level: str = "low"
    requires_confirmation: bool = False
    tool_count: int = 0


@dataclass(frozen=True)
class RoutingResult:
    goal_summary: str = ""
    risk_level: str = "low"
    requires_confirmation: bool = False
    expected_deliverables: tuple[str, ...] = ()
    candidate_plugins: tuple[CandidatePlugin, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Risk inference
# ---------------------------------------------------------------------------

def _infer_risk_level(risk_str: str) -> str:
    """Map a tool risk string to a high/medium/low routing risk level."""
    if risk_str in HIGH_RISK_RISKS:
        return "high"
    if risk_str == "write":
        return "medium"
    return "low"


def _aggregate_risk(levels: list[str]) -> str:
    """Aggregate multiple risk levels into a single level."""
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Keyword extraction / matching
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "and", "but", "or",
    "not", "so", "if", "then", "than", "too", "very", "just", "about",
    "it", "its", "this", "that", "these", "those", "i", "me", "my",
    "we", "our", "you", "your", "he", "him", "his", "she", "her",
    "they", "them", "their", "what", "which", "who", "whom", "how",
    "where", "when", "why", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "nor", "only",
    "own", "same", "also", "too", "up", "out", "off", "over", "under",
})


def _extract_keywords(text: str) -> set[str]:
    """Extract lowercase keywords from text, filtering stop words.

    Also splits on underscores and hyphens to handle compound names.
    """
    words = set()
    for word in text.lower().split():
        # Strip punctuation
        cleaned = "".join(c for c in word if c.isalnum() or c in "-_")
        if not cleaned:
            continue
        # Split on underscores and hyphens for compound words
        parts = cleaned.replace("_", " ").replace("-", " ").split()
        for part in parts:
            if part and len(part) > 1 and part not in _STOP_WORDS:
                words.add(part)
        # Also keep the full cleaned word if it's compound
        if len(parts) > 1:
            words.add(cleaned)
    return words


def _keyword_overlap(a: set[str], b: set[str]) -> set[str]:
    """Return intersection of keyword sets."""
    return a & b


# ---------------------------------------------------------------------------
# Core routing logic
# ---------------------------------------------------------------------------

def route_capability_request(
    goal: str,
    plugin_manifest_jsons: list[str] | None = None,
    max_candidates: int = 5,
) -> dict[str, Any]:
    """Route a capability request against declared plugin manifests.

    Pure read-only: no plugin loading, no execution, no state mutation.
    Returns a bounded safe dict.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # Validate inputs
    if not isinstance(goal, str) or not goal.strip():
        return _build_result(
            goal_summary="",
            risk_level="low",
            requires_confirmation=False,
            expected_deliverables=(),
            candidate_plugins=(),
            warnings=("empty or missing goal",),
            errors=(),
        )

    goal = goal.strip()[:2000]
    goal_keywords = _extract_keywords(goal)

    if not goal_keywords:
        warnings.append("goal contains no meaningful keywords")

    if plugin_manifest_jsons is None:
        plugin_manifest_jsons = []

    if not isinstance(plugin_manifest_jsons, list):
        return _build_result(
            goal_summary=goal[:100],
            risk_level="low",
            requires_confirmation=False,
            expected_deliverables=(),
            candidate_plugins=(),
            warnings=(),
            errors=("plugin_manifest_jsons must be a list",),
        )

    # Clamp max_candidates
    max_candidates = max(1, min(max_candidates, 20))

    # Parse manifests
    parsed_manifests: list[tuple[PluginManifest, list[str], list[str]]] = []
    for i, raw in enumerate(plugin_manifest_jsons):
        if isinstance(raw, str):
            result = parse_manifest_json(raw)
        elif isinstance(raw, dict):
            result = parse_manifest(raw)
        else:
            errors.append(f"manifest[{i}]: must be a JSON string or object")
            continue

        if result.errors:
            for err in result.errors:
                errors.append(f"manifest[{i}]: {err}")
        if result.warnings:
            for warn in result.warnings:
                warnings.append(f"manifest[{i}]: {warn}")

        if result.manifest:
            parsed_manifests.append((result.manifest, list(result.errors), list(result.warnings)))

    # Score and rank candidates
    candidates: list[tuple[float, CandidatePlugin]] = []

    for manifest, man_errors, man_warnings in parsed_manifests:
        if man_errors:
            continue  # Skip invalid manifests

        score, cand = _score_manifest(manifest, goal_keywords)
        if score > 0:
            candidates.append((score, cand))

    # Sort by score descending, then name for determinism
    candidates.sort(key=lambda x: (-x[0], x[1].name))

    # Take top N
    top_candidates = [cand for _, cand in candidates[:max_candidates]]

    # Aggregate risk
    risk_levels = [c.risk_level for c in top_candidates]
    overall_risk = _aggregate_risk(risk_levels)
    overall_requires_confirmation = any(c.requires_confirmation for c in top_candidates)

    # Infer deliverables from goal keywords
    deliverables = _infer_deliverables(goal_keywords, top_candidates)

    # Build goal summary
    goal_summary = goal[:100] + ("..." if len(goal) > 100 else "")

    return _build_result(
        goal_summary=goal_summary,
        risk_level=overall_risk,
        requires_confirmation=overall_requires_confirmation,
        expected_deliverables=tuple(deliverables),
        candidate_plugins=tuple(top_candidates),
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def _score_manifest(
    manifest: PluginManifest,
    goal_keywords: set[str],
) -> tuple[float, CandidatePlugin]:
    """Score a manifest against goal keywords. Returns (score, candidate) or (0, ...)."""
    # Build manifest keyword set
    manifest_keywords: set[str] = set()

    # Add domain keywords
    for d in manifest.domains:
        manifest_keywords.update(_extract_keywords(d))

    # Add capability keywords
    for c in manifest.capabilities:
        manifest_keywords.update(_extract_keywords(c))

    # Add tool names and descriptions
    for tool in manifest.tools:
        manifest_keywords.update(_extract_keywords(tool.name))
        manifest_keywords.update(_extract_keywords(tool.description))

    # Compute overlap
    overlap = _keyword_overlap(goal_keywords, manifest_keywords)
    if not overlap:
        return 0, CandidatePlugin(name=_safe_str(manifest.name), version=_safe_str(manifest.version))

    # Match domains and capabilities
    matched_domains = tuple(sorted(
        d for d in manifest.domains
        if _keyword_overlap(goal_keywords, _extract_keywords(d))
    ))
    matched_capabilities = tuple(sorted(
        c for c in manifest.capabilities
        if _keyword_overlap(goal_keywords, _extract_keywords(c))
    ))

    # Compute risk from tools
    tool_risks = [_infer_risk_level(t.risk) for t in manifest.tools] if manifest.tools else ["low"]
    plugin_risk = _aggregate_risk(tool_risks)
    plugin_requires_confirmation = any(t.requires_confirmation for t in manifest.tools)

    score = len(overlap) + len(matched_domains) * 2 + len(matched_capabilities) * 2

    candidate = CandidatePlugin(
        name=_safe_str(manifest.name),
        version=_safe_str(manifest.version),
        matched_domains=matched_domains,
        matched_capabilities=matched_capabilities,
        risk_level=plugin_risk,
        requires_confirmation=plugin_requires_confirmation,
        tool_count=len(manifest.tools),
    )

    return score, candidate


def _infer_deliverables(
    goal_keywords: set[str],
    candidates: list[CandidatePlugin],
) -> list[str]:
    """Infer expected deliverables from goal keywords and candidate tools."""
    deliverables: list[str] = []

    # Common deliverable patterns
    if goal_keywords & {"code", "implement", "write", "create", "build", "develop", "fix", "refactor"}:
        deliverables.append("code_changes")
    if goal_keywords & {"test", "verify", "validate", "check", "assert"}:
        deliverables.append("test_results")
    if goal_keywords & {"review", "analyze", "audit", "inspect"}:
        deliverables.append("review_report")
    if goal_keywords & {"document", "explain", "describe", "summarize"}:
        deliverables.append("documentation")
    if goal_keywords & {"search", "find", "query", "lookup"}:
        deliverables.append("search_results")
    if goal_keywords & {"deploy", "release", "publish", "ship"}:
        deliverables.append("deployment_artifact")

    if not deliverables and candidates:
        deliverables.append("tool_output")

    return sorted(set(deliverables))


def _build_result(
    goal_summary: str,
    risk_level: str,
    requires_confirmation: bool,
    expected_deliverables: tuple[str, ...],
    candidate_plugins: tuple[CandidatePlugin, ...],
    warnings: tuple[str, ...],
    errors: tuple[str, ...],
) -> dict[str, Any]:
    """Build the final result dict."""
    return {
        "goal_summary": goal_summary,
        "risk_level": risk_level,
        "requires_confirmation": requires_confirmation,
        "expected_deliverables": list(expected_deliverables),
        "candidate_plugins": [
            {
                "name": c.name,
                "version": c.version,
                "matched_domains": list(c.matched_domains),
                "matched_capabilities": list(c.matched_capabilities),
                "risk_level": c.risk_level,
                "requires_confirmation": c.requires_confirmation,
                "tool_count": c.tool_count,
            }
            for c in candidate_plugins
        ],
        "warnings": list(warnings),
        "errors": list(errors),
    }


def route_capability_request_json(goal: str, plugin_manifest_jsons: str = "[]", max_candidates: int = 5) -> str:
    """JSON-string wrapper for registry tool registration."""
    # Parse the outer JSON array
    json_error = False
    try:
        manifests = json.loads(plugin_manifest_jsons) if plugin_manifest_jsons else []
    except (json.JSONDecodeError, TypeError):
        manifests = []
        json_error = True

    if not isinstance(manifests, list):
        manifests = []
        json_error = True

    result = route_capability_request(
        goal=goal,
        plugin_manifest_jsons=manifests,
        max_candidates=max_candidates,
    )

    if json_error:
        errors = list(result.get("errors", []))
        errors.append("plugin_manifest_jsons: invalid JSON or not a list")
        result["errors"] = errors

    return json.dumps(result, ensure_ascii=False)
