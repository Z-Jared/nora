# Nora Phase Status

Last updated: 2026-06-08

## Current Phase

- Phase: Phase 1 - Pet Life MVP
- Percent: 97%
- Status: in progress
- Current focus: Phase 1 Exit Gate final Phase 2 Voice & Presence technical plan.

## Completed This Phase

- Pet Identity / Pet State deterministic foundation.
- Pet Room MVP and local HTTP pet API.
- Nora-01 robot default identity and living Pet Room redesign.
- Token Food Economy estimate/status MVP:
  - `/pet/food-status` read-only cost and balance endpoint.
  - Deterministic local MVP costs: feed=100, chat=25, voice=80, work=150.
  - Pet Room transparent balance and estimated cost display.
  - Guarded no-secret/no-negative/no-manipulative-copy coverage.
- Relationship Memory MVP:
  - `POST /pet/relationship-memory` and `GET /pet/relationship-memory` local HTTP API.
  - Bounded `shared_moment` / `preference` / `task_outcome` records.
  - Pet Room relationship memory section with escaped rendering.
  - Guarded no-secret/no-fake-intimacy/no-auth-regression coverage.
- Identity Editor MVP:
  - `POST /pet/update-identity` local HTTP API.
  - Pet Room Identity Editor for name/species/role/style/traits/skills/voice/taste.
  - Preserves pet_id, created_at, pet state, compute food, activity, and relationship memories.
  - Guarded no-secret/no-auth/no-marketplace/no-voice-cloning coverage.
- Phase 1 MVP release audit:
  - `docs/knowledge/PHASE_1_MVP_RELEASE_AUDIT.md` documents first-use flow, safety, no-manipulation checks, and verification.
  - README documents the Phase 1 local Pet Room demo path.
  - Verification is green: 337 targeted tests OK, 671 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
  - Reviewer approved TASK-167 while keeping Phase 1 in Exit Gate until TASK-168/169/170 complete.
- Phase 1.5 Pet Room life-feel polish:
  - Pet Room now shows deterministic mood summary, identity details, bounded room notices, and a Today diary from activity plus relationship memory.
  - Shared Moment creation refreshes both relationship memories and Today diary.
  - Web UI smoke coverage locks life-feel markers, mood copy, room notices, diary rendering/empty state, and HTML escaping.
- Commercial/no-manipulation audit:
  - `docs/knowledge/PHASE_1_COMMERCIAL_NO_MANIPULATION_AUDIT.md` documents Token Food, future membership/expansion boundaries, local demo limits, and no-manipulation findings.
  - `commercial_no_manipulation_scan` covers README, Pet Room, and audit doc with context-aware negative-disclaimer handling.
  - Verification is green: 343 targeted tests OK, 672 evals passed, 0 failed, 0 skipped, `git diff --check` clean.

## In Progress

- Phase 1 Exit Gate is active. Release audit, life-feel polish, and commercial/no-manipulation audit are complete; PM must still complete the Phase 2 technical plan before moving to Phase 2.

## Next

1. TASK-170 Phase 2 Voice & Presence technical plan with worker scaling plan.

## Phase 1 Exit Criteria

Phase 1 cannot be marked complete until all of these are true:

1. Identity Editor MVP is implemented, reviewed, integrated, and covered by deterministic tests/evals.
2. Token Food Economy, Relationship Memory, Pet Room, Pet State, and Pet Identity all have active regression coverage with 0 task-related eval skips.
3. The Web UI supports a first-use pet loop: see the pet, understand its identity/state/food, edit identity, feed/interact, and see activity or memory feedback.
4. PM has completed a user-perspective walkthrough and documented whether the product feels like a configurable electronic lifeform instead of a raw dashboard or chatbot.
5. Commercial copy has passed a no-manipulation audit: no guilt, loneliness pressure, fake intimacy, hidden cost, voice-cloning pressure, marketplace pressure, or misleading token-food language.
6. README/demo or equivalent project documentation explains the Phase 1 local MVP path.
7. Full verification has passed or baseline failures are documented and separated from Phase 1 changes:
   - `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke`
   - `python3 evals/run_evals.py`
   - `git diff --check`

## Phase 1 Exit Gate Queue

After the Identity Editor tasks land, PM must complete these gate tasks before moving to Phase 2:

1. Phase 1 MVP release audit: complete.
2. Phase 1.5 Pet Room life-feel polish: complete.
3. Commercial model and no-manipulation audit: complete.
4. Phase 2 Voice & Presence technical plan: pending; plan voice profile, TTS boundary, Web/PWA presence, desktop floating pet path, safety, consent, cost controls, and worker scaling.

Phase 2 remains blocked until the Exit Gate Queue is complete and this file is updated to mark Phase 1 as complete.

## Phase 2 Worker Scaling Gate

Before Phase 2 starts, PM must decide and record the Claude worker plan:

1. Keep at least Claude A and Claude B active:
   - Claude A for Voice/Profile/Presence product implementation.
   - Claude B for deterministic evals, safety, cost transparency, and UI smoke coverage.
2. Automatically open or configure additional Claude workers when Phase 2 has independent workstreams with low file conflict risk:
   - Claude C for Web/PWA floating pet presence or responsive UI shell.
   - Claude D for TTS adapter or desktop prototype only after the API boundary is stable.
3. Do not open extra workers if the module boundaries are not ready; first create a small architecture-splitting task.
4. Record active workers, task ownership, file boundaries, and blockers here before dispatching the first Phase 2 tasks.
5. Workers still must not commit or push; Codex PM owns review, integration, commits, and phase status updates.

## Blockers

- None for current local MVP development.
- Real billing/payment, 3D/VRM, voice deep work, marketplace, and cross-device native presence remain later-phase work.
- Phase 2 is intentionally blocked by the Phase 1 Exit Gate Queue above.

## Four-Phase Overview

- Phase 1 Pet Life MVP: 97% / Exit Gate final planning
- Phase 2 Voice & Presence: 0% / not started
- Phase 3 Skill Runtime Reframing: 0% / not started
- Phase 4 Platform & Marketplace: 0% / not started
