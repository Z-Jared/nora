# Claude B Completion Report - TASK-020 (review fix)

Status: completed, ready for Codex review

## Summary

Added deterministic offline eval coverage for durable approval event logging (TASK-019).

Four eval cases in `evals/run_evals.py`:

1. **approval_event_approved** — Initializes a real Git repo with staged changes, then exercises `git_commit_staged` with `confirm_action=lambda _: True`. Asserts `已创建本地提交` in result (proves tool actually succeeds, not just "not cancelled"). Injects secret sentinel into message argument. Verifies APPROVAL_REQUESTED + APPROVAL_DECIDED events with status="approved", severity="info". Asserts secret sentinel, reason sentinel, and full message are absent from serialized approval events.

2. **approval_event_denied** — Exercises `git_commit_staged` with `confirm_action=lambda _: False`. Verifies APPROVAL_REQUESTED + APPROVAL_DECIDED events with status="denied", severity="warning", and cancellation result `已取消操作。`. Asserts sentinel strings absent from serialized events.

3. **approval_event_non_permissioned** — Exercises `calculate` (read-only, no confirmation). Verifies no APPROVAL_REQUESTED or APPROVAL_DECIDED events are emitted.

4. **approval_event_failure_isolation** — Uses a real permissioned tool (`git_commit_staged`) for all four cases: approved+broken store, denied+broken store, approved+no store, denied+no store. Asserts approved path actually succeeds (`已创建本地提交`) and denied path still cancels. No `calculate` fallback.

## Review Fixes Applied

- ✅ `eval_approval_event_approved`: now initializes Git repo, stages changes, asserts `已创建本地提交` (not just "not cancelled")
- ✅ `eval_approval_event_failure_isolation`: now uses `git_commit_staged` for approved cases instead of `calculate`
- ✅ `_APPROVAL_SENTINEL_SECRET`: now injected into message argument and asserted absent from serialized events

## Safety Assertions

- Sentinel strings: message content, reason text, secret-like token (injected into commit message), full message string
- All sentinels verified absent from: event.payload, event.summary, event.to_dict() serialized JSON
- Forbidden payload keys: args, arguments, message, reason, prompt, raw_args, content, secret, command, password, api_key

## Diff

```text
 evals/run_evals.py | 200 +++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 200 insertions(+), 1 deletion(-)
```

## Tests

```text
python3 evals/run_evals.py
117 passed, 0 failed

python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent
Ran 247 tests in 6.409s
OK

git diff --check
(clean)
```

## Notes

- No runtime code changed — eval only as instructed.
- TASK-019 implementation was already complete and approved.
- No commit or push performed.
- Known limitations: none.
