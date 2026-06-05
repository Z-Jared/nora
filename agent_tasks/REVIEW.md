# CCB Review — TASK-117 / TASK-118

**Status: APPROVED**

## TASK-117: Skill-aware capability routing bridge v1

Reviewer: CCB reviewer (`job_f788d6ec4c66`)

Clean implementation of the skill-aware capability routing bridge. No blocking issues found.

- Backwards compatible: `skill_manifest_jsons` defaults to `None` / `"[]"`; plugin-only callers keep the existing behavior.
- Read-only: routing remains pure and does not load skill files, import skill modules, load plugins, execute plugin code, call external services, or mutate durable task/worker/event state.
- Safe bounded output: candidate skill/plugin names and versions use secret-like redaction, malformed skill/plugin manifest input returns bounded errors, and sentinel no-leak tests pass.
- Aggregation is correct: matched skills contribute deduplicated `required_plugins`, `risk_boundaries`, and deliverables; high-risk skill boundaries elevate the top-level risk.
- Registry integration is correct: `route_capability_request` accepts `skill_manifest_jsons` and retains `ToolPermission(category="local", risk="read")`.
- PM verification: 265 focused tests OK, 436 evals passed, `git diff --check` clean, and combined skill+plugin permission/no-leak/no-mutation probe OK.

Residual risk: none identified.

## TASK-118: Deterministic eval coverage for skill and capability manifest surfaces v1

Reviewer: CCB reviewer (`job_8a68523d230c`)

Clean deterministic eval expansion for the skill manifest and capability routing surfaces. No blocking issues found.

- Added 14 offline evals: 7 for `inspect_skill_manifest`, 7 for `route_capability_request`.
- Coverage includes exact local/read permission, valid bounded output, malformed JSON/non-object/list-field safety, secret no-leak, durable task/worker/event no-mutation, and plugin/skill/routing/MCP compatibility.
- Evals are deterministic and isolated with temporary workspaces and local `NoraDB`; no LLM, network, or external state.
- Runtime behavior is unchanged; only `evals/run_evals.py` was modified.
- Non-blocking note: permission evals use `registry._tools`, which matches existing eval practice and has no runtime impact.
- PM verification: 450 evals passed, 242 focused tests OK, and `git diff --check` clean.

Residual risk: none identified.
