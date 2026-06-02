# Claude B Completion Report — TASK-067

Status: completed (review fix applied)

## Summary

Added 8 deterministic offline eval cases for worker workspace file inspection tools (TASK-066 runtime). Addressed all 4 Must Fix items from Codex review.

Only `evals/run_evals.py` was edited. No runtime bugs discovered.

## Review Fix Items Addressed

1. **Secret sentinel injection** — `_FILE_INSPECT_SENTINEL_SECRET` is now injected into the task goal in `_setup_file_inspect_worker_with_files`, making the no-leak assertions in `safety_no_leak` non-tautological.

2. **Symlink-to-denied-dir eval** — Added `gitlink -> .git/config` and `loglink -> logs/app.log` symlinks. Asserts list skips them, read/preview return errors.

3. **Compatibility uses claim/dispatch** — Replaced manual `prepare_worker_workspace` with actual `claim_durable_task` and `dispatch_durable_tasks` calls, asserting they still work after file inspection success/error.

4. **Oversized/binary file eval** — New `workspace_file_inspection_oversized_binary` eval: creates >64KB file and binary/non-UTF8 file, asserts bounded JSON errors without sentinel leaks.

## Evals Added

1. **workspace_file_inspection_valid_list_read_preview** — Tests valid scoped file inspection: `list_worker_workspace_files` returns bounded relative paths, `read_worker_workspace_file` reads inside lease (relative + absolute paths), `preview_worker_workspace_write` returns diff/preview and does NOT mutate files or task state.

2. **workspace_file_inspection_path_escape_rejected** — Relative traversal (`../../etc/passwd`), absolute path escape (`/etc/passwd`), deep traversal, and empty path are all rejected by read and preview tools.

3. **workspace_file_inspection_missing_lease_worker_mismatch** — Unknown worker, worker with no lease, and task mismatch all return JSON errors for all three tools.

4. **workspace_file_inspection_offline_idle_rejected** — Offline and idle workers with stale `current_task_id` and lease are rejected by all three tools.

5. **workspace_file_inspection_safety_no_leak** — Outputs do not leak goal/step/secret sentinels (secret is now injected into task goal). Listing is bounded and relative. Read output size is bounded. Error outputs also do not leak sentinels.

6. **workspace_file_inspection_oversized_binary** — Oversized (>64KB) and binary/non-UTF8 files return bounded JSON errors without leaking task sentinels.

7. **workspace_file_inspection_symlink_sensitive_paths** — Symlinks escaping workspace are skipped in listing and rejected on read. Sensitive files (`.env`) and dirs (`.git`) are rejected. Symlinks to denied dirs (`gitlink -> .git/config`, `loglink -> logs/app.log`) are skipped in listing and rejected on read/preview.

8. **workspace_file_inspection_compatibility** — File inspection and preview do not mutate task/worker/lease/event state. Error calls don't break existing tools. `claim_durable_task` and `dispatch_durable_tasks` still work after file inspection.

## Diff

```
 evals/run_evals.py | 519 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 519 insertions(+)
```

## Verification

```
python3 evals/run_evals.py
236 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 314 tests in 5.987s — OK

git diff --check
(clean)
```

## Notes

- No runtime code changed — eval only.
- No commit or push performed.
