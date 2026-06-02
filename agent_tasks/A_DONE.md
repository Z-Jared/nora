# Claude A Completion Report — TASK-066: Worker Workspace File Inspection Tools v1

Status: ready for Codex review

## Review Fix (Must Fix #1, #2, #3, #4)

**#1 — `max_files` non-integer input:**
- Wrapped `int(max_files or 50)` in `try/except (ValueError, TypeError)`, returns bounded JSON error `{"error": "max_files 必须是整数"}`.
- Regression test: `test_list_files_bad_max_files_returns_error`

**#2 — `context_lines` non-integer input:**
- Wrapped `int(context_lines or 3)` in `try/except (ValueError, TypeError)`, returns bounded JSON error `{"error": "context_lines 必须是整数"}`.
- Regression test: `test_preview_write_bad_context_lines_returns_error`

**#3 — Symlink escape in `list_worker_workspace_files`:**
- After `target.is_file()`, now calls `target.resolve()` and checks `resolved.relative_to(ws_root)` to ensure the real file target stays inside workspace. Symlinks pointing outside are skipped.
- Also checks `resolved.name` against `DENIED_FILE_NAMES` (in case symlink target is a sensitive filename).
- Regression test: `test_list_files_skips_symlink_escape` — creates a symlink inside workspace pointing outside, verifies it is excluded from listing.

**#4 — Symlink to denied directory (e.g. `.git/config`):**
- Added check on `resolved.relative_to(ws_root).parts` against `DENIED_DIR_NAMES`. Previously only the symlink's own path was checked, so `gitlink -> .git/config` was listed.
- Regression tests: `test_list_files_skips_symlink_to_git_dir` (symlink to `.git/config`), `test_list_files_skips_symlink_to_logs_dir` (symlink to `logs/app.log`).

## Summary

Added three worker-scoped file inspection tools that operate only inside the active workspace lease: `list_worker_workspace_files`, `read_worker_workspace_file`, and `preview_worker_workspace_write`. All tools reuse the existing lease validation and workspace file safety rules (`.env`, `.git`, etc.).

## Changes

### `mini_agent/toolkits/registry_builder.py`

Added `import difflib` at top.

**`_resolve_workspace_path(lease, path)` — shared path resolver:**
- Handles both relative paths (resolved under workspace root) and absolute paths (only allowed if they resolve inside workspace)
- Checks path traversal via `relative_to()`
- Rejects sensitive file names (`DENIED_FILE_NAMES`: `.env`, `.env.local`, `.env.production`)
- Rejects paths containing sensitive directory names (`DENIED_DIR_NAMES`: `.git`, `__pycache__`, `.pytest_cache`, `data`, `logs`)
- Returns `(resolved_path, None)` or `(None, error_dict)`

**`list_worker_workspace_files(worker_id, task_id, max_files=50)`:**
- Lists files recursively under workspace, returning bounded relative paths
- Skips sensitive files and directories
- Skips symlinks whose resolved target escapes workspace
- `max_files` bounded to 1..200; non-integer returns bounded JSON error
- Returns `{"files": [...], "count": N, "workspace_path": ..., "lease_id": ...}`

**`read_worker_workspace_file(worker_id, task_id, path)`:**
- Reads UTF-8 text file content
- Rejects missing files, non-files, oversized files, binary files, sensitive paths
- Returns `{"content": ..., "path": ..., "size": ..., "workspace_path": ..., "lease_id": ...}`

**`preview_worker_workspace_write(worker_id, task_id, path, content, context_lines=3)`:**
- Generates unified diff preview without writing any files
- `context_lines` bounded to 0..20; non-integer returns bounded JSON error
- Returns `{"preview": ..., "path": ..., "current_size": ..., "new_size": ..., "will_create": bool, ...}`

All three tools:
- Registered with `risk="read"` permission
- Reuse `_resolve_and_validate_lease()` for worker/task/lease validation
- Reject offline and idle workers
- Output does not leak task goal, steps, or secrets

### `tests/test_durable_workers.py`
- Added `WorkspaceFileInspectionTests` class with 32 tests:
  - **list** (10): empty workspace, relative paths, skips .env, skips .git dir, max bounded, no lease error, unknown worker error, no goal leak, no mutation, bad max_files error
  - **read** (10): returns content, absolute inside workspace, traversal rejected, absolute escape rejected, missing file error, .env rejected, empty path error, offline worker error, no goal leak, no mutation
  - **preview** (9): new file, existing file (diff), no actual write, traversal rejected, .env rejected, no goal leak, no task mutation, context_lines, bad context_lines error
  - **symlink** (3): symlink escape skipped, symlink to .git/config skipped, symlink to logs skipped

## Verification

```
$ python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 617 tests — OK

$ python3 -m unittest tests.test_workspace tests.test_workspace_extra
Ran 42 tests — OK

$ python3 -m unittest discover -s tests
Ran 1673 tests — OK

$ python3 evals/run_evals.py
228 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/toolkits/registry_builder.py | 189 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 tests/test_durable_workers.py           | 227 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 2 files changed
```

## Notes

- No push or commit performed.
- BACKLOG.md untouched.
- All three tools are read-only (`risk="read"`) — preview never writes files.
- Reuses `DENIED_FILE_NAMES` and `DENIED_DIR_NAMES` from `workspace.py` for consistent safety rules.
- `_resolve_workspace_path` is reusable for future workspace-scoped tools.
