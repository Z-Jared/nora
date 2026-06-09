# TASK-182B: API boundary deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 55% complete. TASK-181 extracted Pet Room design tokens and CSS modules. TASK-182A will extract existing Pet Room fetch calls into `mini_agent/static/api.js` without endpoint changes.

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

## Goal

Add deterministic coverage for TASK-182A so the new `api.js` boundary remains local, same-origin, no-build, endpoint-compatible, and Pet Room behavior-preserving.

## Required Coverage

Add evals whose names include `api_boundary` or `pet_room_api`, for example:

- `api_boundary_file_present`
- `pet_room_api_endpoints_preserved`
- `pet_room_api_auth_header_preserved`
- `pet_room_api_index_module_wired`
- `api_boundary_no_external_or_build_drift`

Coverage should verify:

1. `mini_agent/static/api.js` exists after TASK-182A and uses native JS only.
2. API wrapper preserves the current local endpoint paths:
   - `/pet/current`
   - `/pet/create`
   - `/pet/add-food`
   - `/pet/feed`
   - `/pet/care`
   - `/pet/activity`
   - `/pet/food-status`
   - `/pet/update-identity`
   - `/pet/relationship-memory`
   - `/pet/voice-preview`
3. Auth header behavior is preserved:
   - Existing `Authorization` / bearer behavior remains present.
   - API key/token values are not logged or rendered.
4. `index.html` wires `api.js` through a local native module path and does not introduce build tooling.
5. TASK-180/TASK-181 design markers, stylesheet links, local hero asset, and CSS/token evals remain active/pass.
6. No endpoint shape drift: no new `/pet/...` endpoint literals are introduced beyond the known set unless already pre-existing in docs/tests.
7. No build-system drift: no React/Vite/TypeScript/npm/package.json/Webpack/Rollup/bundler/import-map dependency is added.
8. No product scope drift: no marketplace/plugin store/premium skills, voice cloning, recording/background listening, microphone/camera/screen/location access, PWA/service-worker/notification/native drift, or 3D/VRM implementation drift.

Guard evals so they explain missing TASK-182A behavior during isolated worker runs, but after PM combines with TASK-182A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
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

Do not implement UI/JS API wrapper behavior, create frontend modules yourself beyond tests/evals, add Playwright dependencies, add a frontend build system, or add real voice/native/PWA/billing/marketplace/skill execution/3D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-182B`.
