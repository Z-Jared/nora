# TASK-183B: Pet Room Canvas module deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 60% complete. TASK-182 extracted Pet Room API calls into `mini_agent/static/api.js`. TASK-183A will extract the first-screen visual Pet Room canvas boundary into `mini_agent/static/components/pet-room-canvas.js`.

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
- `mini_agent/static/api.js`

## Goal

Add deterministic coverage for TASK-183A so the new Pet Room Canvas module remains local, native-module-only, visual/read-only, design-marker-preserving, and free of API/network/build/product scope drift.

## Required Coverage

Add evals whose names include `pet_room_canvas` or `canvas_module`, for example:

- `pet_room_canvas_module_file_present`
- `pet_room_canvas_module_index_wired`
- `pet_room_canvas_markers_preserved`
- `pet_room_canvas_read_only_no_api_or_fetch`
- `pet_room_canvas_no_external_or_scope_drift`

Coverage should verify:

1. `mini_agent/static/components/pet-room-canvas.js` exists after TASK-183A and uses native JS exports.
2. `index.html` wires the component through a local native module import.
3. Required design markers and local hero asset remain present:
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
   - `/static/nora-01-hero.jpg`
4. The canvas module is visual/read-only:
   - no `fetch(`
   - no `PetAPI`
   - no `/pet/` endpoint literals
   - no mutation endpoint calls
   - no voice preview, food mutation, relationship memory write, identity save, skill/tool/plugin execution.
5. TASK-180/TASK-181/TASK-182 evals remain active/pass.
6. No build-system drift: no React/Vite/TypeScript/npm/package.json/Webpack/Rollup/bundler/import-map dependency is added.
7. No product scope drift: no marketplace/plugin store/premium skills, voice cloning, recording/background listening, microphone/camera/screen/location access, PWA/service-worker/notification/native drift, or 3D/VRM/Live2D implementation drift.

Guard evals so they explain missing TASK-183A behavior during isolated worker runs, but after PM combines with TASK-183A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `mini_agent/static/components/pet-room-canvas.js`
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

Do not implement UI/JS component behavior, create frontend modules yourself beyond tests/evals, add Playwright dependencies, add a frontend build system, or add real voice/native/PWA/billing/marketplace/skill execution/3D/Live2D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-183B`.
