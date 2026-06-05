# CCB Code Review Report

**Task:** TASK-125 + TASK-126
**Worker:** Claude A (runtime), Claude B (evals)
**Status:** APPROVED

---

## Summary

TASK-125 adds a read-only local skill manifest catalog discovery surface (`discover_local_skill_manifests`) that scans project-relative paths for skill manifest files and returns bounded safe metadata. TASK-126 adds 10 deterministic offline eval cases covering this surface. Codex PM removed the registry handler's caller-supplied `project_root` entry point and added test/eval assertions for the root boundary fix.

---

## Review Criteria Assessment

### 1. Read-Only Behavior ✅

`discover_local_skill_manifests` is purely read-only:
- No module loading, no execution, no installation
- Only reads JSON files from disk and parses them using existing `parse_skill_manifest_json`
- Uses `manifest_to_safe_dict` for safe output (redacts secret-like values)
- No state mutation of any kind

**Evidence:**
- `skills.py:772-955` — pure file reading and JSON parsing
- `test_skills.py:1307-1316` — `test_no_durable_task_mutation` verifies no files created/modified
- `run_evals.py:19938-19969` — `eval_local_skill_catalog_read_only` verifies durable task/worker/event counts unchanged

### 2. Registry Root Boundary ✅

The registry handler is strictly bound to `build_default_registry(workspace_root=...)`:

- Handler signature: `_discover_local_skill_manifests_handler(paths, max_files, max_file_bytes)` — no `project_root` parameter
- Handler calls `discover_local_skill_manifests_json(..., project_root=str(root))` where `root` is captured from enclosing scope
- Registry tool schema does not expose `project_root` property
- Caller-supplied `project_root` raises `TypeError` (not silently ignored)

**Evidence:**
- `registry_builder.py:4788-4798` — handler definition, `project_root=str(root)` hardcoded
- `registry_builder.py:4805-4822` — schema definition, no `project_root` property
- `test_skills.py:1288-1303` — `test_registry_tool_rejects_project_root_argument` verifies `TypeError`
- `run_evals.py:19823-19847` — `eval_local_skill_catalog_registry_root_bound` verifies:
  - `project_root` not in registry schema properties
  - Caller-supplied `project_root` raises `TypeError`
  - External directory manifest not discovered when passed as `project_root`

### 3. Path Safety ✅

Comprehensive path validation implemented:

- **Path traversal**: Rejects `../../../etc/passwd` patterns via `os.path.normpath` + prefix check
- **Absolute paths**: Rejects via `os.path.isabs()`
- **Shell metacharacters**: Rejects `` ` $ ; | & < > { } ( ) [ ] ! # ~ `` via regex
- **Secret-like paths**: Rejects paths matching secret patterns
- **Path length**: Capped at 512 characters
- **Hidden files/directories**: `_is_hidden_or_denied()` checks for `.` prefix
- **Denied directories**: `_DENIED_DIRS` includes `.git`, `__pycache__`, `node_modules`, etc.
- **`_has_hidden_or_denied_part`**: Checks all path components for hidden/denied status (PM fix for directly specified directory paths)
- **Resolved path escape**: Verifies `resolved.relative_to(root)` succeeds

**Evidence:**
- `skills.py:719-752` — `_is_safe_relative_path` validation
- `skills.py:755-761` — `_is_hidden_or_denied` check
- `skills.py:764-769` — `_has_hidden_or_denied_part` (checks all path components)
- `skills.py:854-871` — file and directory handling with hidden/denied checks
- `test_skills.py:1187-1217` — path safety tests (traversal, absolute, hidden, denied, non-JSON)
- `run_evals.py:19765-19820` — `eval_local_skill_catalog_path_safety` covers all scenarios

### 4. Bounds and Resource Limits ✅

| Bound | Value | Enforced |
|-------|-------|----------|
| `MAX_DISCOVER_FILES` | 50 | `max_files` clamped to `[1, 50]` |
| `MAX_DISCOVER_FILE_BYTES` | 64 KB | `max_file_bytes` clamped to `[1024, 65536]` |
| `MAX_PATH_LENGTH` | 512 | Path string length check |
| Directory scan depth | 5 | `_scan_directory` depth parameter |
| Input scan | `MAX_DISCOVER_FILES * 2` | `paths[:MAX_DISCOVER_FILES * 2]` |

**Evidence:**
- `skills.py:705-707` — constants
- `skills.py:787-799` — max_files/max_file_bytes clamping with safe fallback
- `skills.py:966-996` — `_scan_directory` with depth limit
- `test_skills.py:1162-1183` — bounds tests (max_files, max_file_size, empty file)
- `run_evals.py:19714-19762` — `eval_local_skill_catalog_bounds` covers all bounds

### 5. Malformed JSON / Invalid Manifest / Secret-Like Values ✅

- Malformed JSON: Returns `invalid_count >= 1` with error message, no crash
- Invalid manifest: Returns `invalid_count >= 1` with validation errors
- Secret-like names/versions: Redacted to `<redacted>` via `_safe_str`
- Secret-like domains/capabilities: Omitted with warning
- Secret-like paths: Rejected with error
- Non-string path entries: Error message, skipped
- Unsupported path argument type: Error message

**Evidence:**
- `test_skills.py:1221-1240` — malformed JSON and invalid manifest tests
- `run_evals.py:19850-19891` — `eval_local_skill_catalog_malformed_input` covers all cases
- `run_evals.py:19894-19935` — `eval_local_skill_catalog_secret_no_leak` verifies no secret leakage

### 6. Eval Determinism and Offline Behavior ✅

All 10 evals are deterministic and offline:
- Use `tempfile.TemporaryDirectory()` for isolated workspace
- Create local manifest files with known content
- No network calls, no live LLM, no external dependencies
- Deterministic sorted order verified

**Evidence:**
- All eval functions use `with tempfile.TemporaryDirectory()` pattern
- `eval_local_skill_catalog_directory_discovery` verifies sorted order: `paths == sorted(paths)`
- No eval depends on external state or timing

### 7. Compatibility ✅

Existing surfaces remain functional:
- `inspect_skill_manifest` — works
- `summarize_skill_manifests` — works
- `preview_skill_context` — works
- `route_capability_request` — works
- `compile_context_pack` — works
- `list_tool_permissions` — works

**Evidence:**
- `test_skills.py:1320-1339` — compatibility tests after discovery
- `run_evals.py:19972-20029` — `eval_local_skill_catalog_compatibility` verifies all surfaces

---

## Findings

### No Blocking Issues

All review criteria are satisfied. No findings requiring changes.

### Notes

1. **PM fix verified**: The hidden/denied directory check for directly specified directory paths is properly implemented via `_has_hidden_or_denied_part()` which checks all path components. This prevents bypassing safety checks by directly specifying a denied directory like `.git/`.

2. **Eval coverage**: 10 eval cases cover tool permission, valid manifest, directory discovery, bounds, path safety, registry root boundary, malformed input, secret no-leak, read-only behavior, and compatibility. This is comprehensive.

3. **Bounded output**: All outputs use `manifest_to_safe_dict` which redacts secret-like values. Error messages are bounded and never echo raw malformed content.

---

## Verification

- `python3 -m unittest tests.test_skills tests.test_mini_agent` → 273 tests OK
- `python3 evals/run_evals.py` → 487 passed, 0 failed
- `git diff --check` → clean
