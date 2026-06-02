# Claude A Completion Report — TASK-070: Worker Workspace Change Summary / Patch Export Tools v1

Status: approved by Codex review

## Summary

Added two read-only tools that compare a worker workspace against the project root and export bounded review metadata/patches: `summarize_worker_workspace_changes` and `export_worker_workspace_patch`. Both tools reuse the existing lease validation, path safety rules, and file size limits.

## Changes

### `mini_agent/toolkits/registry_builder.py`

**`_safe_read_file_content(file_path)` — shared file reader with safety checks:**
- Returns `(content, meta_dict)` where meta_dict contains `exists`, `is_file`, `size`, `text`, `oversized`, `binary`, `read_error` flags.
- Used by both new tools for consistent project-root and worker-file reading.

**Project path / patch budget safety helpers:**
- `_has_denied_workspace_part(...)` rejects sensitive names used anywhere in a path component list.
- `_safe_project_path_for_worker_export(...)` validates both original and resolved project-root paths, including project-root symlinks that resolve into denied paths.
- `_append_worker_patch_if_bounded(...)` enforces per-patch and total patch output limits.

**`summarize_worker_workspace_changes(worker_id, task_id, max_files=50):`**
- Scans worker workspace files recursively, bounded by `max_files` (1..200).
- Compares each safe worker file against the same relative path in project root.
- Returns safe per-file metadata: `path`, `status` (`created`, `modified`, `same`, `skipped`), `reason`, `worker`, and `project`.
- Skips sensitive files/dirs, symlink escapes, project symlink-to-sensitive-file, oversized/binary/non-UTF8/read-error files.
- Does not return raw file content.

**`export_worker_workspace_patch(worker_id, task_id, path="", max_files=50, context_lines=3):`**
- If `path` is provided, exports a bounded unified diff for that single safe file.
- If `path` is empty, exports bounded patches for changed safe files up to `max_files`.
- Created files diff from `/dev/null`; modified files diff against the project-root version; same files are omitted from multi-file export.
- `context_lines` is bounded to 0..20.
- Rejects/skips sensitive paths, path escapes, project symlink-to-sensitive-file, binary/non-UTF8/oversized files, and oversized patch output.

Both tools:
- Registered with `risk="read"` permission.
- Reject offline and idle workers.
- Output does not leak task goal, steps, prompts, shell/env/request strings, or secret sentinels.
- Return safe metadata: lease_id, worker_id, task_id.
- Do not write to project root or mutate worker/task/lease state.

### `tests/test_durable_workers.py`

Added `WorkspaceChangeSummaryTests` class with 48 tests:
- **summary** (26): created file, modified file, same file, skips `.env`/`.env.local`/`.env.production`, skips `.env` as an intermediate directory component, skips `.git`/`logs`/`data` dirs, max_files bounded, bad max_files error, unknown worker, no lease, task mismatch, offline/idle worker, no goal leak, no mutation, safe metadata, project symlink escape, project symlink-to-sensitive-file, oversized project file, worker binary/oversized created files.
- **patch export** (20): created file, modified file, same excluded, single-path no-change, single-path created, max_files bounded, context_lines, bad context_lines error, path traversal rejected, `.env` rejected, `.env` as an intermediate directory component skipped, unknown worker, no lease, offline/idle worker, no goal leak, no mutation, safe metadata, project symlink escape, project symlink-to-sensitive-file, single-file patch size bound, multi-file total patch budget.
- **compatibility** (2): read/list/preview/write still work after summary and patch export, bad max_files error.

## Verification

```
$ python3 -m unittest tests.test_durable_workers
Ran 234 tests — OK

$ python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 401 tests — OK

$ python3 -m unittest discover -s tests
Ran 1760 tests — OK

$ python3 evals/run_evals.py
245 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/toolkits/registry_builder.py | 410 ++++++++++++++++++
 tests/test_durable_workers.py           | 732 ++++++++++++++++++++++++++++++++
 2 files changed, 1142 insertions(+)
```

## Notes

- No push performed.
- Codex PM review fixes tightened sensitive path component rejection, project-root symlink-to-sensitive-file handling, worker binary/oversized summary handling, and patch output budget enforcement.
- Both tools are read-only (`risk="read"`) and do not implement project-root merge/apply behavior.
- Project-root symlink safety uses `Path.resolve()` + `relative_to()` with denied-component checks on both original and resolved paths.
