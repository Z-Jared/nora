# Nora Phase Status

Last updated: 2026-06-10

## Current Phase

- Phase: Phase 2 - Voice & Presence
- Percent: 70%
- Status: in progress
- Current focus: TASK-188A / TASK-188B extracting the Pet Room memory diary native module and deterministic coverage.

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
- Pet Room deterministic skill ability shelf:
  - Pet Room now shows a read-only ability shelf derived only from bounded `identity.skills`.
  - Pet Room exposes stable `pet-skill-shelf`, `pet-skill-list`, `pet-skill-empty`, `pet-skill-card`, and `data-skill-count` markers.
  - Skill labels are bounded and filtered for non-string, empty, overlong, special-character, and secret-like values including `sk-*`, bearer, api key, token, secret, password, credential, private key, and auth patterns.
  - Empty or malformed skill renders clear stale `.pet-skill-card` content before returning.
  - Skill shelf updates are DOM/text-only and read-only: no tool/plugin execution, no fetch, no provider/network call, no food debit, no durable task, no activity/relationship-memory write, and no voice/native/PWA/3D/marketplace drift.
  - Deterministic coverage locks markers, mapping rules, read-only/no-tool behavior, no marketplace/surveillance copy, stale-content cleanup, secret-like filtering, and TASK-178 coverage preservation.
  - Verification is green: 372 targeted tests OK, 714 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pencil Pet Room design restoration:
  - `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md` now records `designs/nora_pet_web_ui.pen` `Room canvas` as the Pet Room front-end source of truth.
  - Pet Room now includes a warm Pencil-derived design shell, wall/floor canvas, local ceramic Nora-01 hero asset, CSS fallback, name/role display, and Mood/Presence/Energy/Bond status chips.
  - The source asset path remains `designs/images/generated-1780975241297.png`; the file bytes are JPEG, so the Web UI uses a controlled static copy at `mini_agent/static/nora-01-hero.jpg`.
  - Existing Pet Room functions remain preserved: food/status, identity editor, speech bubble/consent, expression/presence, greeting/reaction, skill shelf, diary/memory/actions.
  - Deterministic coverage locks the contract, markers, Pencil color tokens, local asset path/existence, no external hero image URL, and no marketplace/voice/native/PWA/3D scope drift.
  - Verification is green: 378 targeted tests OK, 719 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room design token and CSS module extraction:
  - `mini_agent/static/styles/tokens.css` now owns Pencil/Pet Room CSS custom properties for canvas, wall/floor, chips, ceramic fallback, action dock, stat bars, speech bubble, typography, and room shell values.
  - `mini_agent/static/styles/pet-room.css` now owns Pet Room CSS selectors while preserving DOM markers, `renderPet()` marker updates, local static serving, and no-build architecture.
  - `mini_agent/static/index.html` links local `/static/styles/tokens.css` and `/static/styles/pet-room.css`, with non-Pet Room CSS left inline for now.
  - Deterministic coverage locks CSS file presence, Pencil tokens after extraction, local stylesheet wiring, selector ownership, and no React/Vite/TypeScript/npm/Webpack/Rollup or product scope drift.
  - Verification is green: 381 targeted tests OK, 724 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room native API boundary extraction:
  - `mini_agent/static/api.js` now owns same-origin Pet Room API wrappers and `PET_ENDPOINTS` for current local endpoints.
  - `mini_agent/static/index.html` loads the wrapper with `<script type="module">` and routes Pet Room calls through `PetAPI`.
  - Auth bearer header behavior, JSON parsing, `_authError` handling, request/response shapes, DOM markers, stylesheet links, and existing UI behavior are preserved.
  - Deterministic coverage locks native exports, endpoint catalog, auth header behavior, local module wiring, no hidden external URL, and no React/Vite/TypeScript/npm/build-system/product scope drift.
  - Verification is green: 387 targeted tests OK, 729 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room native canvas module extraction:
  - `mini_agent/static/components/pet-room-canvas.js` now owns the visual/read-only first-screen canvas update boundary.
  - `mini_agent/static/index.html` imports `updateCanvas()` locally and keeps Pet Room API calls routed through `PetAPI`.
  - The module updates only room name, relationship role, and Mood/Presence/Energy/Bond chip text with DOM text APIs.
  - Design markers and local hero asset path remain stable: `pet-room-design-shell`, `pet-room-canvas`, `pet-room-hero-image`, `pet-room-status-chip`, `pet-room-name`, `pet-room-role`, chip markers, and `/static/nora-01-hero.jpg`.
  - Deterministic coverage locks module exports, local module wiring, marker preservation, no fetch/PetAPI/endpoint behavior, no external URL, no build-system drift, and no product scope drift.
  - Verification is green: 393 targeted tests OK, 734 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room native status chips module extraction:
  - `mini_agent/static/components/status-chips.js` now owns only Mood/Presence/Energy/Bond chip value text updates.
  - `pet-room-canvas.js` delegates chip updates to `updateStatusChips()` while retaining room name and relationship role updates.
  - The status chips module uses DOM `textContent`, has no fetch/PetAPI/endpoint behavior, and does not touch voice, food, memory, identity, skill/plugin, runtime, or provider boundaries.
  - Deterministic coverage locks module exports, local wiring, required chip markers, read-only/no-fetch/no-PetAPI/no-endpoint behavior, no external URL, no build-system drift, and no product scope drift.
  - Verification is green: 400 targeted tests OK, 739 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room native food panel module extraction:
  - `mini_agent/static/components/food-panel.js` now owns food stat/balance updates, cost estimate rendering, and feed/add-food button wiring.
  - `mini_agent/static/index.html` imports `updateFoodPanel()`, `loadCostEstimates()`, and `wireFoodButtons()` locally while keeping Pet Room API calls routed through delegated `PetAPI` / `petAction` boundaries.
  - The food panel module has no direct `fetch`, no direct `PetAPI` reference, no external URL, and no endpoint shape changes; cost estimates still cover feed/chat/voice/work.
  - Deterministic coverage locks module exports, local wiring, food markers, delegated API/action boundaries, no build-system drift, no payment/marketplace/manipulative copy, and no product scope drift.
  - Verification is green: 411 targeted tests OK, 744 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room native skill shelf module extraction:
  - `mini_agent/static/components/skill-shelf.js` now owns deterministic skill card derivation and shelf rendering.
  - `mini_agent/static/index.html` imports `skillCardsFromIdentity()` and `renderSkillShelf()` locally while keeping skill shelf read-only and disconnected from PetAPI, petAction, `/pet/` endpoints, tool execution, plugin execution, runtime calls, and capability routing.
  - The module preserves icon mapping, unknown default icon behavior, secret-like filtering, special-character/overlong/non-string filtering, empty/malformed stale card cleanup, and stable `pet-skill-*` / `skill-*` / `data-skill-count` markers.
  - Deterministic coverage locks the new module, legacy skill shelf contracts after extraction, no external URL/build-system drift, no marketplace/payment/premium skill drift, and no voice/PWA/native/3D scope drift.
  - Verification is green: 411 targeted tests OK, 750 evals passed, 0 failed, 0 skipped, `git diff --check` clean.
