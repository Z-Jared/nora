# TASK-138: Minimal model routing deterministic eval coverage

**Status:** Complete

## Summary

Added 21 deterministic offline eval cases for the minimal model routing inspection scaffold (`inspect_model_routing`) in `evals/run_evals.py`.

## Changes

- `evals/run_evals.py`: Added 21 eval functions + `LLMSettings` import
  - `eval_model_routing_default_openai` — Configured OpenAI-compatible settings select correct provider/model with policy/version and reason labels; no API key leak
  - `eval_model_routing_anthropic` — Anthropic settings produce safe metadata; no key leak
  - `eval_model_routing_gemini` — Gemini settings produce safe metadata; no key leak
  - `eval_model_routing_unsupported_provider` — Unknown provider returns bounded result; no raw provider/model/key leak
  - `eval_model_routing_missing_api_key` — Missing API key produces disabled route, no crash
  - `eval_model_routing_task_type_hint` — Task type normalized, deterministic reason label
  - `eval_model_routing_risk_level_hint` — High-risk hint adds reason label and route type
  - `eval_model_routing_long_context_hint` — Context tokens >100k produces long_context route
  - `eval_model_routing_tool_and_review_hints` — Tool/review hints produce correct route types
  - `eval_model_routing_invalid_context_tokens_bounded` — Negative tokens bounded with warning
  - `eval_model_routing_no_raw_prompt_leak` — No raw prompt/task content echoed
  - `eval_model_routing_capabilities_present` — Capabilities dict includes expected fields
  - `eval_model_routing_registry_tool_permission` — Registered with `local/read` permission
  - `eval_model_routing_registry_no_mutation` — No mutation of tasks/workers/events
  - `eval_model_routing_registry_with_settings` — Uses injected settings; no key leak
  - `eval_model_routing_registry_no_settings` — Without settings returns safe error
  - `eval_model_routing_registry_with_hints` — Passes hints correctly
  - `eval_model_routing_provider_factory_compatibility` — Existing provider factory intact
  - `eval_model_routing_unknown_task_type_defaults` — Unknown task type defaults to "general"
  - `eval_model_routing_unknown_risk_defaults` — Unknown risk defaults to "low"
  - `eval_model_routing_fallback_available` — Fallback provider available for supported providers

## Verification

```
python3 evals/run_evals.py → 558 passed, 0 failed
python3 -m unittest tests.test_model_router tests.test_config tests.test_mini_agent → 178 tests OK
git diff --check → clean
```

## Notes

- No runtime changes required.
- No commit or push performed.
- Worktree was clean before editing.
