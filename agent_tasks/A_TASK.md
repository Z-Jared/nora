# TASK-180A: Pencil Pet Room design restoration contract and first-pass UI implementation

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 50% complete. The user explicitly wants to redesign the UI through Pencil first, and the current active Pencil design is:

- `/Users/mac/Documents/agent/designs/nora_pet_web_ui.pen`
- Selected node: `P7UnVG` — `Room canvas`
- Reference export: `/Users/mac/Documents/agent/.nora_design_exports/nora_pet_web_ui_screen.png`

Current Pencil structure for `Room canvas`:

- Frame: 880 x 850, fill `#F5F3EE`, stroke `#D8D1C8`, radius 12, outer shadow.
- Back wall: `#F1EEE7`, 880 x 550, radius top 12.
- Soft floor: `#DDD5CA`, 880 x 300, y=550, radius bottom 12.
- Pet ground shadow: ellipse `#B9AA993D`, 390 x 56, x=244, y=654.
- Hero image: `designs/images/generated-1780975241297.png`, 410 x 530, x=235, y=122.
- Name: `Nora-01`, Inter 40/800, centered, x=276, y=720, width 328.
- Role: `ceramic desktop pet agent`, Inter 15/600, centered, x=255, y=768, width 370.
- Chips:
  - Mood chip: `#F6DDC6`, x=92, y=78, 150 x 54, text `Mood` / `focused`.
  - Presence chip: `#DDE6DC`, x=610, y=116, 150 x 54, text `Presence` / `waiting with you`.
  - Energy chip: `#ECE3D6`, x=104, y=500, 150 x 54, text `Energy` / `72`.
  - Bond chip: `#E8DED4`, x=632, y=502, 150 x 54, text `Bond` / `41`.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `designs/nora_pet_web_ui.pen`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`

## Goal

Create a durable front-end restoration contract from the Pencil room design, then apply a first-pass Pet Room UI restoration in `mini_agent/static/index.html` without losing current functional pet data.

The user problem to solve is: “Pencil design exists, but frontend restore is not close enough.” Your task is to make the design source explicit and implement the first front-end slice against that source.

## Required Work

1. Create or update `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`.
   - Treat `designs/nora_pet_web_ui.pen` `Room canvas` as the source of truth.
   - Record dimensions, key colors, typography, image asset, status chip layout, and allowed responsive adaptations.
   - Include clear implementation markers and a short restore checklist for future workers.

2. Update `mini_agent/static/index.html` Pet Room surface.
   - Add stable markers:
     - `pet-room-design-shell`
     - `pet-room-canvas`
     - `pet-room-hero-image`
     - `pet-room-status-chip`
   - Use the ceramic Nora-01 image asset from the repo, preferably by copying or referencing a controlled local static path. Do not use external image URLs.
   - Bring the visual structure closer to Pencil: warm canvas, wall/floor bands, centered ceramic hero, status chips around the pet, name/role below.
   - Preserve existing Pet Room functions: identity editor, food/status, speech bubble, consent panel, expression/presence, greeting, reaction, skill shelf, diary/memory/actions.
   - Keep dynamic state and labels deterministic and safely rendered.

3. Add focused smoke tests in `tests/test_webui_smoke.py` if needed.
   - Lock the new design markers.
   - Lock asset path/local-only behavior.
   - Lock that existing core markers still exist.

## Allowed Files

- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- local static asset copy only if needed under an existing static/assets path
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
- `designs/` or `.nora_design_exports/`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files
- worker configuration or Claude C/D files

## Non-Goals

Do not add or implement:

- Real voice/TTS/audio playback or recording
- Microphone, camera, screen, location access
- Desktop/native shell
- PWA/service worker/notification permission
- Billing/payment/marketplace/premium skill packs
- Real skill execution or plugin installation
- 3D/VRM/Live2D runtime
- New HTTP endpoints
- A full front-end rewrite

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin|https?://" mini_agent/static/index.html tests/test_webui_smoke.py docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md
```

The `https?://` scan may hit unrelated existing links only if they are already present; document any hits. Do not introduce external image URLs.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-180A`.
