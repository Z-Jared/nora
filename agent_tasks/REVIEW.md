# TASK-102 Review — Deterministic eval coverage for runtime policy hook evaluator v1

**Status: APPROVED**

## Review Summary

All 4 review criteria satisfied. The 9 eval cases are concrete, deterministic, isolated, and cover the full TASK-102 requirement surface without runtime changes.

---

## 1. Assertions are concrete and non-vacuous

Every eval verifies specific field values, not just presence:

- **`policy_hook_allow_read`**: Checks `decision=="allow"`, `requires_confirmation is False`, `blocked is False`, `"rule_pre_tool_read" in matched_rules`, `action=="read_file"`, `action_label=="safe"`, `reason_present is False`. 12 assertions.
- **`policy_hook_confirm_write`**: Covers 5 hook+risk combos (pre_tool/write, pre_shell/write, pre_git/write, before_commit/write, pre_tool/high). Each checks `decision=="confirm"`, `requires_confirmation is True`, specific `reason_label`. 15 assertions.
- **`policy_hook_block_destructive`**: Checks destructive→block and external_send→block, `blocked is True`, `requires_confirmation is False`, `reason_label=="high_risk_blocked"`, matched rule present. 10 assertions.
- **`policy_hook_unknown_hook_error`**: Uses sentinel `"UNKNOWN_HOOK_SENTINEL_XYZ_123"`, asserts `error=="unsupported_hook"`, sentinel absent from `json.dumps(result)`, `valid_hooks` non-empty. 4 assertions.
- **`policy_hook_unknown_category_risk`**: Checks `category=="unknown"`, `risk=="unknown"`, `decision in ("allow","confirm","block")`. 3 assertions.
- **`policy_hook_reason_no_leak`**: Uses sentinel `"REASON_SECRET_SENTINEL_ABC_789"`, asserts absent from `json.dumps(result)`, `reason_present is True`. Also tests no-reason→`reason_present is False`. 4 assertions.
- **`policy_hook_action_redaction`**: 8 sub-cases (SECRET_VALUE_XYZ, /etc/passwd, DATABASE_URL=..., workspace path, shell command, long >60, safe label, empty). Each checks `action==""`, `action_label=="redacted"`, raw string absent. Safe label checks `action=="read_file"`, `action_label=="safe"`. 20+ assertions.
- **`policy_hook_read_only_no_mutation`**: Snapshots task/worker/event counts before, calls evaluator 3 times, asserts counts unchanged. 3 assertions.
- **`policy_hook_compatibility`**: Checks `"evaluate_runtime_policy_hook" in perms_str`, existing task CRUD still works. 3 assertions.

No eval only asserts tool existence or event presence. All are field-value specific.

## 2. Eval fixtures are deterministic and isolated

- Every eval uses `tempfile.TemporaryDirectory()` with `NoraDB(Path(tmpdir) / "test.db")`.
- `db.close()` in `finally` blocks.
- No shared state between evals.
- No timing dependencies, no network calls, no external processes.
- PM verification: 373 passed, 0 failed — fully deterministic.

## 3. No raw sentinel leaks in serialized outputs

Leak checks cover:
- **Reason sentinel**: `"REASON_SECRET_SENTINEL_ABC_789"` absent from `json.dumps(result)` ✓
- **Unknown hook sentinel**: `"UNKNOWN_HOOK_SENTINEL_XYZ_123"` absent from `json.dumps(result)` ✓
- **Secret-like action**: `"SECRET_VALUE_XYZ"` absent from `json.dumps(r1)` ✓
- **Path action**: `"/etc/passwd"` absent from `json.dumps(r2)` ✓
- **Env-like action**: `"DATABASE_URL=postgres://secret-user:secret-pass@localhost/db"` absent from `json.dumps(r2b)` ✓
- **Workspace path action**: `str(Path(tmpdir) / "workspace" / "secret.txt")` absent from `json.dumps(r2c)` ✓

All sentinel checks use `json.dumps(result)` on the full output, not just a field — catches leaks in any field.

## 4. No runtime behavior changed

Diff touches only:
- `evals/run_evals.py` — 9 eval functions + 9 case registrations
- `agent_tasks/B_DONE.md` — completion report
- `agent_tasks/PM_INBOX.md` — status entries

No changes to `mini_agent/`, `tests/`, or any runtime code. Eval count 364→373 (9 new). Existing tests unaffected (37 unit tests still pass, 607 worker tests still pass, 311 other tests still pass).

---

## Coverage Matrix vs B_TASK Requirements

| Requirement | Eval | Covered |
|---|---|---|
| Read/pre_tool → allow | `policy_hook_allow_read` | ✓ |
| Write/high → confirm | `policy_hook_confirm_write` | ✓ |
| Destructive/external_send → block | `policy_hook_block_destructive` | ✓ |
| Unknown hook bounded error | `policy_hook_unknown_hook_error` | ✓ |
| Unknown category/risk normalization | `policy_hook_unknown_category_risk` | ✓ |
| Reason no-leak | `policy_hook_reason_no_leak` | ✓ |
| Action redaction (secret/path/env/shell/workspace/long/safe/empty) | `policy_hook_action_redaction` | ✓ |
| Read-only/no mutation | `policy_hook_read_only_no_mutation` | ✓ |
| Compatibility | `policy_hook_compatibility` | ✓ |

All B_TASK requirements covered.
