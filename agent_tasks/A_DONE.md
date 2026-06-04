# Claude A Completion Report

Status: ready for Codex review

## Summary

Implemented `describe_runtime_policy_hook_rules` read-only registry tool (TASK-109), with catalog metadata corrected to match `_evaluate_policy_hook_core` actual priority order.

## Implementation Details

**Registry tool** (`mini_agent/toolkits/registry_builder.py`):
- Added `_describe_runtime_policy_hook_rules_json()` function
- Returns static catalog with no parameters (fully read-only)
- Registered with `ToolPermission(category="local", risk="read")`

**Rules catalog (priority-corrected):**
- `rule_deny_destructive_external` — blocks destructive/external_send across all hooks (highest priority)
- `rule_high_risk_confirm` — confirms high risk across all hooks (catches high before specific hook rules)
- `rule_pre_shell_write` — confirms write only (high caught by rule_high_risk_confirm first)
- `rule_pre_git_write` — confirms write only (high caught by rule_high_risk_confirm first)
- `rule_before_commit_write` — confirms write only (high/destructive caught by higher-priority rules first)
- `rule_pre_tool_write` — confirms write
- `rule_pre_tool_read` — allows read
- `rule_read_allow` — allows read across all hooks
- `rule_write_confirm` — confirms generic write
- `rule_default_allow` — allows unknown risk fallback

## Tests

**New test class** (`tests/test_durable_workers.py`):
- `DescribeRuntimePolicyHookRulesTests` with 34 tests covering:
  - Output shape (policy_version, hooks, categories, risks, decisions, rules list)
  - All 10 known rules with correct properties
  - All rules have required fields and unique IDs
  - No-leak: no raw actions, reasons, paths, env vars, shell commands, request headers
  - Evaluator alignment: catalog rules match actual evaluator `matched_rules` for key scenarios
  - Read-only: no event creation, no task mutation
  - Compatibility: all existing tools still work

## Diff

```text
 agent_tasks/A_DONE.md                   |  79 +++++----
 agent_tasks/PM_INBOX.md                 |   5 +
 mini_agent/toolkits/registry_builder.py | 124 ++++++++++++++
 tests/test_durable_workers.py           | 288 ++++++++++++++++++++++++++++++++
 4 files changed, 468 insertions(+), 28 deletions(-)
```

## Test Results

```text
python3 -m unittest tests.test_durable_workers
Ran 737 tests in 12.235s — OK

python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent
Ran 311 tests in 8.091s — OK

python3 evals/run_evals.py
406 passed, 0 failed

git diff --check
(clean)
```

## PM Review Fix (v2)

Fixed catalog metadata to match `_evaluate_policy_hook_core` actual priority order:
- `rule_pre_shell_write`, `rule_pre_git_write`, `rule_before_commit_write`: removed "high" and "destructive" from `risks` since those are caught by higher-priority rules first
- Added evaluator alignment tests verifying catalog matches actual `matched_rules` for key scenarios
- Enhanced no-leak tests with path/env/shell/request sentinel checks
