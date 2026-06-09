# TASK-185A: Extract Pet Room Food Panel native module

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 64% complete. TASK-184 extracted `mini_agent/static/components/status-chips.js`. The next frontend architecture slice is Step 4 in:

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
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `tests/test_webui_smoke.py`

## Goal

Create `mini_agent/static/components/food-panel.js` and move the Pet Room Compute Food / Token Energy panel rendering and cost estimate DOM updates out of `index.html` into a bounded native ES module without changing UI behavior, DOM markers, endpoint shapes, or Token Food safety copy.

## Required Work

1. Create `mini_agent/static/components/food-panel.js`.
   - Use native browser JavaScript only.
   - Export a small API for food panel DOM updates and cost estimate rendering.
   - It may own these markers only:
     - `stat-food`
     - `bar-food`
     - `pet-food-balance`
     - `pet-cost-table`
     - `pet-food-amount`
     - `pet-add-food-btn` only for wiring if needed
     - `pet-feed-btn` only for wiring if needed
   - It must preserve the existing action set: `feed`, `chat`, `voice`, `work`.
   - Dynamic text must use DOM text APIs or escaped HTML for bounded generated rows.

2. Update the smallest implementation boundary.
   - Prefer importing food panel functions into `index.html` while keeping global behavior stable.
   - Keep all Pet Room API calls routed through `PetAPI` from `api.js`.
   - Do not direct-fetch `/pet/food-status`, `/pet/feed`, or `/pet/add-food` from the module.
   - Preserve `petAction()` behavior unless a minimal delegation is needed.
   - Preserve existing DOM IDs/classes/markers and user-visible copy.
   - Preserve `renderPet()` behavior for `stat-food`, `bar-food`, `pet-food-balance`, and cost estimates.

3. Add or adjust focused smoke tests only where needed.
   - Lock that `food-panel.js` exists and is locally wired.
   - Lock expected exports.
   - Lock no direct fetch/no external URL/no build-system markers.
   - Lock `PetAPI` boundary for food status/feed/add food remains intact.
   - Lock render behavior still updates food balance and cost table markers.

## Allowed Files

- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/static/api.js`
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
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
- React, Vite, TypeScript, Node build steps, npm packages, bundlers, import maps, or transpilers
- Skill shelf, voice preview, memory diary, identity editor, or API module extraction
- Real payment, billing, checkout, marketplace, premium skill packs, or purchase pressure copy
- Real voice/TTS/audio playback or recording
- Microphone, camera, screen, location access
- Desktop/native shell
- PWA/service worker/notification permission
- Real skill execution or plugin installation
- 3D/VRM/Live2D runtime

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|purchase tokens|buy more food|top up to feed|your pet is starving|pet will die|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" mini_agent/static/index.html mini_agent/static/components/food-panel.js tests/test_webui_smoke.py
```

The scan may hit existing negative test assertions. `food-panel.js` itself must not contain direct `fetch(`, external URLs, build tooling, payment/marketplace/purchase-pressure, or scope-drift markers. Document expected hits.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-185A`.
