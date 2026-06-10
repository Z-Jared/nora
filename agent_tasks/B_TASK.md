# TASK-189B: First-screen pet experience deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 75% complete. TASK-189A will make the Web UI initial viewport unmistakably pet-first. Your job is to lock that public contract with deterministic smoke/eval coverage so the UI cannot regress back to dashboard-first, chatbot-first, or hidden-pet behavior.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `evals/run_evals.py`
- `tests/test_webui_smoke.py`
- `mini_agent/static/index.html`
- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`

## Goal

Add deterministic coverage whose names include `pet_first_screen` or `first_screen_pet`, proving that the Web UI first-screen path makes Nora-01 and the Pet Room the primary visible experience.

## Required Coverage

Add eval/smoke coverage for:

1. Pet-first required markers remain present:
   - `pet-room-design-shell`
   - `pet-room-canvas`
   - `pet-room-hero-image`
   - `pet-room-name`
   - `pet-room-role`
   - `pet-room-status-chip`
   - `pet-food-panel` or existing food/status markers
   - interaction/action controls
   - `speech-bubble-area`
   - `pet-today-content`
   - `pet-memory-list`
2. Local Nora-01 image remains local-only: `/static/nora-01-hero.jpg`, no external hero/image URL.
3. First-screen semantics do not hide Pet Room behind chat/task/runtime UI.
   - Check for expected first-screen class/structure introduced by TASK-189A.
   - Check no obvious `display:none` / hidden class on the Pet Room root.
4. Existing Pet Room modules remain wired:
   - `pet-room-canvas.js`
   - `food-panel.js`
   - `skill-shelf.js`
   - `voice-preview.js`
   - `memory-diary.js`
5. No build-system drift: no React/Vite/TypeScript/npm/package.json/Webpack/Rollup/bundler dependency.
6. No product scope drift: no real audio_url/audio bytes, recording/background listening, voice cloning, microphone/camera/screen/location access, checkout/billing/real payment, provider activation, marketplace/plugin store/premium skill, PWA/service-worker/notification/native drift, or 3D/VRM/Live2D implementation drift.

Guard evals so they explain missing TASK-189A behavior during isolated worker runs, but after PM combines with TASK-189A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`
- `mini_agent/static/components/*.js`
- `mini_agent/static/api.js`
- `mini_agent/static/nora-01-hero.jpg`
- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`
- `designs/` or `.nora_design_exports/`
- `mini_agent/http_server.py`
- `mini_agent/pets.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files
- worker configuration or Claude C/D files

## Non-Goals

Do not implement layout, create frontend modules, add Playwright dependencies, add a frontend build system, or add real TTS/provider/audio/recording/payment/native/PWA/marketplace/3D/Live2D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\('/pet|fetch\\(\\\"/pet|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-189B`.
