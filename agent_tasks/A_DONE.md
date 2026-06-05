# TASK-121 Completion Report

## Summary

Added a read-only skill context preview surface. Takes a user goal and a bounded list of skill manifest JSON strings/objects, selects relevant skill manifests using metadata only (name, description, domains, capabilities, workflows, deliverables), and returns safe context hints for downstream context compiler.

## PM Review Fixes

1. **Malformed/non-list JSON error reporting**: `preview_skill_context_json` now appends safe errors (`invalid JSON in skill_manifest_jsons`, `skill_manifest_jsons must be a list`, `skill_manifest_jsons must be a JSON string or list`) to the result instead of silently converting to `[]`.

2. **Input scan cap**: `preview_skill_context` now caps input scanning at 50 entries (`_MAX_INPUT_SCAN`) before `max_skills` selection. Truncated inputs produce a bounded warning. This prevents unbounded error/warning accumulation on large invalid inputs.

3. **`max_skills` safe normalization**: `preview_skill_context` now wraps `max_skills` in `try/except (TypeError, ValueError)` with fallback to 5 and a bounded warning `"invalid max_skills; using default"`. Non-int values no longer raise and the raw bad value is never echoed.

## Files Changed

```
mini_agent/skills.py                    | 270 +++++++++++++++++++++++++
mini_agent/toolkits/registry_builder.py |  37 ++++
tests/test_skills.py                    | 360 ++++++++++++++++++++++++++++++++
3 files changed, 667 insertions(+)
```

## Implementation

### `mini_agent/skills.py`

- `preview_skill_context(goal, skill_manifest_jsons, max_skills)` — pure helper. Extracts goal keywords, scores each skill manifest by keyword overlap against metadata (domains, capabilities, workflows, deliverables, name, description), selects top N, returns bounded context sections with matched_domains, matched_capabilities, workflows, deliverables, required_plugins, risk_boundaries, evals. Includes `untrusted_framing` field for read-only context framing.
- `preview_skill_context_json(goal, skill_manifest_jsons, max_skills)` — JSON-string wrapper for registry tool. Reports safe errors for malformed/non-list JSON instead of silently returning empty.
- `max_skills` clamped to 1-20. Input scan capped at `_MAX_INPUT_SCAN=50` with truncation warning.
- Secret-like values redacted via `_safe_str`. Raw malformed input never echoed.

### `mini_agent/toolkits/registry_builder.py`

- Registered `preview_skill_context` tool with `ToolPermission(category="local", risk="read")`.
- Parameters: `goal` (string, required), `skill_manifest_jsons` (JSON string), `max_skills` (integer, default 5).

## Tests (119 total in test_skills.py)

New test classes:
- `TestPreviewSkillContextValid` — empty goal, none/empty manifests, relevant skill selected, irrelevant skipped, deterministic bounded ordering, max_skills clamp, untrusted framing, goal bounding, aggregate required_plugins/risk_boundaries
- `TestPreviewSkillContextMetadata` — context section fields match manifest
- `TestPreviewSkillContextErrors` — non-list input, malformed JSON, non-string/dict entries, missing required fields, mixed valid/invalid, large invalid input bounded with truncation warning, bad max_skills (string/None/float-string with warning and no-leak)
- `TestPreviewSkillContextSafety` — secret sentinel no-leak for goal, name, version, domains, capabilities, all fields combined, malformed entry
- `TestPreviewSkillContextReadOnly` — no durable task/worker/event mutation via registry
- `TestPreviewSkillContextRegistry` — tool registered, exact permission, registry wrapper honors max_skills, JSON handling, malformed JSON asserts error, non-list JSON asserts error, unsupported type asserts error, bad max_skills with warning and no-leak, empty
- `TestPreviewSkillContextCompatibility` — inspect_skill_manifest, summarize_skill_manifests, route_capability_request still work; preview doesn't affect inspect

## Verification

```
python3 -m unittest tests.test_skills tests.test_context_memory tests.test_mini_agent
Ran 284 tests in 2.341s — OK

python3 evals/run_evals.py
459 passed, 0 failed

git diff --check
(clean)
```

## Notes

- No commit or push performed.
- No edits to `evals/run_evals.py`, `CODEX_TERMINAL_HANDOFF.md`, or `designs/`.
- No durable task/worker/event mutation.
- Existing `inspect_skill_manifest`, `summarize_skill_manifests`, and `route_capability_request` remain functional.