- Pet Room native voice preview module extraction:
  - `mini_agent/static/components/voice-preview.js` now owns the text-only voice preview consent gate, input validation, button wiring, fallback text rendering, and metadata tag rendering.
  - `mini_agent/static/index.html` imports `wireVoicePreview()` locally while keeping preview calls delegated through injected `PetAPI.previewVoice` and auth errors delegated through `handleAuthError`.
  - The module preserves consent-before-call, empty/over-500 validation, bounded preview failure copy, safe DOM text rendering, escaped meta tags, and stable `speech-bubble-*`, `voice-consent-*`, and `speech-preview-*` markers.
  - Deterministic coverage locks module exports, local wiring, delegated API boundary, combined speech/consent surface scanning, no direct fetch/endpoint literal, no build-system drift, and no audio/recording/provider/payment/PWA/native/3D scope drift.
  - Verification is green: 421 targeted tests OK, 756 evals passed, 0 failed, 0 skipped, `git diff --check` clean.

## In Progress
- TASK-188A: Extract Pet Room Memory Diary native module — assigned to Claude A.
- TASK-188B: Memory Diary module deterministic coverage — assigned to Claude B.

## Next

1. Wait for Claude A/B completion reports for TASK-188A / TASK-188B.
2. PM initial review must combine both changes and verify `memory-diary.js` preserves delegated API boundaries, escaped rendering, shared moment refresh behavior, and no direct endpoint/fetch drift.
3. Keep Phase 2 on A/B only until Web/PWA presence or desktop shell has independent file boundaries.
4. Continue avoiding real audio/TTS providers, native/desktop presence, PWA/service workers, notifications, billing, marketplace, and 3D/VRM until explicit later-phase tasks.

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
   - Claude A: Voice/Profile/Presence product implementation; last completed TASK-187A voice preview module extraction.
   - Claude B: deterministic evals, safety, cost transparency, and UI smoke coverage; last completed TASK-187B voice preview module coverage.
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
- Phase 2 Voice & Presence: 70% / Voice Profile, TTS text fallback, Pet Room speech bubble preview, consent/cost boundary, CSS-only expression mapping, CSS-only idle/presence signals, deterministic room-load greeting, deterministic interaction reactions, deterministic skill ability shelf, Pencil Pet Room restoration, Pet Room CSS/token extraction, native Pet Room API boundary extraction, native Pet Room canvas module extraction, native status chips module extraction, native food panel module extraction, native skill shelf module extraction, and native voice preview module extraction complete
- Phase 3 Skill Runtime Reframing: 0% / not started
- Phase 4 Platform & Marketplace: 0% / not started
