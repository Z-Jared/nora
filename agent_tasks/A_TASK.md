# TASK-183A: Extract Pet Room Canvas native module

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 60% complete. TASK-182 extracted Pet Room API calls into native `mini_agent/static/api.js`. The next frontend architecture slice is Step 3 in:

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
- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`
- `tests/test_webui_smoke.py`

## Goal

Create `mini_agent/static/components/pet-room-canvas.js` and move the first-screen visual Pet Room canvas boundary into a native ES module without changing UI behavior, DOM markers, CSS selectors, asset paths, or API behavior.

## Required Work

1. Create `mini_agent/static/components/pet-room-canvas.js`.
   - Use native browser JavaScript only.
   - Export a small render/update API for the visual canvas boundary.
   - The module may own only:
     - wall/floor room canvas wiring,
     - Nora-01 hero image marker/reference,
     - ground shadow / visual shell marker wiring,
     - pet name and role text updates,
     - Mood/Presence/Energy/Bond chip text updates.
   - It must not call `fetch`, `PetAPI`, provider APIs, voice preview, food mutation, relationship memory, identity save, skill execution, or durable runtime tools.

2. Update `mini_agent/static/index.html`.
   - Import the canvas module with a local native module path.
   - Use the module from existing `renderPet()` or the smallest equivalent call site.
   - Preserve all existing DOM IDs/classes/markers, including:
     - `pet-room-design-shell`
     - `pet-room-canvas`
     - `pet-room-hero-image`
     - `pet-room-status-chip`
     - `pet-room-name`
     - `pet-room-role`
     - `chip-mood-value`
     - `chip-presence-value`
     - `chip-energy-value`
     - `chip-bond-value`
   - Preserve local `/static/nora-01-hero.jpg` usage and CSS fallback behavior.
   - Keep all Pet Room API calls routed through `PetAPI` from `api.js`.

3. Add or adjust focused smoke tests only where needed.
   - Lock that the canvas module is locally wired.
   - Lock that required design markers still exist.
   - Lock that the canvas update path still updates name/role/chip text.
   - Keep existing Web UI and HTTP tests passing.

## Allowed Files

- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
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

Do not add or implement:

- New HTTP endpoints or changed endpoint shapes
- React, Vite, TypeScript, Node build steps, npm packages, bundlers, import maps, or transpilers
- Food panel, skill shelf, voice preview, memory diary, identity editor, or API module extraction
- Real voice/TTS/audio playback or recording
- Microphone, camera, screen, location access
- Desktop/native shell
- PWA/service worker/notification permission
- Billing/payment/marketplace/premium skill packs
- Real skill execution or plugin installation
- 3D/VRM/Live2D runtime

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|PetAPI|voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" mini_agent/static/index.html mini_agent/static/components/pet-room-canvas.js tests/test_webui_smoke.py
```

The scan may hit allowed `PetAPI` usage in `index.html` and existing LLM setup URLs. `pet-room-canvas.js` itself must not contain `fetch(`, `PetAPI`, external URLs, build tooling, or scope-drift markers. Document any expected hits.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-183A`.
