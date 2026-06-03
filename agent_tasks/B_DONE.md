# Claude B Completion Report - TASK-086

Status: approved by Codex PM

## Summary

Added deterministic offline eval coverage for `finalize_ready_worker_workspace_merges`.

Coverage added:
- **Ready path**: finalize one and multiple ready workers; task marked completed, worker marked idle with cleared current_task_id; correct processed/finalized_count/results fields.
- **Guard rails**: limit counts ready candidates not raw not-ready candidates; 100 not-ready + 1 ready still found with limit=1; no candidates and no-ready-candidates paths return zero; bad limit returns bounded error; bad release_workspace returns bounded error.
- **Safety/no-leak**: goal/secret/step/file sentinels not leaked in output, error output, or event payloads.
- **No mutation**: project root and workspace not mutated; rejection paths don't mutate state.
- **Compatibility**: closeout candidate query, single-task finalize, audit query, worker/task registry, claim, and dispatch tools all work after batch finalize.

Codex PM review fix applied:
- Added explicit eval assertions for idempotent repeated calls.
- Added explicit `release_workspace=False` lease retention coverage.
- Made the file-content sentinel part of the actual workspace file input.

## Diff

```text
 evals/run_evals.py | 278 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 278 insertions(+)
```

## Verification

```text
python3 evals/run_evals.py
298 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 580 tests in 17.440s
OK

python3 -m unittest discover -s tests
Ran 1939 tests in 126.401s
OK
Warning: failed to load plugin broken.py: bad

git diff --check
OK
```

## Notes

- No push performed.
- No runtime changes were needed for TASK-086.
- Critical regression covered: 100 raw not-ready candidates before 1 ready candidate — the ready worker is still finalized because limit counts ready candidates, not raw workers scanned.
