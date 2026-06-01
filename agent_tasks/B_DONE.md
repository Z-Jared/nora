# Claude B Completion Report — TASK-065

Status: ready for Codex review

## Summary

Added 7 deterministic offline eval cases for worker workspace sandbox guard (TASK-064 runtime). Addressed REVIEW.md Must Fix #2.

### Eval Cases

1. **sandbox_guard_valid_path_passes** — `get_worker_workspace` returns lease info (lease_id, worker_id, task_id, workspace_path). `validate_worker_workspace_path` accepts absolute paths within the workspace directory and the workspace root itself.

2. **sandbox_guard_path_traversal_rejected** — Paths with `../` that escape the workspace are rejected with `"path 不在 workspace 内"` error. Deep traversal (`subdir/../../../etc/shadow`) is also rejected. Traversal that stays within workspace (`subdir/../other/file.txt`) passes.

3. **sandbox_guard_absolute_escape_rejected** — Absolute paths outside the workspace (`/etc/passwd`, tmpdir root) are rejected with `"path 不在 workspace 内"` error.

4. **sandbox_guard_no_lease_errors** — Unknown worker → error. Worker with no lease → `"无 workspace lease"` error. Task mismatch → error. Empty path → `"path 不能为空"` error.

5. **sandbox_guard_offline_idle_rejected** — Offline worker with stale `current_task_id` and lease → rejected by both `get_worker_workspace` and `validate_worker_workspace_path` with `"离线"` error. Idle worker with stale `current_task_id` and lease → rejected with `"空闲"` error.

6. **sandbox_guard_safety_no_leak** — `get_worker_workspace` and `validate_worker_workspace_path` outputs (both valid and error paths) do not leak goal, steps, or secret sentinels. No forbidden keys in output.

7. **sandbox_guard_error_does_not_break_other_tools** — After sandbox guard errors, `list_workers`, `get_worker`, `list_durable_tasks`, `get_durable_task`, and `claim_durable_task` all still work correctly. Post-claim validation uses absolute workspace path with strict `valid is True` assertion.

### Review Fix (Must Fix #2)

- Replaced loose `val_parsed.get("valid") is True or "error" in val_parsed` assertion with strict `val_parsed.get("valid") is True` using an absolute path inside the claimed workspace.
- Added `sandbox_guard_offline_idle_rejected` eval covering offline and idle worker rejection paths.

## Diff

```text
 evals/run_evals.py | 377 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 371 insertions(+), 6 deletions(-)
```

## Tests

```text
python3 evals/run_evals.py
228 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 585 tests in 13.330s — OK

git diff --check
OK
```

## Notes

- TASK-064 runtime fix (offline/idle rejection) was already in place.
- Only `evals/run_evals.py` was edited.
- No runtime bugs discovered.
- No commit or push performed.
