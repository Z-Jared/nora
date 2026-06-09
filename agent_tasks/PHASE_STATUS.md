# Nora Phase Status

Last updated: 2026-06-09

## Current Phase

- Phase: Phase 2 - Voice & Presence
- Percent: 45%
- Status: in progress
- Current focus: Next bounded Voice & Presence presence step after deterministic interaction reactions.

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
- Phase 2 Voice & Presence technical plan:
  - `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md` documents Voice Profile v1, TTS adapter boundary, Web/PWA presence path, desktop floating pet prerequisites, safety policy, eval plan, task candidates, and worker scaling.
  - Phase 2 starts with A/B only; Claude C/D are deferred until independent low-conflict workstreams exist.
  - Verification is green: 343 targeted tests OK, 672 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Voice Profile v1 identity contract:
  - `PetStore.create_pet()` and `PetStore.update_identity()` normalize bounded local voice metadata fields.
  - Allowed fields are `voice_id`, `speed`, `tone`, `pitch`, `expression_hints`, and `speech_style_override`.
  - Unsafe audio sample, speaker embedding, clone reference, provider credential, and secret-like nested values are rejected recursively.
  - Unknown non-secret fields are stripped without storing unsupported voice data.
  - Deterministic coverage locks default no-cloning, bounded fields, recursive/list secret rejection, HTTP create/update preservation, and no promotional voice/payment/marketplace/background-listening copy.
  - Verification is green: 369 targeted tests OK, 677 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- TTS adapter boundary with deterministic text fallback:
  - `mini_agent/tts.py` defines a local text-only `TextFallbackTTSAdapter`, deterministic `cost_tokens` estimate, bounded preview length, and state-derived mood context.
  - `POST /pet/voice-preview` returns text fallback metadata with `has_audio: false`, no-audio reason, no network/provider call, no recording, voice profile summary, and mood context.
  - Preview rejects missing, empty, non-string, secret-like, and over-500-character text without echoing secret or over-limit input.
  - Preview is read-only: no compute food debit, no pet state mutation, no activity event, and no relationship-memory write.
  - Deterministic coverage locks fallback availability, cost transparency, secret rejection/no echo, read-only behavior across food/state/activity/memory, and no recording/background/voice-cloning/payment/marketplace copy.
  - Verification is green: 274 targeted tests OK, 682 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room speech bubble text fallback surface:
  - Pet Room now exposes a visible text-only speech bubble near the robot avatar.
  - The preview control calls `POST /pet/voice-preview` and displays fallback text plus cost/no-audio/no-network/no-recording metadata.
  - UI errors are bounded and avoid raw secret or over-limit text echo.
  - Dynamic speech text uses DOM text APIs, while generated meta tags use escaping before HTML insertion.
  - Deterministic coverage locks all speech bubble DOM markers, preview request shape, text escaping, metadata visibility, and no voice-cloning/recording/background-listening/marketplace/payment copy drift.
  - Verification is green: 281 targeted tests OK, 686 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Voice preview consent and cost confirmation boundary:
  - `POST /pet/voice-preview` now exposes stable consent/cost/provider metadata: `requires_user_confirmation`, `confirmation_kind`, `audio_requires_confirmation`, `provider_status`, and `food_debit`.
  - Pet Room speech preview now requires an explicit confirmation checkbox before it fetches `/pet/voice-preview`.
  - The UI displays text-only preview, estimated cost, no-audio, no-network/provider, no-recording, and no-food-debit/read-only boundaries.
  - Dynamic speech text remains rendered with DOM text APIs and generated meta tags use escaping.
  - Deterministic coverage locks consent DOM markers, unchecked no-fetch control flow, HTTP metadata, and no voice-cloning/recording/background-listening/marketplace/payment copy drift.
  - Verification is green: 284 targeted tests OK, 691 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- CSS-only expression state mapping:
  - Pet Room robot avatar now maps mood, energy, and hunger into deterministic expression states: hungry, sleepy, low-energy, happy, focused, and calm.
  - Avatar root exposes stable `data-expression` and `expression-*` classes.
  - Pet Room exposes `pet-expression-state`, `pet-expression-icon`, `pet-expression-label`, and `pet-expression-detail` markers.
  - Expression updates are CSS/DOM-only and read-only: no provider/network calls, no voice preview call, no food debit, no state/activity/relationship-memory mutation, and no microphone/camera/screen/location access.
  - Dynamic expression label/detail use DOM text APIs.
  - Deterministic coverage locks exact markers/classes, mood/energy/hunger mapping fallback, function-body read-only checks, and no voice/surveillance/marketplace/3D scope drift.
  - Verification is green: 297 targeted tests OK, 695 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- CSS-only idle/presence signals:
  - Pet Room robot avatar now maps bounded mood, energy, hunger, and bond into deterministic presence states: charging, resting, alert, drifting, and waiting.
  - Avatar root exposes stable `data-presence` and `presence-*` classes.
  - Pet Room exposes `pet-presence-state`, `pet-presence-icon`, `pet-presence-label`, and `pet-presence-detail` markers.
  - Presence updates are CSS/DOM-only and read-only: no provider/network calls, no voice preview call, no food debit, no state/activity/relationship-memory mutation, and no microphone/camera/screen/location access.
  - `clampState()` normalizes null, undefined, strings, booleans, NaN, Infinity, negative values, and values over 100 before presence mapping or detail text.
  - Dynamic presence label/detail use DOM text APIs.
  - Deterministic coverage locks markers/classes, bounded mapping fallback, malformed-state clamp behavior, function-body read-only checks, and no voice/native/PWA/surveillance/marketplace/3D scope drift.
  - Verification is green: 317 targeted tests OK, 700 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Deterministic room-load greeting:
  - Pet Room now renders a text-only room-load greeting when the current pet is displayed.
  - Greeting text and meta derive only from bounded mood, energy, hunger, bond, and a coarse local time bucket.
  - Pet Room exposes stable `pet-room-greeting`, `pet-room-greeting-text`, `pet-room-greeting-meta`, and `data-greeting` markers.
  - Greeting updates are read-only: no provider/network calls, no voice preview call, no food debit, no state/activity/relationship-memory mutation, and no microphone/camera/screen/location access.
  - Dynamic greeting text/meta use DOM text APIs.
  - Deterministic coverage locks markers, state/time-bucket mapping fallback, function-body read-only checks, malformed-state handling, and no voice/native/PWA/surveillance/marketplace/3D scope drift.
  - Verification is green: 333 targeted tests OK, 704 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Deterministic interaction reaction surface:
  - Pet Room now shows a text-only immediate reaction after successful feed, care, add demo food, and shared moment interactions.
  - Reaction text and meta derive only from bounded action type, existing interaction result, and bounded pet state.
  - Pet Room exposes stable `pet-room-reaction`, `pet-room-reaction-text`, `pet-room-reaction-meta`, and `data-reaction` markers.
  - `petAction('/pet/add-food', ...)` normalizes `add-food` to `food_added` before applying the reaction, so the demo food path does not fall through to neutral.
  - Reaction updates are read-only beyond the existing user-triggered interaction request: no provider/network calls beyond the original endpoint, no voice preview call, no food debit, no state/activity/relationship-memory mutation, and no microphone/camera/screen/location access.
  - Dynamic reaction text/meta use DOM text APIs.
  - Deterministic coverage locks markers, action/state/result/fallback mapping, add-food normalization, function-body read-only checks, and no voice/native/PWA/surveillance/marketplace/3D scope drift.
  - Verification is green: 356 targeted tests OK, 708 evals passed, 0 failed, 0 skipped, `git diff --check` clean.

