# TASK-188A: Extract Pet Room Memory Diary native module

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 70% complete. TASK-187 extracted Pet Room voice preview into `mini_agent/static/components/voice-preview.js`. The next frontend architecture slice is Step 4 in:

- `docs/knowledge/NORA_FRONTEND_ARCHITECTURE_PLAN.md`

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
- `mini_agent/static/index.html`
- `mini_agent/static/api.js`
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`
- `mini_agent/static/components/voice-preview.js`
- `tests/test_webui_smoke.py`

## Goal

Create `mini_agent/static/components/memory-diary.js` and move the Pet Room Today diary, relationship memory list rendering, and shared moment button wiring out of `index.html` into a bounded native ES module without changing API request shapes, DOM markers, copy, auth delegation, escaping behavior, or reaction/notice behavior.

## Required Work

1. Create `mini_agent/static/components/memory-diary.js`.
   - Use native browser JavaScript only.
   - Export a small API, expected shape:
     - `loadTodayDiary(petId, api)`
     - `loadRelationshipMemories(petId, api, onAuthError)`
     - `wireMemoryDiary(getPet, api, callbacks)`
   - Preserve current behavior for:
     - Today diary combines `api.getPetActivity(petId, 5)` and `api.getRelationshipMemory(petId, 3)`.
     - Empty Today diary copy: `Start your first interaction above.`
     - Activity item time uses `created_at.substring(11,16)`.
     - Memory diary item uses `memory` as time label and renders `[kind] summary`.
     - Relationship memory list empty copy: `No memories yet.`
     - Shared moment prompt copy: `Describe the shared moment:`
     - Shared moment request body: `{pet_id, kind:'shared_moment', summary, source:'pet_room_demo'}`.
     - After a successful shared moment: refresh relationship memories and Today diary, show `memory recorded.`, and call the existing reaction callback with `shared_moment`.
     - Auth error delegation through the existing `handleAuthError({status:401})` path.
   - The module may own these markers/classes only:
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
     - `pet-loading`
   - Dynamic text must use DOM text APIs or `escapeHtml` before HTML insertion.

2. Update the smallest implementation boundary in `index.html`.
   - Import the memory diary functions from `/static/components/memory-diary.js`.
   - Replace inline `loadTodayDiary`, `loadRelationshipMemories`, and `pet-memory-moment-btn` click wiring with module calls.
   - Keep Pet Room API calls delegated through existing `PetAPI` or an injected API object/function.
   - Preserve existing DOM IDs/classes/markers and user-visible copy.
   - Keep `renderPet()`, `petAction()`, `showRoomNotice()`, and `applyReaction()` behavior intact.

3. Add or adjust focused smoke tests only where needed.
   - Lock that `memory-diary.js` exists and is locally wired.
   - Lock expected exports.
   - Lock no direct fetch/no direct endpoint literal/no external URL/no build-system markers.
   - Lock Today diary rendering, relationship memory list rendering, shared moment request body, refresh behavior, and auth failure delegation still work.

## Allowed Files

- `mini_agent/static/components/memory-diary.js`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/static/api.js`
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`
- `mini_agent/static/components/voice-preview.js`
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

Do not add or implement:

- New HTTP endpoints or changed endpoint shapes
- New relationship-memory kinds, scoring, persistence rules, or backend mutations
- React, Vite, TypeScript, Node build steps, npm packages, bundlers, import maps, or transpilers
- Real TTS provider integration, audio playback, recording, voice cloning, or provider credential/config UI
- Food debit mutation or payment/billing/checkout/purchase pressure copy
- Microphone, camera, screen, or location access
- Desktop/native shell
- PWA/service worker/notification permission
- Marketplace, premium voice/skill packs, plugin installation, or real skill/tool execution
- 3D/VRM/Live2D runtime

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|/pet/activity|/pet/relationship-memory|tool_call|execute_tool|run_tool|install plugin|plugin store|marketplace|premium skill|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" mini_agent/static/index.html mini_agent/static/components/memory-diary.js tests/test_webui_smoke.py
```

The scan may hit existing negative test assertions or unrelated legacy memory UI outside the Pet Room module. `memory-diary.js` itself must not contain direct `fetch(`, direct `/pet/activity` or `/pet/relationship-memory` endpoint literals, external URLs, build tooling, audio/recording/payment/marketplace/provider-activation, PWA/native, or 3D scope-drift markers. Document expected hits.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-188A`.
