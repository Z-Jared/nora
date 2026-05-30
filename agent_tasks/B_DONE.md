# TASK-014 Completion Report — File-Edit Event Eval Coverage

Status: ready for Codex review

## Summary

Claude B reported a stale-worktree blocker: its isolated worktree did not contain TASK-013 runtime and still showed old TASK-012 task content. Codex PM took over TASK-014 in the main worktree to avoid duplicating runtime or adding fallback shims.

Added deterministic offline eval coverage for durable file-edit events in `evals/run_evals.py`.

## Coverage Added

New eval cases:

1. `file_edit_event_success`
   - Exercises registry-wired `write_project_file`.
   - Verifies `FILE_EDIT_STARTED` → `FILE_EDIT_FINISHED`.
   - Checks path, paths list, status, byte metadata, severity, and `task_id is None`.

2. `file_edit_event_patch_metadata`
   - Exercises `apply_project_patch` and `apply_project_multi_patch`.
   - Verifies patch and multi-patch started/finished events.
   - Checks path(s), file_count, and byte metadata.
   - Asserts raw patch text is not persisted.

3. `file_edit_event_blocked_or_cancelled`
   - Exercises denied `.env` write as blocked-only.
   - Exercises direct `WorkspaceFiles` confirmation cancellation as started → blocked.
   - Verifies no finished event is emitted on cancellation.

4. `file_edit_event_error`
   - Simulates `Path.write_text` OSError.
   - Verifies started → error with generic `write_failed` event label.
   - Preserves existing user-visible error return while asserting raw OSError sentinel is not persisted.

5. `file_edit_event_failure_isolation`
   - Uses a broken event store.
   - Verifies write and replace operations still succeed.

Safety assertions cover:

- raw file content
- replacement text
- patch text
- raw OS error text
- reason text
- forbidden payload keys such as `content`, `old_text`, `new_text`, `patch`, `diff`, `reason`, `exception`, `traceback`

## Diff

```text
 evals/run_evals.py | 224 +++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 217 insertions(+), 7 deletions(-)
```

## Tests

```text
python3 evals/run_evals.py
103 passed, 0 failed

python3 -m unittest tests.test_durable_events tests.test_workspace tests.test_workspace_patch
Ran 104 tests — OK

git diff --check
OK
```

## Notes

- No runtime changes were added for TASK-014.
- No fallback imports or shims were added.
- Claude B's stale worktree was not modified.
- No commit or push performed.
