# Claude B Done

## TASK-120: Deterministic eval coverage for skill-aware capability routing v1

**Status:** completed
**Date:** 2026-06-04

### Summary

Added 9 new deterministic eval cases to `evals/run_evals.py` covering the TASK-117 `skill_manifest_jsons` skill-aware capability routing path.

### New Eval Cases

1. **skill_aware_routing_skill_only** — Skill-only routing returns `candidate_skills` with matched domains/capabilities, required_plugins, risk_boundaries, and expected deliverables.
2. **skill_aware_routing_combined** — Combined skill + plugin routing returns both `candidate_skills` and `candidate_plugins`.
3. **skill_aware_routing_required_plugins_aggregation** — `required_plugins` and `risk_boundaries` aggregate as deterministic deduplicated sorted top-level fields across multiple matched skills.
4. **skill_aware_routing_high_risk_boundary** — High-risk skill boundary (e.g. `"high"` in risk_boundaries) elevates top-level `risk_level` to `"high"`.
5. **skill_aware_routing_malformed_outer_skill_json** — Malformed outer skill manifest JSON produces bounded safe errors.
6. **skill_aware_routing_malformed_individual_skill** — Malformed individual skill manifests (missing name/version, invalid JSON) produce bounded safe errors; no candidates returned.
7. **skill_aware_routing_secret_no_leak** — Secret-like skill manifest name/version/list items do not leak through routing output.
8. **skill_aware_routing_no_mutation** — Skill-aware routing does not mutate durable tasks, workers, or events.
9. **skill_aware_routing_plugin_only_compatibility** — Existing plugin-only routing (no `skill_manifest_jsons`) still works deterministically.

### Files Changed

- `evals/run_evals.py` — Added 9 eval cases + EvalCase registrations (only file modified)

### Verification

```
python3 evals/run_evals.py                           459 passed, 0 failed
python3 -m unittest tests.test_plugins tests.test_skills tests.test_mini_agent  265 tests OK
git diff --check                                      clean
```

### Notes

- No runtime modules changed.
- No edits to `designs/`, `CODEX_TERMINAL_HANDOFF.md`, `A_TASK.md`, or `A_DONE.md`.
- No commit or push performed.
- One test adjustment: `risk_boundaries` containing `"no-secrets"` is filtered by `_is_secret_like` pattern matching; replaced with `"high"` boundary to properly test aggregation.
