# B Done

## TASK-124: Deterministic eval coverage for skill context preview v1

Status: **completed**

### Summary

Added 9 deterministic offline eval cases for `preview_skill_context` / registry `preview_skill_context` in `evals/run_evals.py`.

### Changes

**`evals/run_evals.py`** — added 9 eval functions + 9 EvalCase registrations:

1. **`eval_skill_context_preview_tool_permission`** — verifies `ToolPermission(category="local", risk="read")`.
2. **`eval_skill_context_preview_valid`** — valid preview: relevant skill selected, bounded context sections, required plugins, risk boundaries, eval hints, untrusted framing, deterministic output.
3. **`eval_skill_context_preview_stable_ordering`** — multiple matching skills have stable ordering by score descending, then name.
4. **`eval_skill_context_preview_max_skills`** — default (5), explicit, high clamp (20), zero/negative/bad clamp.
5. **`eval_skill_context_preview_malformed_input`** — malformed outer JSON, non-list JSON, unsupported input type, invalid individual manifest entries.
6. **`eval_skill_context_preview_large_input`** — input scan cap (50) with truncation warning.
7. **`eval_skill_context_preview_secret_no_leak`** — secret-like goal, name, domains, capabilities, workflows, deliverables, required_plugins, risk_boundaries, evals do not leak raw sentinel values.
8. **`eval_skill_context_preview_read_only`** — durable task, worker, and event counts unchanged.
9. **`eval_skill_context_preview_compatibility`** — `inspect_skill_manifest`, `summarize_skill_manifests`, `route_capability_request`, and `list_tool_permissions` still work.

### Verification

```
python3 evals/run_evals.py           → 477 passed, 0 failed
python3 -m unittest tests.test_skills tests.test_mini_agent → 242 tests OK
git diff --check                     → clean
```

### Notes

- No runtime changes; eval-only.
- No bugs found in TASK-121 implementation.
