# Claude B Task

Owner: Claude B
Status: assigned

## Goal

Upgrade the eval harness to measure trace and context compiler behavior.

## Instructions

Implement only eval harness coverage. Do not modify agent runtime behavior unless a test reveals a clear bug and Codex PM approves scope.

Context:

- Existing `evals/run_evals.py` covers many old capabilities.
- New trace and context compiler features need eval coverage so progress is measurable.

Required:

- Add offline eval cases for:
  - context compiler includes git status/changed files and Python outline.
  - context compiler skips `.env`, `data/`, and `logs` paths in explicit inputs and git output.
  - `compile_context_pack` registry tool returns Markdown text, not an object.
  - trace store records a run with status, event counts, and tool call summary.
  - trace output redacts sensitive input/tool previews.
- If Claude A adds trace inspection tools before you finish, add eval coverage for `list_run_traces` and `get_run_trace`.
- Update README eval description to include trace and context compiler coverage.
- Keep evals deterministic and offline by default.

Suggested files:

- `evals/run_evals.py`
- `README.md`
- README only if you add a user-visible tool/CLI command
- `agent_tasks/B_DONE.md`

## Current PM Note

The context compiler and trace store are now code, but Nora needs eval gates to prevent regressions. This is how we move toward Codex/Claude Code-level engineering reliability.

## Completion Report

Update `agent_tasks/B_DONE.md` with:

- Summary of eval cases added.
- Diff stat.
- Exact tests/checks run.
- Any known limitations or eval gaps.
