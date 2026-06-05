# TASK-121 Review — Skill context preview surface v1

**Status: APPROVED**

## Summary

Read-only skill context preview surface that selects relevant skills by keyword overlap against manifest metadata and returns bounded context hints. All three PM-identified blockers properly fixed.

## Implementation Quality

### Read-Only / No Mutation ✅
- Pure function `preview_skill_context` — no skill loading, no execution, no state mutation
- `_preview_skill_context_json` wrapper handles JSON parsing safely
- Registry tool registered with `ToolPermission(category="local", risk="read")`
- `TestPreviewSkillContextReadOnly.test_no_mutation_via_registry` verifies durable task/worker/event counts unchanged

### Keyword Extraction & Scoring ✅
- `_extract_keywords` normalizes to lowercase, strips punctuation, splits on `_`/`-`, filters stop words
- `_score_skill_for_preview` computes overlap between goal keywords and manifest metadata (domains, capabilities, workflows, deliverables, name, description)
- Deterministic sorting: `(-score, skill_name)`
- Score formula: `len(overlap) + len(matched_domains) * 2 + len(matched_capabilities) * 2`

### Bounded Output ✅
- Goal bounded to 2000 chars, summary to 100 chars
- `max_skills` clamped to `[1, 20]` (constant `MAX_SKILLS_PREVIEW = 20`)
- Input scan capped at `_MAX_INPUT_SCAN = 50` entries
- Secret-like values redacted via `_safe_str` on all output fields
- `untrusted_framing` clearly marks output as read-only metadata hints

## PM Review Fixes (3 blockers)

### 1. Malformed/non-list JSON error reporting ✅
- `preview_skill_context_json` now detects non-list parsed result and appends safe error
- Non-string/non-list input returns bounded error
- Test: `test_registry_wrapper_non_list_json`, `test_registry_wrapper_unsupported_type`

### 2. Input scan cap ✅
- Input capped at `_MAX_INPUT_SCAN = 50` before `max_skills` selection
- Truncation produces bounded warning: `"input truncated to 50 entries"`
- Test: `test_large_invalid_input_bounded` — 200 invalid manifests, errors/warnings bounded ≤ 60

### 3. `max_skills` safe normalization ✅
- `try/except (TypeError, ValueError)` wraps `int(max_skills)`
- Fallback to default 5 with warning `"invalid max_skills; using default"`
- Raw bad value never echoed (test asserts sentinel absent)
- Tests: `test_bad_max_skills_string`, `test_bad_max_skills_none`, `test_bad_max_skills_float_string`

## Test Coverage

119 tests in `test_skills.py` across 7 new test classes:
- `TestPreviewSkillContextValid` (11 tests) — empty goal, none/empty manifests, relevant/irrelevant selection, deterministic bounded ordering, max_skills clamp, untrusted framing, goal bounding, aggregate plugins/risk_boundaries
- `TestPreviewSkillContextMetadata` (1 test) — context section fields match manifest
- `TestPreviewSkillContextErrors` (8 tests) — non-list, malformed JSON, non-string/dict, missing fields, mixed valid/invalid, large input bounded, bad max_skills (string/None/float-string)
- `TestPreviewSkillContextSafety` (7 tests) — sentinel no-leak for goal, name, version, domains, capabilities, all fields combined, malformed entry
- `TestPreviewSkillContextReadOnly` (1 test) — no durable mutation via registry
- `TestPreviewSkillContextRegistry` (9 tests) — tool registered, exact permission, max_skills honored, JSON handling, malformed/non-list/unsupported type, bad max_skills with warning, empty
- `TestPreviewSkillContextCompatibility` (4 tests) — inspect, summarize, route_capability still work; preview doesn't affect inspect

Total: 284 tests pass.

## Compatibility

- `inspect_skill_manifest` still functional ✅
- `summarize_skill_manifests` still functional ✅
- `route_capability_request` still functional ✅
- `preview_skill_context` does not affect `inspect_skill_manifest` results ✅

## Files Changed

- `mini_agent/skills.py` — +270 lines (preview functions, keyword extraction, scoring, untrusted framing)
- `mini_agent/toolkits/registry_builder.py` — +37 lines (registry tool registration)
- `tests/test_skills.py` — +360 lines (119 tests across 7 new classes)

## Verdict

Clean read-only implementation with proper safety, bounded output, and comprehensive test coverage. All PM blockers fixed. APPROVED.
