# Claude B Completion Report - TASK-022 (review fix)

Status: completed, ready for Codex review

## Summary

Added deterministic offline eval coverage for durable review-gate event logging (TASK-021).

Five new eval cases added to `evals/run_evals.py`:

1. **review_gate_event_no_diff** — Exercises `review_staged_diff` in an initialized Git repo with no staged changes. Verifies REVIEW_GATE_STARTED + REVIEW_GATE_FINISHED(no_diff) events with has_staged_diff=False, file_count=0.

2. **review_gate_event_present_diff** — Writes sentinel diff content into staged README.md. Verifies REVIEW_GATE_STARTED + REVIEW_GATE_FINISHED events with has_staged_diff=True, file_count>=1. User-visible review output includes the staged file name. Asserts sentinel diff content is NOT in serialized events.

3. **review_gate_event_sensitive_path** — Stages `.env` (denied file) using `git add -f`. Verifies REVIEW_GATE_BLOCKED is emitted with sensitive_path_count>=1. Asserts raw `.env` path name and secret sentinel are NOT in serialized events.

4. **review_gate_event_git_error** — Patches `GitTools._run` to return `Git 命令失败: <sentinel>`. Verifies REVIEW_GATE_ERROR is emitted with error_label="git_command_failure". Asserts raw sentinel error text is NOT in serialized events.

5. **review_gate_event_failure_isolation** — Verifies broken/null event store does not change `review_staged_diff` behavior: no-diff and present-diff paths both work correctly.

## Review Fixes Applied

- ✅ `eval_review_gate_event_present_diff`: now writes `_REVIEW_GATE_SENTINEL_DIFF` into staged README.md content, then asserts it is absent from serialized review-gate events

## Safety Assertions

- Sentinel strings used for: diff content, secret-like token (injected into .env), raw Git error text
- All sentinels verified absent from: event.payload, event.summary, event.to_dict() serialized JSON
- Forbidden payload keys checked: diff, patch, path, paths, files, stdout, stderr, command, args, error, exception, traceback, output

## Diff

```text
 evals/run_evals.py | 217 +++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 217 insertions(+), 1 deletion(-)
```

## Tests

```text
python3 evals/run_evals.py
122 passed, 0 failed

python3 -m unittest tests.test_durable_events tests.test_git_tools tests.test_cli
Ran 170 tests in 6.722s
OK

git diff --check
(clean)
```

## Notes

- No runtime code changed — eval only as instructed.
- TASK-021 implementation was already complete and approved.
- No commit or push performed.
- Known limitations: none.
