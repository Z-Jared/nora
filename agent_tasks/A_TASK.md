# TASK-189A: Pet Room first-screen pet-first experience

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 75% complete. The user reported that the Web UI still does not make the pet obvious: "哪里有宠物". Recent TASK-181 through TASK-188 extracted Pet Room internals into native modules, but the next slice must be visible product experience, not another invisible refactor.

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
- `mini_agent/static/index.html`
- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`
- `mini_agent/static/components/voice-preview.js`
- `mini_agent/static/components/memory-diary.js`
- `tests/test_webui_smoke.py`

## Goal

Make the Web UI initial viewport unmistakably pet-first. When the page opens, the user should immediately see Nora-01 and the Pet Room as the primary experience, with status, food, interaction, speech, and diary/memory entry points visible or clearly attached to the pet room.

## Required Work

1. Adjust the smallest Web UI/CSS boundary needed so the Pet Room is the dominant first-screen surface.
   - Nora-01 / `pet-room-hero-image` and `pet-room-canvas` must be visually central or first.
   - `pet-room-name`, `pet-room-role`, status chips, food/status panel, interaction controls, speech bubble, and Today diary / memory entry should be in the first Pet Room path.
   - Do not make the page feel like an Agent OS dashboard, ordinary chatbot, or tools table.
   - Keep cards restrained; do not add marketing hero copy, decorative blobs, or dashboard tables.

2. Preserve existing behavior and module boundaries.
   - Keep current Pet Room API calls delegated through `PetAPI` and native modules.
   - Keep all existing DOM IDs/classes/markers that current tests/evals rely on.
   - Keep `renderPet()`, `petAction()`, `showRoomNotice()`, `applyReaction()`, `wireVoicePreview()`, and `wireMemoryDiary()` behavior intact.
   - Do not change endpoint request or response shapes.

3. Add or adjust focused smoke tests only where needed.
   - Lock that the first-screen Pet Room markers exist in the main initial UI.
   - Lock that Nora-01 local image, room canvas, status chips, food, actions, speech, and diary/memory markers are not removed.
   - Lock no external hero URL, no direct pet endpoint fetch drift, no build-system markers, and no product scope drift.

## Allowed Files

- `mini_agent/static/index.html`
- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/static/api.js`
- `mini_agent/static/components/*.js`
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
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\('/pet|fetch\\(\\\"/pet|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" mini_agent/static/index.html mini_agent/static/styles/tokens.css mini_agent/static/styles/pet-room.css tests/test_webui_smoke.py
```

Document expected hits from existing negative test assertions or non-pet legacy UI. The changed Pet Room first-screen surface must not contain external image URLs, direct pet endpoint fetches, build-system markers, audio/recording/payment/marketplace/provider-activation, PWA/native, or 3D scope-drift markers.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-189A`.
