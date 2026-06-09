# TASK-179B: Skill ability shelf deterministic eval and safety coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Phase 2 is in progress. TASK-179A will add a deterministic read-only skill ability shelf to the Pet Room. Your job is deterministic eval/smoke/safety coverage only. Phase 2 still uses A/B only; do not open or assume Claude C/D.

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

Add deterministic coverage for the Pet Room skill ability shelf that TASK-179A implements. Coverage should lock the public contract without implementing the UI yourself.

Expected coverage areas:

- Pet Room exposes stable skill shelf DOM markers/attributes.
- Rendering derives from bounded `identity.skills` only.
- Missing, empty, malformed, secret-like, HTML, or excessive skill inputs fall back safely or escape/bound output.
- Skill shelf update is read-only: no fetch, provider/model call, tool execution, plugin install, durable task creation, food debit, state mutation, activity write, relationship-memory write, voice-preview call, microphone/camera/screen/location access, service worker, desktop/native code, or notification setup.
- UI copy does not imply marketplace/plugin store, premium skill packs, purchase pressure, hidden cost, voice cloning, recording by default, always listening, notification opt-in, PWA install, or 3D/VRM scope drift.

## Scope

Allowed files:

- `evals/run_evals.py`
- `tests/test_webui_smoke.py` only if adding narrowly targeted smoke tests
- `agent_tasks/B_DONE.md`

Do not edit implementation files:

- `mini_agent/static/index.html`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/tts.py`
- skill/plugin/runtime/capability-router files

## Required Coverage

Add evals whose names include `skill_shelf` or `pet_skill`, for example:

- `pet_skill_shelf_markers_present`
- `skill_shelf_mapping_rules`
- `skill_shelf_read_only_no_tool_execution`
- `skill_shelf_no_marketplace_native_pwa_or_surveillance_copy`

Guard evals so they can explain missing TASK-179A behavior during isolated worker runs, but after PM combines with TASK-179A they must be active/pass and not permanently skipped.

## Non-Goals

- Do not implement the skill shelf UI, CSS, or JS helper.
- Do not add real skill execution, plugin installation, marketplace, billing, payment, PWA/service worker, notifications, desktop floating pet, real TTS/audio, speech recognition, microphone/camera/screen/location access, relationship-memory writes, activity writes, or 3D/VRM.
- Do not weaken existing pet, voice profile, TTS fallback, speech bubble, voice consent, expression state, presence state, room greeting, interaction reaction, identity editor, commercial/no-manipulation, or Web UI smoke coverage.
- Do not add new Claude C/D worker files.

## Safety Boundaries

- Eval scans may allow negative boundary statements, but must block enabling/promotional language for:
  - plugin store / marketplace / premium skills
  - tool execution from the shelf
  - hidden cost / surprise food debit
  - subscription or purchase pressure
  - voice cloning
  - recording by default
  - microphone/camera/screen/location access
  - always/background listening
  - PWA/service-worker/notification/native drift
  - 3D/VRM implementation drift
- Tests must not assert only that files exist; they must lock markers, mapping behavior, read-only/no-tool/no-mutation behavior, escaping/bounding, or copy contracts.
- Do not include real secrets or credentials in fixtures.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_webui_smoke tests.test_http_server
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|always listening|checkout now|subscribe now|marketplace|plugin store|premium skill|real payment|audio_url|audio bytes|microphone|mic access|camera access|screen capture|location access|3d model|vrm|live2d|service worker|notification permission|install plugin" evals/run_evals.py tests/test_webui_smoke.py
```

The `rg` command may find negative test/safety assertions only; explain any hits in `B_DONE.md`.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-179B` and include:

- Summary of eval/test coverage
- Eval names added
- Exact command results
- Any coordination notes for Claude A / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
