# Claude B Task

Owner: Claude B
Status: assigned

## Goal

Add eval coverage for the durable task CLI inspection tools (once Claude A implements them).

## Instructions

The durable task shadow write evals are done (71 passing). Next:

1. Wait for Claude A to add `list_durable_tasks` tool and `/tasks` CLI command.
2. Add eval cases for:
   - `list_durable_tasks` returns correct task count and fields
   - Task status transitions (pending → running → completed) are captured
   - CLI `/tasks` output format is readable and correct
3. Keep evals deterministic and offline.

## Context

- `evals/run_evals.py` currently has 71 passing evals
- Durable task shadow write evals were added in commit `dbdb7c2`
- If Claude A's tools are not yet available, focus on adding eval cases for any other gaps you find

## Completion Report

Update `agent_tasks/B_DONE.md` with summary, diff stat, tests run, and known limitations.
