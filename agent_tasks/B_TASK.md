# Claude B Task

Owner: Claude B
Status: assigned

## Goal

TASK-022: eval coverage for durable review-gate event logging.

## Instructions

TASK-021 is complete and approved. Add deterministic offline eval coverage for durable review-gate events in `evals/run_evals.py`.

Add eval cases for:

1. No staged diff:
   - Exercise `git_review_staged_diff` in an initialized Git repo with no staged changes.
   - Verify review-gate started + finished/no_diff events are recorded.

2. Present staged diff:
   - Stage a deterministic change.
   - Verify started + finished events are recorded with safe metadata and user-visible review output still includes the staged file.

3. Sensitive staged path:
   - Stage a denied/sensitive path such as `.env` using `git add -f`.
   - Verify `REVIEW_GATE_BLOCKED` is emitted with only counts/generic metadata and no raw sensitive path names.

4. Git command error:
   - Deterministically patch the Git command path to return `Git 命令失败: <sentinel>` or `Git 命令超时。`.
   - Verify `REVIEW_GATE_ERROR` is emitted with a generic `error_label`.

5. Safety assertions:
   - Use sentinels that would fail the eval if raw diff content, file paths, sensitive path names, Git command strings, stdout/stderr, raw error text, or secret-like values are persisted in durable event payloads, summaries, or serialized records.
   - Check forbidden payload keys such as `diff`, `patch`, `path`, `paths`, `files`, `stdout`, `stderr`, `command`, `args`, `error`, `exception`, and `traceback`.

6. Failure isolation:
   - Broken/null event store should not change `review_staged_diff` behavior.

Keep evals offline and deterministic. Do not call live LLM APIs and do not reimplement TASK-021 runtime behavior in eval-only code. If you find a real runtime bug while writing evals, stop and report it in `agent_tasks/B_DONE.md` instead of silently changing runtime code.

Suggested verification:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_durable_events tests.test_git_tools tests.test_cli
git diff --check
```

## Context

- TASK-021 added `REVIEW_GATE_STARTED`, `REVIEW_GATE_FINISHED`, `REVIEW_GATE_BLOCKED`, and `REVIEW_GATE_ERROR`.
- Runtime tests already cover review-gate durable events in `tests/test_durable_events.py`.
- `evals/run_evals.py` already has durable event lifecycle, tool-call, model-call, file-edit, shell-command, test-run, and approval event evals.
- Keep this task eval-only. Runtime changes belong to TASK-021 and should not be duplicated here.

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.

Do not commit or push.
