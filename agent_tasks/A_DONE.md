# TASK-127: Context compiler local skill catalog bridge v1

## Status: DONE (PM review fixes applied)

## Summary

Bridged TASK-125 local skill manifest discovery into the context compiler. Nora can now compile a task context pack from project-local skill manifest paths without callers first reading manifest files manually.

## PM Review Fixes

### Fix 1: Discovery diagnostics no longer leak raw paths
- Added `_sanitize_discovery_message()` helper at module level in `context_compiler.py` (line 19)
- Maps known discovery messages to coarse reason labels without raw paths
- Applied to all discovery errors/warnings before including in Skill Context Preview
- Examples: `path not found: .git/hidden.json` → `path not found`; `skipped hidden/denied file: .git/x` → `skipped hidden/denied file`

### Fix 2: Malformed JSON string `skill_manifest_paths` returns bounded error
- When `skill_manifest_paths` is a non-empty string that fails JSON parsing or parses to non-list, returns bounded diagnostic section: `Discovery errors: skill_manifest_paths must be a JSON list or array of strings`
- No longer silently ignored; raw input string not echoed

## Changes

### `mini_agent/context_compiler.py`
- Added `import json` for JSON parsing
- Added `_sanitize_discovery_message()` module-level helper (line 19)
- Extended `ContextCompiler.compile()` with `skill_manifest_paths` parameter
- Added `_combine_skill_manifests()` helper with sanitized diagnostics
- Updated `_skill_context_section()` to surface sanitized discovery diagnostics
- Added malformed `skill_manifest_paths` detection with bounded error section

### `mini_agent/toolkits/register_developer.py`
- Added `skill_manifest_paths` parameter to `compile_context_pack` registry schema

### `tests/test_context_compiler.py`
- `ContextCompilerLocalSkillCatalogTests` class with 15 tests covering:
  - Valid manifests, directory discovery, registry integration, combination with manual manifests
  - Path safety: traversal, hidden/denied, missing paths — all sanitized, no raw path leak
  - Malformed JSON string paths: bounded error section, no raw input echo
  - Secret-like values, budget enforcement, compatibility

## Verification

```
python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent → 333 tests OK
python3 evals/run_evals.py → 487 passed, 0 failed
git diff --check → clean
```
