# TASK-181A: Extract Pet Room design tokens and CSS modules

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 55% complete. TASK-180A/B restored the Pet Room from the Pencil design and established a durable front-end contract.

The next architecture step is documented in:

- `docs/knowledge/NORA_FRONTEND_ARCHITECTURE_PLAN.md`
- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`

TASK-181A is an implementation-only architecture extraction. Keep DOM and JS behavior stable while moving the Pencil/Pet Room design constants out of the single inline style block.

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

## Goal

Extract Pet Room design tokens and Pet Room CSS into native static CSS files without changing behavior, DOM markers, API calls, or requiring a build step.

This is the first step toward a maintainable front-end architecture while preserving the current local-first Python-served Web UI.

## Required Work

1. Create `mini_agent/static/styles/tokens.css`.
   - Define stable CSS custom properties for Pencil/Pet Room values:
     - canvas max width, room radius, wall/floor heights if useful;
     - `#F5F3EE`, `#D8D1C8`, `#F1EEE7`, `#DDD5CA`, `#B9AA993D`;
     - chip colors `#F6DDC6`, `#DDE6DC`, `#ECE3D6`, `#E8DED4`;
     - warm primary/action colors currently used by the Pet Room;
     - type scale for pet room name, role, chip label/value;
     - shadow/border/radius values used by the design shell.
   - Reference `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md` in a short file comment.

2. Create `mini_agent/static/styles/pet-room.css`.
   - Move the Pet Room CSS rules from `mini_agent/static/index.html` into this file.
   - Use variables from `tokens.css` for Pencil-derived values.
   - Keep selectors and DOM markers stable.
   - Keep non-Pet Room Web UI CSS in `index.html` for now unless a tiny shared variable is already appropriate.

3. Update `mini_agent/static/index.html`.
   - Add `<link rel="stylesheet" href="/static/styles/tokens.css">` and `<link rel="stylesheet" href="/static/styles/pet-room.css">`.
   - Remove only the CSS that is now owned by `pet-room.css`.
   - Do not change existing Pet Room DOM IDs/classes/markers.
   - Do not change JS behavior.

4. Add or adjust focused smoke tests only where needed.
   - Lock that both stylesheet links exist.
   - Lock that critical design markers still exist.
   - Lock that `renderPet()` still updates design markers.

## Allowed Files

- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
- `designs/` or `.nora_design_exports/`
- `mini_agent/static/nora-01-hero.jpg`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files
- worker configuration or Claude C/D files

## Non-Goals

Do not add or implement:

- React, Vite, TypeScript, Node build steps, npm packages, bundlers, or transpilers
- Real voice/TTS/audio playback or recording
- Microphone, camera, screen, location access
- Desktop/native shell
- PWA/service worker/notification permission
- Billing/payment/marketplace/premium skill packs
- Real skill execution or plugin installation
- 3D/VRM/Live2D runtime
- New HTTP endpoints
- New JS modules or API extraction; that is a later task

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin|https?://|react|vite|typescript|npm install|package.json" mini_agent/static/index.html mini_agent/static/styles tests/test_webui_smoke.py
```

The `https?://` scan may hit unrelated existing LLM setup links only if they are already present in `index.html`; document any hits. Do not introduce external image URLs.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-181A`.
