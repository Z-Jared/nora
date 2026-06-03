# Claude A Completion Report — TASK-087: Guarded Worker Lifecycle Run-once v1

Status: ready for Codex review

## Summary

Added `run_worker_lifecycle_once(limit=5, dry_run=True, release_workspace=True)` and Codex PM follow-up fixes.

- Default `dry_run=True` returns planner output and would-execute metadata without mutation.
- `dry_run=False` executes only `finalize_ready_workspace_merge` actions by reusing existing finalize logic.
- Wait actions and dispatch recommendations are skipped; no shell/git/process/project write/workspace write/start-worker behavior.
- Limit validation rejects bool/float/string, defaults `None` to 5, and clamps integer limits to 1..100.
- `release_workspace` must be boolean.
- Codex PM follow-up: registered the tool as `task/write` with confirmation required, and added `failed_count` for non-finalized finalize attempts.

## Diff

```text
 mini_agent/toolkits/registry_builder.py | 91 ++++++++
 tests/test_durable_workers.py           | 293 ++++++++++++++++++++++++++
```

## Tests

```text
python3 -m unittest tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests
Ran 42 tests in 1.590s
OK

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 604 tests in 16.548s
OK

python3 evals/run_evals.py
304 passed, 0 failed

python3 -m unittest discover -s tests
Ran 1963 tests in 126.243s
OK
Warning: failed to load plugin broken.py: bad

python3 - <<'PY'
from evals.run_evals import eval_lifecycle_planner_guard_rails, eval_lifecycle_planner_no_mutation
for fn in [eval_lifecycle_planner_guard_rails, eval_lifecycle_planner_no_mutation]:
    fn()
    print(fn.__name__, "OK")
PY
OK

git diff --check
OK
```

## New / Updated Tests

- `test_dry_run_returns_plan_without_mutation`
- `test_execute_finalizes_ready_closeout`
- `test_execute_multiple_workers`
- `test_wait_actions_skipped`
- `test_dispatch_skipped`
- `test_limit_zero_clamps_to_one`
- `test_limit_101_clamps_to_100`
- `test_limit_true_returns_error`
- `test_limit_float_returns_error`
- `test_limit_string_returns_error`
- `test_permission_requires_confirmation`
- `test_release_workspace_false`
- `test_release_workspace_true`
- `test_bad_release_workspace_returns_error`
- `test_no_goal_leak`
- `test_no_steps_leak`
- `test_no_file_content_leak`

## Notes

- No push performed.
- Codex PM fixed the previous eval regression before marking ready for review.
- Full `python3 -m unittest discover -s tests` was rerun after final report edits and passed.
