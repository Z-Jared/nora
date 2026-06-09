# TASK-186A: Extract Pet Room Skill Shelf native module

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 66% complete. TASK-185 extracted `mini_agent/static/components/food-panel.js`. The next frontend architecture slice is Step 4 in:

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
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/components/food-panel.js`
- `tests/test_webui_smoke.py`

## Goal

Create `mini_agent/static/components/skill-shelf.js` and move the Pet Room deterministic skill ability shelf mapping/rendering out of `index.html` into a bounded native ES module without changing UI behavior, DOM markers, filtering rules, or read-only safety boundaries.

## Required Work

1. Create `mini_agent/static/components/skill-shelf.js`.
   - Use native browser JavaScript only.
   - Export a small API for skill shelf card derivation/rendering.
   - Preserve the current `skillCardsFromIdentity(identity, state)` and `renderSkillShelf(identity, state)` behavior, either as the exported function names or as compatible exported wrappers.
   - It may own these markers/classes only:
     - `pet-skill-shelf`
     - `pet-skill-list`
     - `pet-skill-empty`
     - `pet-skill-card`
     - `skill-icon`
     - `skill-name`
     - `data-skill-count`
   - It must preserve the existing icon mapping and default icon behavior.
   - It must preserve filtering for non-string, empty, overlong, special-character, and secret-like skill labels.
   - Dynamic skill label/icon text must use DOM text APIs or escaped HTML.

2. Update the smallest implementation boundary.
   - Import the skill shelf functions into `index.html` while keeping global behavior stable for tests.
   - Preserve `renderPet()` behavior and the call site that renders the skill shelf.
   - Preserve existing DOM IDs/classes/markers and user-visible copy.
   - Do not route skill shelf through PetAPI, petAction, or tool/plugin/runtime code.

3. Add or adjust focused smoke tests only where needed.
   - Lock that `skill-shelf.js` exists and is locally wired.
   - Lock expected exports.
   - Lock no direct fetch/no PetAPI/no petAction/no external URL/no build-system markers.
   - Lock marker preservation, valid/unknown skill rendering, secret filtering, and stale cleanup still work.

## Allowed Files

- `mini_agent/static/components/skill-shelf.js`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/static/api.js`
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/components/food-panel.js`
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
- Voice preview, memory diary, identity editor, or API module extraction
- Real skill execution, tool execution, plugin installation, marketplace, or premium skill packs
- Real payment, billing, checkout, or purchase pressure copy
- Real voice/TTS/audio playback or recording
- Microphone, camera, screen, location access
- Desktop/native shell
- PWA/service worker/notification permission
- 3D/VRM/Live2D runtime

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|PetAPI|petAction|tool_call|execute_tool|run_tool|install plugin|plugin store|marketplace|premium skill|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" mini_agent/static/index.html mini_agent/static/components/skill-shelf.js tests/test_webui_smoke.py
```

The scan may hit existing negative test assertions. `skill-shelf.js` itself must not contain direct `fetch(`, PetAPI, petAction, tool/plugin execution, external URLs, build tooling, payment/marketplace/purchase-pressure, or scope-drift markers. Document expected hits.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-186A`.
