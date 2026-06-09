# TASK-179A: Pet Room deterministic skill ability shelf

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Phase 2 is in progress. Voice Profile v1, text-only TTS fallback, speech bubble preview, consent/cost boundary, CSS-only expression/presence states, room-load greeting, and deterministic interaction reactions are integrated. The next bounded step is to make Nora-01's skills feel like visible pet abilities without executing any tools.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`

## Goal

Add a deterministic read-only Pet Room skill ability shelf. It should display `identity.skills` as Nora-01 abilities/equipment in the Pet Room so the user can understand what the pet can help with, without running tools or creating tasks.

Suggested implementation shape:

- Add stable DOM markers in the Pet Room:
  - `pet-skill-shelf`
  - `pet-skill-list`
  - `pet-skill-empty`
  - `pet-skill-card`
  - `data-skill-count` on the shelf root
- Add a helper such as `skillCardsFromIdentity(identity, state)` or `renderSkillShelf(identity, state)`.
- Render only bounded skill names/labels/meta. Unknown/malformed/empty skills should fall back to a safe empty state.
- Use DOM text APIs or existing escaping helpers for all dynamic text.
- Keep rendering read-only: no fetch, no provider/model calls, no tool calls, no plugin install, no durable task creation, no food debit, no activity write, no relationship-memory write.

## Scope

Allowed files:

- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `agent_tasks/A_DONE.md`

Do not modify:

- `evals/run_evals.py` (Claude B owns eval coverage)
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files
- payment/billing/provider/native desktop/PWA/service-worker files
- worker configuration or Claude C/D files

## Required Behavior

- Text/DOM-only and deterministic; no LLM calls and no provider/network calls.
- Skill shelf must derive only from `currentPet.identity.skills` and bounded state already available in the UI.
- Must not execute skills/tools/plugins or imply that clicking a skill runs anything.
- Pet Room still renders safely when skills are missing, not an array, contain non-string values, secret-like text, HTML, or excessive length.
- Existing room greeting, reaction, expression, presence, speech bubble, voice consent, identity editor, and food status behavior must continue to pass.

## Non-Goals

- Do not add or change HTTP endpoints.
- Do not implement real skill execution, plugin installation, marketplace, billing, payment, PWA/service worker, desktop floating pet, notifications, 3D/VRM, real TTS/audio playback, speech recognition, microphone/camera/screen/location access, extra relationship memory write, extra activity write, or Claude C/D worker setup.
- Do not add promotional plugin packs, marketplace, premium skills, voice cloning, recording by default, always/background listening, hidden costs, purchase pressure, surveillance, notification, PWA, or 3D/VRM copy.

## Verification

Run:

```bash
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" mini_agent/static/index.html tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-179A` and include:

- Summary of skill shelf rendering changes
- Public DOM markers/classes/attributes added
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
