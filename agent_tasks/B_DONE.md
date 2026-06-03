# Claude B / Codex PM Completion Report - TASK-090

Status: approved by Codex PM after local takeover

## Summary

Claude B started deterministic eval coverage for `run_worker_lifecycle_once`, but the CCB Claude provider failed with repeated `provider_api_error` after a timeout. Codex PM took over the preserved worker diff and completed the eval task locally.

Added deterministic offline eval coverage for:

- Dry-run ready closeout metadata and no execution mutation.
- Non-dry-run ready closeout finalization.
- Limit handling with multiple ready closeouts.
- Wait actions skipped.
- Dispatch recommendations skipped.
- `release_workspace=True` releases the lease.
- `release_workspace=False` keeps the lease.
- Bad `limit`, `dry_run`, and `release_workspace` validation.
- Stale finalize / failed-count accounting.
- Safety no-leak for goal, steps, file content, reviewer summary, shell/env/request sentinels, workspace paths, and secrets.
- Compatibility with planner, batch finalize, worker/task registry, claim, and dispatch tools.

Codex PM fixes during takeover:

- Allowed approval events during dry-run because `run_worker_lifecycle_once` is intentionally confirmation-gated as `task/write`.
- Updated the lifecycle ready-worker eval helper to use worker-specific file paths, so multiple ready workers produce real merge-apply events.
- Split release-workspace assertions so prior ready workers do not contaminate later cases.

## Diff

```text
 evals/run_evals.py | 270 +++++++++++++++++++++++++++++++-
```

## Tests

```text
python3 - <<'PY'
from evals.run_evals import (
    eval_run_once_dry_run_ready_closeout,
    eval_run_once_non_dry_run_finalizes,
    eval_run_once_limit_and_skips,
    eval_run_once_release_workspace,
    eval_run_once_bad_params,
    eval_run_once_stale_finalize,
    eval_run_once_safety_no_leak,
    eval_run_once_compatibility,
)
for fn in [
    eval_run_once_dry_run_ready_closeout,
    eval_run_once_non_dry_run_finalizes,
    eval_run_once_limit_and_skips,
    eval_run_once_release_workspace,
    eval_run_once_bad_params,
    eval_run_once_stale_finalize,
    eval_run_once_safety_no_leak,
    eval_run_once_compatibility,
]:
    fn()
    print(fn.__name__, "OK")
PY
OK

python3 evals/run_evals.py
312 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 623 tests in 31.747s
OK

python3 -m unittest discover -s tests
Ran 1982 tests in 134.827s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push was performed by Claude B.
- Codex PM completed the work locally because CCB delivery to Claude B failed after provider/API retries.
- Known issue: the CCB Claude provider remained unhealthy during this handoff, so the PM automation is paused.
