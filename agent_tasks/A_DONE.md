# Claude A Completion Report — TASK-072: Worker Workspace Review Gate Artifact v1

Status: approved by Codex review

## Summary

Added two review gate tools that record and retrieve auditable review decisions for worker workspace output: `record_worker_workspace_review_gate` and `get_worker_workspace_review_gate`. Both tools reuse existing lease validation and store review gates as durable events.

## Changes

### `mini_agent/toolkits/registry_builder.py`

**`record_worker_workspace_review_gate(worker_id, task_id, decision, reviewer, summary, checks_passed, patch_exported):`**
- Validates lease via `_resolve_and_validate_lease`.
- `decision` must be one of `approved`, `changes_requested`, `blocked`.
- Records a `REVIEW_GATE_FINISHED` durable event with safe payload: worker_id, task_id, lease_id, decision, reviewer, checks_passed, patch_exported, summary_present, summary_length.
- Sanitizes reviewer labels and bounds long reviewer text before returning or storing it.
- Does not store raw summary body; only `summary_present` and `summary_length`.
- Returns safe metadata: recorded, event_id, decision, reviewer, summary_present, summary_length, checks_passed, patch_exported, lease_id, worker_id, task_id, created_at.
- Event failure returns bounded JSON error and does not mutate worker/task/lease state.

**`get_worker_workspace_review_gate(worker_id, task_id):`**
- Validates lease.
- Queries latest `REVIEW_GATE_FINISHED` durable event filtered by task_id and worker_id.
- Returns latest safe gate metadata, or `has_gate: false` if none exists.
- Query failure returns bounded JSON error.
- Does not leak task goal, steps, raw reviewer text, or raw summary content.

Both tools:
- Registered with appropriate permissions (`risk="write"` for record, `risk="read"` for get).
- Reject offline and idle workers.
- Output does not leak task goal, steps, reviewer secrets, summary body, or secret sentinels.
- Do not perform project-root merge, patch apply, commit, or push behavior.

### `tests/test_durable_workers.py`

Added `WorkspaceReviewGateTests` class with 27 tests:
- **record** (17): approved gate metadata, changes_requested accepted, blocked accepted, custom reviewer/summary, sensitive reviewer redaction in record/get/event, summary length metadata, checks_passed/patch_exported flags, unknown decision rejected, unknown worker, no lease, task mismatch, offline/idle worker, no goal leak, no summary body leak, no event payload leak, event failure bounded error/no mutation, normal record no mutation.
- **get** (8): no gate before record, returns latest after multiple records, unknown worker, no lease, offline/idle worker, no goal leak, query failure bounded error.
- **compatibility** (2): existing read/list/preview/write/summary/patch tools still work after gate.

## Verification

```
$ python3 -m unittest tests.test_durable_workers
Ran 261 tests — OK

$ python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 593 tests — OK

$ python3 -m unittest discover -s tests
Ran 1787 tests — OK

$ python3 evals/run_evals.py
260 passed, 0 failed

$ git diff --check
clean
```

## Diff

```
 mini_agent/toolkits/registry_builder.py | 143 ++++++++++-
 tests/test_durable_workers.py           | 440 ++++++++++++++++++++++++++++++++
 2 files changed, 582 insertions(+), 1 deletion(-)
```

## Notes

- No push performed.
- Review gates are stored as `REVIEW_GATE_FINISHED` durable events; no separate store was added.
- Codex PM review fixes added reviewer sanitization plus event/query failure safety coverage.
- Raw reviewer summary is never persisted; only `summary_present` and `summary_length` are recorded.
- `get_worker_workspace_review_gate` returns the latest gate via `list_events(max_results=1)`.
