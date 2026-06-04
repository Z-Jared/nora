# B DONE — TASK-102

## Status: DONE

## What changed

Added 9 deterministic offline eval cases in `evals/run_evals.py` covering `evaluate_runtime_policy_hook`:

| Eval | Coverage |
|------|----------|
| `policy_hook_allow_read` | pre_tool + risk=read → decision=allow, not blocked, no confirmation, safe matched rule |
| `policy_hook_confirm_write` | pre_tool/pre_shell/pre_git + write, before_commit + write → decision=confirm, requires_confirmation=True |
| `policy_hook_block_destructive` | risk=destructive/external_send → decision=block, blocked=True |
| `policy_hook_unknown_hook_error` | Unknown hook → error=unsupported_hook, raw sentinel not echoed |
| `policy_hook_unknown_category_risk` | Unknown category/risk normalize to "unknown" |
| `policy_hook_reason_no_leak` | Raw reason sentinel not in output; reason_present correct |
| `policy_hook_action_redaction` | Secret/path/env-like/workspace-path/shell/long actions redacted; safe labels preserved |
| `policy_hook_read_only_no_mutation` | No durable task/worker/event mutation |
| `policy_hook_compatibility` | list_tool_permissions includes tool; existing tools still work |

### `eval_policy_hook_action_redaction` specifics (PM review fix):
- `DATABASE_URL=postgres://secret-user:secret-pass@localhost/db` → redacted, raw string absent
- `str(Path(tmpdir) / "workspace" / "secret.txt")` → redacted, raw path absent

## Tests run

```
python3 evals/run_evals.py                    → 373 passed, 0 failed
python3 -m unittest ...RuntimePolicyHookEvaluatorTests → 37 tests OK
python3 -m unittest tests.test_durable_workers → 607 tests OK
python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent → 311 tests OK
git diff --check                              → clean
```

## Notes

- No runtime changes needed; TASK-101 implementation is correct.
- Only `evals/run_evals.py` modified.
- No commit/push performed.
