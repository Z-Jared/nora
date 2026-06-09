# TASK-186B: Skill Shelf module deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 66% complete. TASK-185 extracted `mini_agent/static/components/food-panel.js`. TASK-186A will extract the Pet Room skill ability shelf into `mini_agent/static/components/skill-shelf.js`.

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
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/components/food-panel.js`

## Goal

Add deterministic coverage for TASK-186A so the Skill Shelf module remains local, native-module-only, read-only, marker-preserving, secret-filtering, stale-cleanup-preserving, no-build, and free of real skill/tool/plugin/marketplace drift.

## Required Coverage

Add evals whose names include `skill_shelf_module` or `pet_skill_shelf_module`, for example:

- `skill_shelf_module_file_present`
- `skill_shelf_module_wired`
- `skill_shelf_module_markers_preserved`
- `skill_shelf_module_read_only_no_tool_execution`
- `skill_shelf_module_secret_filtering_and_stale_cleanup`
- `skill_shelf_module_no_marketplace_or_scope_drift`

Coverage should verify:

1. `mini_agent/static/components/skill-shelf.js` exists after TASK-186A and uses native JS exports.
2. `index.html` wires the component through a local native module import.
3. Required skill markers/classes remain present:
   - `pet-skill-shelf`
   - `pet-skill-list`
   - `pet-skill-empty`
   - `pet-skill-card`
   - `skill-icon`
   - `skill-name`
   - `data-skill-count`
4. Skill module preserves valid/unknown skill behavior and default icon behavior.
5. Skill module preserves filtering for non-string, empty, overlong, special-character, and secret-like skill labels.
6. Skill module preserves empty/malformed stale card cleanup.
7. Skill module is read-only: no `fetch(`, no `PetAPI`, no `petAction`, no `/pet/` endpoint, no tool execution, no plugin installation, no runtime/capability-router call.
8. TASK-185 food panel evals remain active/pass.
9. No build-system drift: no React/Vite/TypeScript/npm/package.json/Webpack/Rollup/bundler/import-map dependency is added.
10. No product scope drift: no checkout/billing/real payment, marketplace/plugin store/premium skills, voice cloning, recording/background listening, microphone/camera/screen/location access, PWA/service-worker/notification/native drift, or 3D/VRM/Live2D implementation drift.

Guard evals so they explain missing TASK-186A behavior during isolated worker runs, but after PM combines with TASK-186A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `mini_agent/static/components/skill-shelf.js`
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

Do not implement UI/JS component behavior, create frontend modules yourself beyond tests/evals, add Playwright dependencies, add a frontend build system, or add real skill/tool/plugin execution, payment/native/PWA/billing/marketplace/3D/Live2D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|PetAPI|petAction|tool_call|execute_tool|run_tool|install plugin|plugin store|marketplace|premium skill|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-186B`.
