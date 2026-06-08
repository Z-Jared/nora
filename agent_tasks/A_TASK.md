# TASK-167: Phase 1 MVP release audit

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora is now in Phase 1 Exit Gate after Identity Editor landed. Your job is to audit whether Phase 1 Pet Life MVP can be considered release-ready as a local customizable electronic pet agent.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `mini_agent/static/index.html`
- README or any relevant demo docs if present

## Goal

Perform a Phase 1 MVP release audit.

Verify the first-use pet loop:

1. Open or inspect Pet Room and confirm Nora-01/current pet, state, token food, activity, and memory surfaces are visible.
2. Confirm Identity Editor can edit name, species, relationship role, speech style, personality traits, skills, voice profile, and taste profile.
3. Confirm compute food add/feed/status paths show transparent balance and estimates.
4. Confirm care/feed/relationship memory paths create visible state, activity, or memory feedback.
5. Confirm user-visible copy has no fake intimacy, guilt, loneliness pressure, hidden purchase pressure, marketplace pressure, or voice-cloning claims.

## Allowed Changes

- `agent_tasks/A_DONE.md`
- Optional small audit document, such as `docs/knowledge/PHASE_1_MVP_RELEASE_AUDIT.md`
- Minimal README/demo documentation if the Phase 1 local MVP path is missing

## Non-Goals

- Do not implement Phase 2 voice or presence features.
- Do not implement 3D/VRM, real payments, marketplace, account sync, native desktop, or native mobile.
- Do not modify product/runtime code unless you find a tiny documentation/test naming issue; report real product blockers in `A_DONE.md`.

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

If full evals fail because of unrelated baseline state, report exact failures and still run targeted tests.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-167` and include:

- Whether the first-use flow passed
- Whether Phase 1 can be sealed or which blockers remain
- Whether PM should proceed to `TASK-168`
- Exact command results

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
