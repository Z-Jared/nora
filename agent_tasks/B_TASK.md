# TASK-181B: Design token and CSS module deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 55% complete. TASK-180A/B restored the Pet Room from Pencil. TASK-181A will extract design tokens and Pet Room CSS modules without changing DOM, JS behavior, or APIs.

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

## Goal

Add deterministic coverage for TASK-181A so extracted token/CSS files remain wired, local, no-build, and contract-preserving.

## Required Coverage

Add evals whose names include `design_tokens` or `pet_room_css`, for example:

- `design_tokens_files_present`
- `design_tokens_match_pencil_contract`
- `pet_room_css_module_wired`
- `pet_room_css_preserves_markers`
- `pet_room_css_no_build_or_scope_drift`

Coverage should verify:

1. `mini_agent/static/styles/tokens.css` exists and contains stable variables for:
   - `#F5F3EE`, `#D8D1C8`, `#F1EEE7`, `#DDD5CA`, `#B9AA993D`;
   - `#F6DDC6`, `#DDE6DC`, `#ECE3D6`, `#E8DED4`;
   - room radius, name/role/chip typography, and warm action color.
2. `mini_agent/static/styles/pet-room.css` exists and owns the Pet Room selectors:
   - `.pet-room-design-shell`
   - `.pet-room-canvas`
   - `.pet-room-hero-image`
   - `.pet-room-status-chip`
   - `.pet-actions`
3. `mini_agent/static/index.html` links both stylesheets with local `/static/styles/...` paths.
4. Pencil design evals from TASK-180 remain active/pass; do not weaken them.
5. Existing core Pet Room markers remain present: food, identity, speech bubble/consent, expression/presence, greeting/reaction, skill shelf, diary/memory/actions.
6. No build-system drift: no React/Vite/TypeScript/npm/package.json/bundler/import-map dependency is added.
7. No product scope drift: no marketplace/plugin store/premium skills, voice cloning, recording/background listening, microphone/camera/screen/location access, PWA/service-worker/notification/native drift, or 3D/VRM implementation drift.

Guard evals so they explain missing TASK-181A behavior during isolated worker runs, but after PM combines with TASK-181A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`
- `mini_agent/static/nora-01-hero.jpg`
- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`
- `designs/` or `.nora_design_exports/`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files
- worker configuration or Claude C/D files

## Non-Goals

Do not implement UI/CSS/JS, create tokens yourself, add Playwright dependencies, add a frontend build system, or add real voice/native/PWA/billing/marketplace/skill execution/3D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin|react|vite|typescript|npm install|package.json|webpack|rollup" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-181B`.

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-180B`.
