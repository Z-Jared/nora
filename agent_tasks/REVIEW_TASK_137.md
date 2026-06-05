# TASK-137 Review: Minimal model routing inspection scaffold v1

**Status: APPROVED**

## Summary

Claude A implemented a read-only model routing inspection scaffold. Codex PM integrated it and tightened three points before approval:

- `build_agent()` now passes the final `LLMSettings` into `build_default_registry()`, so routing inspection matches the actual model client configuration after `agent.yaml` overrides.
- Unsupported providers return bounded labels (`unsupported_provider`, `unsupported`) without echoing raw provider/model/key strings.
- Fallback provider selection uses stable provider order instead of set iteration.

## Findings

No blocking issues remain.

## Evidence

```text
python3 -m unittest tests.test_model_router tests.test_config tests.test_mini_agent
Ran 178 tests in 8.413s
OK

python3 evals/run_evals.py
537 passed, 0 failed

git diff --check
clean
```

Manual probe:

```text
inspect_model_routing permission: local/read
Injected anthropic settings returned selected_provider=anthropic and selected_model=claude-test without leaking the fake key.
```

## Verdict

Approved for integration. TASK-138 should now add deterministic eval coverage for this surface without changing runtime implementation.
