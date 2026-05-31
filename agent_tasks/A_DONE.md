# Claude A Completion Report — TASK-036 Review Fix: Supermemory Metadata Bounding & Container Tag Config

Status: ready for Codex review

## Summary

Fixed CHANGES_REQUESTED review items for TASK-036: bounded metadata in search/profile output, added `SUPERMEMORY_CONTAINER_TAG` env var support, and updated docs.

## Changes

### 1. Metadata bounding (`mini_agent/toolkits/register_supermemory.py`)
- Added `_bound_metadata(meta)` function that sanitizes metadata before returning:
  - Keeps only JSON-safe scalars: `bool`, `int`, `float`, `str`
  - Drops nested dicts, lists, and other non-scalar values
  - Truncates string values to 300 chars (`_METADATA_VALUE_MAX_CHARS`)
  - Limits to 20 fields max (`_METADATA_MAX_FIELDS`)
  - Filters out secret-like keys (`secret`, `token`, `api_key`, `password`, `authorization`, `bearer`)
  - Filters out secret-like values (patterns like `sk-`, `bearer `, `api_key`, `password`, `secret`)
- `_bound_search_output` now calls `_bound_metadata(item["metadata"])` instead of passing raw metadata through

### 2. Container tag configuration (`mini_agent/toolkits/supermemory.py`)
- `from_env()` now reads `SUPERMEMORY_CONTAINER_TAG` env var
- Falls back to the `container_tag` parameter (default `"nora"`) when unset

### 3. Documentation (`docs/knowledge/SUPERMEMORY.md`)
- Added `SUPERMEDIA_CONTAINER_TAG` to config table
- Added production/multi-project recommendation for project-level tags
- Updated tool descriptions to reference "configured container tag" instead of hardcoded "nora"
- Updated privacy boundary section to mention metadata sanitization

### 4. Tests (`tests/test_supermemory.py`)
- Added `MetadataBoundingTests` class with 8 tests:
  - `test_keeps_scalar_strings`, `test_keeps_numbers_and_bools`
  - `test_truncates_long_strings` (value capped at 300 chars)
  - `test_drops_nested_dicts`, `test_drops_lists`
  - `test_limits_field_count` (max 20 fields)
  - `test_empty_metadata`
  - `test_search_output_uses_bounded_metadata` (integration test)
  - `test_drops_secret_like_metadata` (added by linter)
- Added `test_from_env_custom_container_tag` and `test_from_env_default_container_tag` to `SupermemoryClientTests`

## Verification

```
$ python3 -m unittest tests.test_supermemory tests.test_mini_agent tests.test_tool_cache
Ran 171 tests — OK

$ python3 evals/run_evals.py
159 passed, 0 failed

$ git diff --check — OK
```

## Diff

```
 mini_agent/toolkits/supermemory.py          | 101 lines (new)
 mini_agent/toolkits/register_supermemory.py | 193 lines (new)
 tests/test_supermemory.py                   | 388 lines (new)
 docs/knowledge/SUPERMEMORY.md               |  28 lines (new)
 4 files, 710 lines total
```

## Notes

- No push or commit performed.
- No eval changes needed.
- GitHub radar files untouched.
- Linter added `_looks_sensitive_key`/`_looks_sensitive_value` helpers and `test_drops_secret_like_metadata` test — all pass.
