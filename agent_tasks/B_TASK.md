# TASK-180B: Pencil design restoration deterministic smoke and safety coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 50% complete. TASK-180A will create a durable Pencil-to-frontend restoration contract and first-pass UI implementation. Your job is coverage only.

Design source:

- `/Users/mac/Documents/agent/designs/nora_pet_web_ui.pen`
- Selected node: `P7UnVG` — `Room canvas`
- Reference export: `/Users/mac/Documents/agent/.nora_design_exports/nora_pet_web_ui_screen.png`

Important design facts to lock:

- Room canvas: 880 x 850, `#F5F3EE`, stroke `#D8D1C8`, radius 12.
- Wall/floor colors: `#F1EEE7` and `#DDD5CA`.
- Hero asset: `designs/images/generated-1780975241297.png` or a controlled local static copy.
- Name/role: `Nora-01`, `ceramic desktop pet agent`.
- Status chip labels: Mood, Presence, Energy, Bond.
- New implementation markers expected from TASK-180A:
  - `pet-room-design-shell`
  - `pet-room-canvas`
  - `pet-room-hero-image`
  - `pet-room-status-chip`

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `evals/run_evals.py`
- `tests/test_webui_smoke.py`

## Goal

Add deterministic coverage so the Pencil UI restoration does not drift away from the design source or product safety boundaries.

## Required Coverage

Add evals whose names include `pencil_design` or `pet_room_design`, for example:

- `pencil_design_contract_present`
- `pet_room_design_markers_present`
- `pet_room_design_tokens_match_pencil`
- `pet_room_design_local_asset_only`
- `pet_room_design_no_scope_drift_copy`

Coverage should verify:

1. `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md` exists and references:
   - `designs/nora_pet_web_ui.pen`
   - `Room canvas`
   - `880 x 850`
   - the key colors above
   - the hero asset
   - the required markers
2. Web UI contains the required design markers.
3. Web UI contains key local design tokens/colors from Pencil.
4. Hero image is local or repo-controlled, with no external `http://` or `https://` image source introduced for the pet hero.
5. Existing core Pet Room markers remain present: food, identity, speech bubble/consent, expression/presence, greeting/reaction, skill shelf, diary/memory/actions.
6. No copy or code implies marketplace/plugin store/premium skills, purchase pressure, voice cloning, recording/background listening, microphone/camera/screen/location access, PWA/service-worker/notification/native drift, or 3D/VRM implementation drift.

Guard evals so they explain missing TASK-180A behavior during isolated worker runs, but after PM combines with TASK-180A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`
- `designs/` or `.nora_design_exports/`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files
- worker configuration or Claude C/D files

## Non-Goals

Do not implement UI/CSS/JS, generate images, edit Pencil, run real browser automation unless already available and strictly read-only, add Playwright dependencies, or add real voice/native/PWA/billing/marketplace/skill execution/3D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-180B`.
