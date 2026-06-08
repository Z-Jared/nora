# TASK-170A: Phase 2 Voice & Presence product technical plan

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora is in the final Phase 1 Exit Gate. TASK-167, TASK-168, and TASK-169 are integrated and reviewer-approved. Phase 2 must not start until this planning task is reviewed, integrated, and `agent_tasks/PHASE_STATUS.md` is updated by Codex PM.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_1_MVP_RELEASE_AUDIT.md`
- `docs/knowledge/PHASE_1_COMMERCIAL_NO_MANIPULATION_AUDIT.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `mini_agent/pets.py`
- `mini_agent/server.py`
- `mini_agent/static/index.html`

## Goal

Draft the product and technical plan for Phase 2 Voice & Presence, focused on low-risk, consent-based next steps.

Create or update a small planning document:

- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`

Your section must cover:

1. Voice Profile v1 data contract: identity fields, tone/speech style, expression hints, no real voice cloning.
2. TTS adapter boundary: interface shape, local/demo fallback, no secrets in docs, no network implementation in Phase 1 exit gate.
3. Web/PWA presence path: what can be implemented first in Web UI without native desktop/mobile.
4. Desktop floating pet path: prototype boundaries and prerequisites, not implementation.
5. Task candidates for Phase 2 product implementation, split into small verifiable tasks.

## Scope

Allowed files:

- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/A_DONE.md`

Coordinate implicitly with Claude B by keeping your work product-focused. Claude B owns safety/eval/worker-scaling sections.

## Non-Goals

- Do not implement voice, TTS, speech recognition, desktop app, PWA, native mobile, 3D/VRM, billing, marketplace, or account sync.
- Do not edit source code, tests, evals, `BACKLOG.md`, `PHASE_STATUS.md`, `B_TASK.md`, `B_DONE.md`, or `REVIEW.md`.
- Do not add API keys, model credentials, vendor-specific secrets, or claims that Phase 2 features already exist.

## Safety Boundaries

- Voice cloning is excluded by default.
- Any TTS/voice action must require user consent, transparent cost estimate, no recording by default, and clear local demo fallback.
- Cross-device presence must not imply cloud sync or background tracking.
- Keep commercial language non-manipulative and consistent with TASK-169.

## Verification

Run:

```bash
git diff --check
rg -n "voice clone|clone voice|real payment|checkout now|subscribe now|marketplace" docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md
```

The `rg` command may find negative boundary statements only; explain any hits in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-170A` and include:

- Summary of the product/technical plan sections you wrote
- Phase 2 task candidates you proposed
- Exact command results
- Any coordination notes for Claude B / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
