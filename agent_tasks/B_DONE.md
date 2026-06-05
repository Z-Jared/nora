# Claude B Done

## TASK-122: Deterministic eval coverage for skill manifest catalog summary v1

**Status:** completed
**Date:** 2026-06-04

### Summary

Added 9 deterministic offline eval cases for `summarize_skill_manifests` in `evals/run_evals.py`, covering:

1. **Tool registration and exact permission** — `ToolPermission(category="local", risk="read")`
2. **Valid catalog summary** — `valid_count`, bounded `skills`, sorted/deduplicated `domains`/`capabilities`/`workflows`/`deliverables`/`required_plugins`/`risk_boundaries`/`evals`; deterministic output
3. **Bounds** — default `max_skills=20`, explicit `max_skills=2`, high value (999) clamps to 50, zero/negative clamp to 1
4. **Malformed input** — malformed outer JSON, malformed individual manifest, non-list input (string and int); all return bounded safe errors
5. **Secret no-leak** — secret-like `name`/`version` produce invalid manifest without leaking raw values; secret-like list items (`domains`, `capabilities`, `required_plugins`) are omitted with warnings; safe values preserved
6. **Read-only** — durable task, worker, and event counts unchanged after `summarize_skill_manifests` call
7. **Compatibility** — `inspect_skill_manifest`, `route_capability_request`, and `list_tool_permissions` still work alongside the new tool

### Files Changed

- `evals/run_evals.py` — added 9 new eval functions (`eval_skill_manifest_catalog_*`) and helper `_make_skill_manifest()`; registered in `cases` list

### PM Review Fix

Fixed `eval_skill_manifest_catalog_bounds` high-clamp test: now uses 60 valid manifests and asserts `valid_count == 50` and `len(skills) == 50` when `max_skills=999`, proving the upper clamp actually works. Previously only tested with 5 manifests which couldn't distinguish clamping from processing all inputs.

### Verification (post-fix)

```bash
python3 evals/run_evals.py
# 468 passed, 0 failed

python3 -m unittest tests.test_skills tests.test_mini_agent
# 200 tests OK

git diff --check
# clean
```

### Notes

- No runtime changes required; `summarize_skill_manifests` already implements correct behavior including `max_skills` clamping and secret-like filtering.
- No conflicts with Claude A's work.
