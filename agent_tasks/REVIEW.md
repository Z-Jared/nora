# CCB Review — TASK-125/TASK-126: Local skill manifest catalog discovery

**Status: APPROVED**

## Findings

No blocking findings remain.

PM review found and fixed two safety gaps before approval:

- Direct file paths under hidden or denied parent directories could bypass the recursive scanner's skip logic. PM added parent-part validation for direct files and directories.
- Registry callers could supply `project_root` as an extra argument even though it was not advertised in the schema. PM bound registry discovery to `build_default_registry(workspace_root=...)`, removed `project_root` from exposed parameters, and added a root-binding eval.

## Scope Reviewed

- `mini_agent/skills.py`
- `mini_agent/toolkits/registry_builder.py`
- `tests/test_skills.py`
- `evals/run_evals.py`
- `agent_tasks/A_DONE.md`
- `agent_tasks/B_DONE.md`
- `agent_tasks/A_TASK.md`
- `agent_tasks/B_TASK.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PM_INBOX.md`

## Review Notes

TASK-125 adds `discover_local_skill_manifests` as a bounded, read-only workspace catalog surface for local skill manifest metadata.

The implementation:

- accepts project-relative file and directory paths
- rejects traversal, absolute paths, unsafe path characters, and secret-like paths
- skips hidden or denied directories, including direct paths and parent path parts
- scans directories in stable sorted order with caps on file count, recursion depth, and file size
- reuses existing skill manifest parsing and safe output logic
- returns only bounded safe metadata and aggregate catalog fields
- does not load, install, import, or execute skill contents
- does not mutate durable task, worker, event, memory, or trace state
- registers as `ToolPermission(category="workspace", risk="read")`
- keeps existing inspect, summarize, preview, route, context compiler, and permission listing behavior compatible

TASK-126 adds deterministic offline eval coverage for the same surface:

- exact registry permission
- valid manifest discovery
- deterministic directory discovery
- bounds and non-JSON behavior
- traversal, absolute, hidden, denied, and root-binding path safety
- malformed input handling
- secret no-leak
- durable store read-only behavior
- compatibility with existing skill and context surfaces

## Verification

```text
python3 -m unittest tests.test_skills tests.test_mini_agent
Ran 273 tests in 6.345s
OK

python3 evals/run_evals.py
487 passed, 0 failed

git diff --check
OK
```

## Decision

Approved for local integration. TASK-125 and TASK-126 complete the local skill manifest discovery slice and its deterministic eval coverage.
