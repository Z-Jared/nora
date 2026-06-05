# Claude A Completion Report

Status: ready for Codex review

## Summary

Extended `mini_agent/capability_router.py` to support skill-aware capability routing (TASK-117). The router now accepts optional `skill_manifest_jsons` alongside existing `plugin_manifest_jsons`, scores skill manifests against goals, and aggregates skill metadata (required_plugins, risk_boundaries, deliverables) into the route result.

## Changes

```text
 M mini_agent/capability_router.py
 M mini_agent/toolkits/registry_builder.py
 M tests/test_plugins.py
```

### mini_agent/capability_router.py

- Added `CandidateSkill` dataclass with: name, version, matched_domains, matched_capabilities, required_plugins, risk_boundaries, expected_deliverables
- Added `skill_manifest_jsons` parameter to `route_capability_request()` (pure function) and `route_capability_request_json()` (registry wrapper)
- Added `_score_skill_manifest()` for keyword-based scoring against skill manifest metadata
- Updated `_build_result()` to include candidate_skills, required_plugins, risk_boundaries
- Skill risk_boundaries aggregate into top-level risk_level (high boundaries elevate overall risk)
- Skill deliverables merge into expected_deliverables
- Imports from `mini_agent.skills`: `SkillManifest`, `parse_skill_manifest`, `parse_skill_manifest_json`, `_safe_str`
- Backwards compatible: callers using only `plugin_manifest_jsons` see identical behavior

### mini_agent/toolkits/registry_builder.py

- Updated `route_capability_request` registration to accept `skill_manifest_jsons` JSON string parameter
- Description updated to mention skill manifests

### tests/test_plugins.py

- Added `TestSkillAwareRouting` class with 25 tests:
  - Skill routing match/no-match
  - Skill + plugin combined routing
  - required_plugins aggregation
  - risk_boundaries aggregation and risk elevation
  - Deliverables from skills
  - Backwards compatibility (plugin-only, no skill param)
  - Malformed skill JSON / type errors
  - Output shape validation
  - No secret leak (name, version)
  - Multiple skills ranked, max_candidates
  - Deterministic output
  - JSON wrapper with skills
  - Registry tool has skill_manifest_jsons param
  - Registry call with skills
  - Registry call with skills + plugins combined
  - No durable mutation with skills

## Tests

```text
python3 -m unittest tests.test_plugins tests.test_skills tests.test_mini_agent
Ran 265 tests in 2.095s - OK

python3 evals/run_evals.py
436 passed, 0 failed

git diff --check
(clean)
```

## Notes

- No push performed.
- No edits to B_TASK, B_DONE, CODEX_TERMINAL_HANDOFF.md, or designs/.
- No conflicts with uncommitted work detected.
