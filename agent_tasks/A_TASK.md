# TASK-168: Phase 1.5 Pet Room life-feel polish

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora is now in Phase 1 Exit Gate. TASK-167 release audit is integrated and reviewer-approved, but Phase 1 cannot move to Phase 2 until the remaining Exit Gate tasks are complete. Your job is to make the existing Pet Room feel more like a living electronic pet surface through deterministic UI/state feedback, without starting Phase 2 voice/presence work.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_1_MVP_RELEASE_AUDIT.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `tests/test_pets.py`
- `tests/test_http_server.py`

## Goal

Polish the Phase 1 Pet Room life-feel while staying deterministic and local.

Implement a narrow vertical slice that improves at least three of these:

1. A clearer pet mood/status summary that reads from deterministic `hunger`, `energy`, `mood`, `bond`, and `growth` state.
2. More visible feedback after Feed/Care/Shared Moment actions, such as a bounded room notice or diary-style latest activity surface.
3. Identity-driven presentation, for example showing relationship role, speech style, taste profile, or skills in the room without requiring the editor to be open.
4. A small "pet diary" or "today with Nora" surface derived from existing activity/memory data.
5. Better first-use empty states that explain local demo boundaries without purchase pressure.

The result should help a first-time user feel "this is my configurable electronic pet" rather than "this is a form/dashboard".

## Scope

Allowed files:

- `mini_agent/static/index.html`
- `tests/test_webui_smoke.py`
- `tests/test_pets.py` or `tests/test_http_server.py` only if you add a tiny deterministic API/state helper that is directly required
- `agent_tasks/A_DONE.md`

Keep changes small and product-facing.

## Non-Goals

- Do not implement real voice, TTS, speech recognition, desktop presence, mobile/PWA, 3D/VRM, Live2D asset pipeline, real billing, marketplace, account sync, or cloud sync.
- Do not redesign the whole Web UI or return to Agent OS dashboard work.
- Do not add model calls. All pet state and room feedback must be deterministic.
- Do not edit `agent_tasks/B_TASK.md`, `agent_tasks/B_DONE.md`, `agent_tasks/REVIEW.md`, `CODEX_TERMINAL_HANDOFF.md`, `designs/`, or untracked design exports.

## Safety Boundaries

- Escape all dynamic text before rendering.
- Do not add fake intimacy, guilt, loneliness pressure, suffering/death language, hidden purchase pressure, marketplace pressure, or voice-cloning claims.
- Do not make compute food feel like a coercive payment gate; keep local demo boundaries transparent.
- Do not let model output directly mutate pet state.
- Keep token food cost language precise and bounded.

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

If full evals fail because of unrelated baseline state, report exact failures and still run targeted tests.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-168` and include:

- What life-feel surfaces changed
- How the result remains deterministic and Phase-1-only
- Exact command results
- Any remaining blockers or UX gaps

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
