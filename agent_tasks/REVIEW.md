# CCB Review — TASK-123/TASK-124: Skill context compiler preview bridge

**Status: APPROVED**

## Findings

No blocking findings remain.

PM review found one consistency gap before approval: the compiler bridge initially called `preview_skill_context(...)` directly, so it only naturally supported list input, while the registry-facing skill surfaces also support JSON string input. PM fixed this by switching the bridge to `preview_skill_context_json(...)`, updating the schema to accept array or string, and adding JSON-string/malformed-outer-JSON compiler tests.

## Scope Reviewed

- `mini_agent/context_compiler.py`
- `mini_agent/toolkits/register_developer.py`
- `tests/test_context_compiler.py`
- `evals/run_evals.py`
- `agent_tasks/A_DONE.md`
- `agent_tasks/B_DONE.md`
- `agent_tasks/A_TASK.md`
- `agent_tasks/B_TASK.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PM_INBOX.md`

## Review Notes

TASK-123 bridges TASK-121's read-only `preview_skill_context` metadata preview into `ContextCompiler` and registry `compile_context_pack`.

The implementation:

- preserves existing context compiler behavior when no skill manifests are supplied
- adds an explicit `Skill Context Preview [skill manifest metadata]` section only when skill metadata is provided
- marks the section as untrusted/read-only metadata, not executable instructions
- reuses existing skill preview parsing/safety logic instead of duplicating parser behavior
- supports JSON string or list manifest input
- keeps the section on the normal context budget/truncation path
- avoids skill loading, skill installation, plugin execution, external calls, and durable state mutation

TASK-124 adds deterministic offline eval coverage for the existing `preview_skill_context` surface:

- exact `ToolPermission(category="local", risk="read")`
- valid preview shape, selected skills, required plugins, risk boundaries, eval hints, and untrusted framing
- stable ordering and `max_skills` bounds
- malformed input and large input safety
- secret no-leak across goal and manifest fields
- durable task/worker/event read-only behavior
- compatibility with inspect, summarize, route, and permission listing surfaces

## Verification

```text
python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent
Ran 287 tests in 11.503s — OK

python3 -m unittest tests.test_skills tests.test_mini_agent
Ran 242 tests in 2.559s — OK

python3 evals/run_evals.py
477 passed, 0 failed

git diff --check
clean
```

## Decision

Approved for local integration. TASK-123 and TASK-124 complete the skill context preview bridge and deterministic preview eval slice.
