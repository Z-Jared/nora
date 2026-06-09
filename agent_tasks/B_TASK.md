# TASK-185B: Food Panel module deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 64% complete. TASK-184 extracted `mini_agent/static/components/status-chips.js`. TASK-185A will extract the Compute Food / Token Energy panel into `mini_agent/static/components/food-panel.js`.

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
- `mini_agent/static/components/status-chips.js`

## Goal

Add deterministic coverage for TASK-185A so the Food Panel module remains local, native-module-only, PetAPI-boundary-preserving, marker-preserving, no-build, and free of payment/marketplace/manipulative-copy drift.

## Required Coverage

Add evals whose names include `food_panel` or `pet_room_food`, for example:

- `food_panel_module_file_present`
- `food_panel_module_wired`
- `food_panel_markers_preserved`
- `food_panel_petapi_boundary_no_direct_fetch`
- `food_panel_no_payment_or_scope_drift`

Coverage should verify:

1. `mini_agent/static/components/food-panel.js` exists after TASK-185A and uses native JS exports.
2. `index.html` wires the component through a local native module import.
3. Required food markers remain present:
   - `pet-food-section`
   - `pet-cost-table`
   - `pet-food-amount`
   - `pet-add-food-btn`
   - `pet-food-balance`
   - `pet-feed-btn`
   - `stat-food`
   - `bar-food`
4. Food module preserves the existing cost action set: `feed`, `chat`, `voice`, `work`.
5. Food module does not direct-fetch `/pet/` endpoints and preserves the `PetAPI` API boundary.
6. TASK-184 status chips evals remain active/pass.
7. No build-system drift: no React/Vite/TypeScript/npm/package.json/Webpack/Rollup/bundler/import-map dependency is added.
8. No product scope drift: no checkout/billing/real payment, marketplace/plugin store/premium skills, manipulative food copy, voice cloning, recording/background listening, microphone/camera/screen/location access, PWA/service-worker/notification/native drift, or 3D/VRM/Live2D implementation drift.

Guard evals so they explain missing TASK-185A behavior during isolated worker runs, but after PM combines with TASK-185A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `mini_agent/static/components/food-panel.js`
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

Do not implement UI/JS component behavior, create frontend modules yourself beyond tests/evals, add Playwright dependencies, add a frontend build system, or add real payment/native/PWA/billing/marketplace/skill execution/3D/Live2D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|purchase tokens|buy more food|top up to feed|your pet is starving|pet will die|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-185B`.
