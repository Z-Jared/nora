# TASK-187A: Extract Pet Room Voice Preview native module

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is 68% complete. TASK-186 extracted the Pet Room skill shelf into `mini_agent/static/components/skill-shelf.js`. The next frontend architecture slice is Step 4 in:

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
- `mini_agent/static/api.js`
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`
- `tests/test_webui_smoke.py`

## Goal

Create `mini_agent/static/components/voice-preview.js` and move the Pet Room text-only voice preview UI wiring out of `index.html` into a bounded native ES module without changing consent-before-call behavior, request shape, metadata rendering, DOM markers, or read-only safety boundaries.

## Required Work

1. Create `mini_agent/static/components/voice-preview.js`.
   - Use native browser JavaScript only.
   - Export a small API for voice preview UI wiring/rendering.
   - Preserve the current behavior for:
     - `voice-consent-checkbox` checked before any preview API call.
     - Empty text error: `Enter text to preview.`
     - Over-500 text error: `Text too long (max 500).`
     - Preview request body: `{pet_id: currentPet.pet_id, text: text}`.
     - Text rendering into `speech-bubble-text`.
     - Meta tags for cost, audio text-only status, no network, no recording, no food debit, provider status, and audio confirmation.
     - Auth error delegation to existing `handleAuthError({status:401})`.
     - Generic preview failure copy: `Preview failed.`
   - The module may own these markers/classes only:
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
     - `meta-tag`
     - `visible`
   - Dynamic preview text must use DOM text APIs.
   - Dynamic meta HTML must use `escapeHtml` or DOM text APIs.

2. Update the smallest implementation boundary in `index.html`.
   - Import the voice preview functions from `/static/components/voice-preview.js`.
   - Replace the inline `speech-preview-btn` click handler with a bounded module wiring call.
   - Keep Pet Room API calls delegated through existing `PetAPI.previewVoice` or an injected API object/function.
   - Preserve existing DOM IDs/classes/markers and user-visible copy.
   - Do not route voice preview through food panel, skill shelf, relationship memory, tool/plugin/runtime code, or new endpoints.

3. Add or adjust focused smoke tests only where needed.
   - Lock that `voice-preview.js` exists and is locally wired.
   - Lock expected exports.
   - Lock no direct fetch/no direct endpoint literal/no external URL/no build-system markers.
   - Lock consent-before-call, empty/overlong validation, metadata rendering, and auth failure behavior still work.

## Allowed Files

- `mini_agent/static/components/voice-preview.js`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

## Do Not Modify

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/static/api.js`
- `mini_agent/static/components/pet-room-canvas.js`
- `mini_agent/static/components/status-chips.js`
- `mini_agent/static/components/food-panel.js`
- `mini_agent/static/components/skill-shelf.js`
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
rg -n "https?://|react|vite|typescript|npm install|package.json|webpack|rollup|fetch\\(|/pet/voice-preview|tool_call|execute_tool|run_tool|install plugin|plugin store|marketplace|premium skill|checkout now|subscribe now|real payment|purchase tokens|voice clone|clone voice|record by default|background listening|always listening|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission" mini_agent/static/index.html mini_agent/static/components/voice-preview.js tests/test_webui_smoke.py
```

The scan may hit existing negative test assertions or `api.js` wrapper references outside this file set. `voice-preview.js` itself must not contain direct `fetch(`, direct `/pet/voice-preview`, external URLs, build tooling, audio/recording/payment/marketplace/provider-activation, PWA/native, or 3D scope-drift markers. Document expected hits.

## Completion Report

Write `agent_tasks/A_DONE.md` using the standard format. Explicitly mention `TASK-187A`.