## In Progress

- None assigned after TASK-178 integration.

## Next

1. Select the next bounded Phase 2 presence task from the Voice & Presence plan.
2. Keep Phase 2 on A/B only until Web/PWA presence or desktop shell has independent file boundaries.
3. Continue avoiding real audio/TTS providers, native/desktop presence, PWA/service workers, notifications, billing, marketplace, and 3D/VRM until explicit later-phase tasks.

## Phase 1 Exit Criteria

Phase 1 is complete. Completion evidence:

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
4. Phase 2 Voice & Presence technical plan: complete.

Phase 1 Exit Gate is complete. Phase 2 may start with the worker plan below.

## Phase 2 Worker Scaling Gate

Phase 2 start worker plan:

1. Keep Claude A and Claude B active only at Phase 2 start:
   - Claude A: Voice/Profile/Presence product implementation.
   - Claude B: deterministic evals, safety, cost transparency, and UI smoke coverage.
2. Do not open Claude C/D for the first Phase 2 tasks because initial Voice/Profile/Presence work shares `mini_agent/pets.py`, `mini_agent/server.py`, `mini_agent/static/index.html`, test files, and eval files.
3. Automatically open or configure additional Claude workers only when Phase 2 has independent workstreams with low file conflict risk:
   - Claude C for Web/PWA floating pet presence or responsive UI shell.
   - Claude D for TTS adapter or desktop prototype only after the API boundary is stable.
4. Record any future C/D opening here before dispatching tasks.
5. Workers still must not commit or push; Codex PM owns review, integration, commits, and phase status updates.

## Blockers

- None for current Phase 2 A/B start.
- Real billing/payment, 3D/VRM, voice deep work, marketplace, and cross-device native presence remain later-phase work.
- Real TTS provider integration remains blocked until a later provider task adds explicit provider configuration, cost/food-debit confirmation, and no-cloning/no-recording safeguards.

## Four-Phase Overview

- Phase 1 Pet Life MVP: 100% / complete
- Phase 2 Voice & Presence: 45% / Voice Profile, TTS text fallback, Pet Room speech bubble preview, consent/cost boundary, CSS-only expression mapping, CSS-only idle/presence signals, deterministic room-load greeting, and deterministic interaction reactions complete
- Phase 3 Skill Runtime Reframing: 0% / not started
- Phase 4 Platform & Marketplace: 0% / not started
