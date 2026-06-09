# TASK-182A: Extract Pet Room API boundary into native api.js

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 55% complete. TASK-181 extracted Pet Room design tokens and CSS modules while preserving the Pencil-restored design. The next frontend architecture slice is Step 2 in:

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
- `tests/test_webui_smoke.py`
- `mini_agent/http_server.py`

## Goal

Create `mini_agent/static/api.js` and centralize current Pet Room fetch calls behind native ES module wrappers without changing server behavior, request/response shapes, auth behavior, DOM markers, or UI behavior.

## Required Work

1. Create `mini_agent/static/api.js`.
   - Use native browser JavaScript only.
   - Export wrappers for current local endpoints:
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
   - Keep wrappers same-origin only. Do not add any `http://` or `https://` URL.
   - Keep auth header behavior equivalent to current `api()` helper in `index.html`.
   - Keep JSON parsing/error behavior compatible with current UI expectations.

2. Update `mini_agent/static/index.html`.
   - Wire `api.js` with a native module approach.
   - Replace direct Pet Room fetch helper usage with the API wrapper.
   - Preserve all DOM IDs/classes/markers, including TASK-180/TASK-181 Pet Room design markers and stylesheet links.
   - Preserve all JS-visible behavior and user-facing copy.
   - Do not extract Pet Room components in this task.

3. Add or adjust focused smoke tests only where needed.
   - Lock that `api.js` is locally wired.
   - Lock that endpoint literals are not duplicated in a way that bypasses the wrapper, where practical.
   - Keep existing Pet Room and HTTP smoke tests passing.

## Allowed Files

- `mini_agent/static/api.js`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
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
- Pet Room component extraction
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
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" mini_agent/static/index.html mini_agent/static/api.js tests/test_webui_smoke.py
```

The `https?://` scan may hit unrelated existing LLM setup links in `index.html`; document any hits. Do not introduce external URLs.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-182A`.
