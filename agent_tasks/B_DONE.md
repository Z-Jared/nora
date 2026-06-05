# TASK-128: Deterministic eval coverage for context compiler local skill catalog bridge v1

## Summary

Added 10 deterministic offline eval cases for TASK-127 context compiler local skill catalog bridge in `evals/run_evals.py`. PM review fix applied to address 4 blocking findings.

## Changes

**`evals/run_evals.py`** — added 10 eval functions + 10 EvalCase registrations:

1. **`eval_context_compiler_skill_catalog_valid_file`** — direct `ContextCompiler.compile(...)` with valid `skill_manifest_paths` file adds a Skill Context Preview section.
2. **`eval_context_compiler_skill_catalog_directory_discovery`** — directory path discovery contributes multiple local skill manifests in deterministic order.
3. **`eval_context_compiler_skill_catalog_registry`** — registry `compile_context_pack` accepts `skill_manifest_paths` as a JSON string and stays `workspace/read`.
4. **`eval_context_compiler_skill_catalog_combined`** — manual `skill_manifest_jsons` and local `skill_manifest_paths` combine correctly.
5. **`eval_context_compiler_skill_catalog_path_safety`** — traversal, absolute path, hidden directory, denied directory paths are rejected.
6. **`eval_context_compiler_skill_catalog_malformed_input`** — malformed paths JSON, non-list paths input, invalid manifest file are handled gracefully with bounded diagnostic messages; raw input sentinels not echoed.
7. **`eval_context_compiler_skill_catalog_secret_no_leak`** — secret-like manifest fields, raw unsafe path sentinels, raw file content do not leak.
8. **`eval_context_compiler_skill_catalog_read_only`** — durable task, worker, and event counts unchanged during registry compile.
9. **`eval_context_compiler_skill_catalog_registry_root_binding`** — registry `compile_context_pack` ignores caller-supplied `project_root`; only discovers workspace-bound manifests.
10. **`eval_context_compiler_skill_catalog_compatibility`** — existing manual `skill_manifest_jsons`, git status, knowledge excerpts, `discover_local_skill_manifests`, `preview_skill_context`, `list_tool_permissions` still work.

## PM Review Fixes

1. **Malformed input assertions** (lines 20307, 20319): Removed `or True` tautology; now assert specific diagnostic message "skill_manifest_paths must be a JSON list or array of strings" and verify raw input sentinel not echoed.
2. **Git status assertion** (line 20452): Removed `or True` tautology; now asserts "Git Status" or "git" appears in output when `include_git_status=True`.
3. **Read-only eval**: Added worker store count check (`list_workers`) alongside task/event counts.
4. **Registry root binding**: New eval `eval_context_compiler_skill_catalog_registry_root_binding` verifies workspace-bound manifest discovered, external manifest not leaked.

## Verification

```
python3 evals/run_evals.py — 497 passed, 0 failed
python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent — 333 tests OK
git diff — check — clean
```

## Notes

- No runtime behavior changes.
- Only `evals/run_evals.py` modified.
