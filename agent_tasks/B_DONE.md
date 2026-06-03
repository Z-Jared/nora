# Claude B Completion Report - TASK-088

Status: ready for Codex review

## Summary

Added deterministic offline eval coverage for `plan_worker_lifecycle_actions`, with Codex PM follow-up fixes.

Coverage added:
- **Ready path**: ready closeout produces `finalize_ready_workspace_merge` action with correct worker_id/task_id; idle worker + pending task produces `dispatch_pending_task` with correct counts; mixed state returns all expected action types.
- **Guard rails**: empty state returns no actions and zero summary counts; limit clamps returned actions but does not hide ready closeout behind wait actions; 100 not-ready + 1 ready: limit=1 still finds the ready one; bad limit returns bounded error.
- **Safety/no-leak**: goal/secret/step/file sentinels not leaked in output, error output, or action payloads; `.workspaces` path fragment not leaked.
- **No mutation**: task status, worker status/current_task_id, lease, project root, and workspace all unchanged after planner call.
- **Compatibility**: closeout candidate query, batch finalize, single-task finalize, worker/task registry, claim, and dispatch tools all work after planner call.
- Codex PM follow-up: isolated the 100 not-ready + 1 old ready regression from earlier ready fixtures, and fixed event-store snapshot calls to use the current `max_results` API.

## Diff

```text
 evals/run_evals.py | 230 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 230 insertions(+)
```

## Verification

```text
python3 - <<'PY'
from evals.run_evals import eval_lifecycle_planner_guard_rails, eval_lifecycle_planner_no_mutation
for fn in [eval_lifecycle_planner_guard_rails, eval_lifecycle_planner_no_mutation]:
    fn()
    print(fn.__name__, "OK")
PY
OK

python3 evals/run_evals.py
304 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 604 tests in 16.548s
OK

python3 -m unittest discover -s tests
Ran 1963 tests in 126.243s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push performed.
- No runtime changes were needed for TASK-088 beyond PM review fixes in eval assertions.
- Critical regression covered: 100 raw not-ready candidates before 1 ready candidate — the ready closeout is still recommended because the planner iterates workers (limit=500 scan), not a flat candidate list.
- Full `python3 -m unittest discover -s tests` was rerun after final report edits and passed.
