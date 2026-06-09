# TASK-187B: Voice Preview module deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is 68% complete. TASK-186 extracted `mini_agent/static/components/skill-shelf.js`. TASK-187A will extract the Pet Room text-only voice preview UI into `mini_agent/static/components/voice-preview.js`.

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
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`

## Goal

Add deterministic coverage for TASK-187A so the Voice Preview module remains local, native-module-only, consent-gated, API-delegated, text-only, escaping-safe, no-build, and free of real audio/recording/provider/payment/native/PWA/3D drift.

## Required Coverage

Add evals whose names include `voice_preview_module`, for example:

- `voice_preview_module_file_present`
- `voice_preview_module_wired`
- `voice_preview_module_markers_preserved`
- `voice_preview_module_delegated_api_boundary`
- `voice_preview_module_consent_validation_and_escaping`
- `voice_preview_module_no_audio_or_scope_drift`

Coverage should verify:

1. `mini_agent/static/components/voice-preview.js` exists after TASK-187A and uses native JS exports.
2. `index.html` wires the component through a local native module import.
3. Required markers/classes remain present:
   - `speech-bubble-area`
   - `voice-consent-panel`
   - `voice-consent-checkbox`
   - `voice-consent-boundary`
   - `voice-consent-cost`
   - `voice-consent-provider`
   - `speech-bubble`
   - `speech-bubble-text`
   - `speech-bubble-meta`
   - `speech-preview-input`
   - `speech-preview-btn`
   - `speech-bubble-error`
4. Module preserves consent-before-call and does not call preview API when unchecked.
5. Module preserves empty text and over-500 text validation.
6. Module uses DOM text APIs or escaping for preview text and meta tags.
7. Module uses delegated API boundary: no direct `fetch(` and no direct `/pet/voice-preview` endpoint literal in `voice-preview.js`; it should accept an API object/function or call injected `api.previewVoice`.
8. Existing speech bubble and voice consent evals remain active/pass after extraction. If old evals only scan `index.html`, update them to scan combined `index.html` + `voice-preview.js` surface while preserving the original assertions.
9. No build-system drift: no React/Vite/TypeScript/npm/package.json/Webpack/Rollup/bundler/import-map dependency is added.
10. No product scope drift: no audio_url/audio bytes, real recording/background listening, voice cloning, microphone/camera/screen/location access, checkout/billing/real payment, provider activation, marketplace/plugin store/premium skill, PWA/service-worker/notification/native drift, or 3D/VRM/Live2D implementation drift.

Guard evals so they explain missing TASK-187A behavior during isolated worker runs, but after PM combines with TASK-187A they must be active/pass and not permanently skipped.

## Allowed Files

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted tests
- `agent_tasks/B_DONE.md`

## Do Not Modify

- `mini_agent/static/index.html`
- `mini_agent/static/components/voice-preview.js`
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`
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

Do not implement UI/JS component behavior, create frontend modules yourself beyond tests/evals, add Playwright dependencies, add a frontend build system, or add real TTS/provider/audio/recording/payment/native/PWA/marketplace/3D/Live2D behavior.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|/pet/voice-preview|tool_call|execute_tool|run_tool|install plugin|plugin store|marketplace|premium skill|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" evals/run_evals.py tests/test_webui_smoke.py
```

## Completion Report

Write `agent_tasks/B_DONE.md` using the standard format. Explicitly mention `TASK-187B`.
