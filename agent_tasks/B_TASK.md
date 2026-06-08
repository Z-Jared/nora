# TASK-170B: Phase 2 safety, eval, and worker-scaling plan

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

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
- `evals/run_evals.py`
- `tests/test_webui_smoke.py`

## Goal

Draft the Phase 2 safety, eval, and worker-scaling plan for Voice & Presence.

Create or update the same planning document as Claude A:

- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`

Your section must cover:

1. Safety policy for voice/TTS/presence:
   - no voice cloning without explicit consent; default is no cloning
   - no recording by default
   - no hidden background listening
   - transparent cost estimate before voice/TTS actions
   - no emotional pressure, dependency, or purchase manipulation
2. Deterministic eval and test plan:
   - voice profile contract evals
   - no-secret/no-recording/no-cloning copy scans
   - Web/PWA presence smoke tests
   - cost transparency checks
3. Phase 2 worker scaling plan:
   - decide whether PM should keep A/B only or open Claude C/D
   - propose file boundaries and ownership for each worker
   - identify conflict risks and when not to add workers
4. Reviewer/PM approval criteria before switching `PHASE_STATUS.md` to Phase 2.

## Scope

Allowed files:

- `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`
- `agent_tasks/B_DONE.md`

Coordinate implicitly with Claude A by keeping your work safety/eval/scaling-focused. Claude A owns product/technical path sections.

## Non-Goals

- Do not implement voice, TTS, speech recognition, desktop app, PWA, native mobile, 3D/VRM, billing, marketplace, or account sync.
- Do not edit source code, tests, evals, `BACKLOG.md`, `PHASE_STATUS.md`, `A_TASK.md`, `A_DONE.md`, or `REVIEW.md`.
- Do not add API keys, model credentials, vendor-specific secrets, or claims that Phase 2 features already exist.

## Safety Boundaries

- Treat voice and presence as higher-risk surfaces.
- Keep all claims framed as plans, not shipped features.
- Preserve TASK-169 commercial/no-manipulation boundaries.
- Worker-scaling recommendations must avoid parallel edits to the same core files unless the plan first splits architecture boundaries.

## Verification

Run:

```bash
git diff --check
rg -n "voice clone|clone voice|record by default|background listening|checkout now|subscribe now|marketplace" docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md
```

The `rg` command may find negative boundary statements only; explain any hits in `B_DONE.md`.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-170B` and include:

- Summary of the safety/eval/scaling plan sections you wrote
- Your worker-scaling recommendation for Phase 2
- Exact command results
- Any coordination notes for Claude A / Codex PM

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
