# TASK-188B: Memory Diary module deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 70% complete. TASK-188A will extract the Pet Room Today diary and relationship memory list into `mini_agent/static/components/memory-diary.js`.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `docs/knowledge/NORA_FRONTEND_ARCHITECTURE_PLAN.md`
- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `evals/run_evals.py`
- `tests/test_webui_smoke.py`
- `mini_agent/static/index.html`
- `mini_agent/static/components/voice-preview.js`

## Goal

Add deterministic coverage for TASK-188A so the Memory Diary module remains local, native-module-only, API-delegated, escaping-safe, auth-delegated, no-build, and free of extra memory mutation/provider/payment/native/PWA/3D drift.

## Required Coverage

Add evals whose names include `memory_diary_module`, for example:

- `memory_diary_module_file_present`
- `memory_diary_module_wired`
- `memory_diary_module_markers_preserved`
- `memory_diary_module_delegated_api_boundary`
- `memory_diary_module_rendering_and_refresh_contract`
- `memory_diary_module_no_scope_drift`

Coverage should verify:

1. `mini_agent/static/components/memory-diary.js` exists after TASK-188A and uses native JS exports.
2. `index.html` wires the component through a local native module import.
3. Required markers/classes remain present:
   - `pet-today-content`
   - `pet-today-item`
   - `today-time`
   - `today-text`
   - `pet-memory-moment-btn`
   - `pet-memory-list`
   - `pet-memory-item`
   - `kind`
   - `mem-summary`
   - `mem-meta`
4. Module preserves Today diary calls through delegated `api.getPetActivity(petId, 5)` and `api.getRelationshipMemory(petId, 3)`.
5. Module preserves relationship memory list rendering and shared moment request shape through delegated `api.createRelationshipMemory`.
6. Module preserves refresh behavior after successful shared moment: reload relationship memories, reload Today diary, show notice, and call reaction callback.
7. Module uses DOM text APIs or escaping for dynamic activity and memory text.
8. Existing Pet Room life-feel / Today diary / relationship memory evals remain active/pass after extraction. If old evals only scan `index.html`, update them to scan combined `index.html` + `memory-diary.js` surface while preserving original assertions.
9. No build-system drift: no React/Vite/TypeScript/npm/package.json/Webpack/Rollup/bundler/import-map dependency is added.
10. No product scope drift: no direct fetch or endpoint literals in `memory-diary.js`, no new backend mutation, no audio_url/audio bytes, real recording/background listening, voice cloning, microphone/camera/screen/location access, checkout/billing/real payment, provider activation, marketplace/plugin store/premium skill, PWA/service-worker/notification/native drift, or 3D/VRM/Live2D implementation drift.

Guard evals so they explain missing TASK-188A behavior during isolated worker runs, but after PM combines with TASK-188A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `mini_agent/static/components/memory-diary.js`
- `mini_agent/static/components/voice-preview.js`
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/api.js`
- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`
- `mini_agent/static/nora-01-hero.jpg`
- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`
- `designs/` or `.nora_design_exports/`
- `mini_agent/http_server.py`
- `mini_agent/pets.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files
- worker configuration or Claude C/D files

## Non-Goals

Do not implement UI/JS component behavior, create frontend modules yourself beyond tests/evals, add Playwright dependencies, add a frontend build system, or add real TTS/provider/audio/recording/payment/native/PWA/marketplace/3D/Live2D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|/pet/activity|/pet/relationship-memory|tool_call|execute_tool|run_tool|install plugin|plugin store|marketplace|premium skill|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-188B`.
