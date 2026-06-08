# TASK-159: Nora-01 robot default identity and living Pet Room redesign

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora has pivoted to a customizable electronic pet agent. TASK-157/158 added the first local Pet Room HTTP/API MVP in commit `93e495c`, but the current default pet is still `Nora / digital_cat`. Product direction now requires the default example character to be a robot electronic pet, not a fox/cat and not a generic dashboard mascot.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Make the default visible pet identity and Pet Room experience match the new product direction: a robot electronic lifeform named `Nora-01`.

Required behavior:

1. Default pet identity:
   - `GET /pet/current` must create a default pet named `Nora-01` when no pet exists.
   - Default species should be robot/electronic-life oriented, for example `robot_pet` or `electronic_robot`.
   - Default identity should include bounded personality, relationship role, speech style, taste profile, voice profile, and skills that fit a customizable robot companion.
   - Keep user-created custom identities fully supported.

2. Pet Room visual redesign:
   - The first visible Pet Room should feel like a living electronic pet room, not a dashboard.
   - Use a modular 2D HTML/CSS robot avatar placeholder. It should clearly read as robot/electronic pet without relying on a fox/cat visual.
   - Show identity, hunger/energy/mood/bond/growth, compute food balance, and transparent food consumption.
   - Keep actions: feed, pat, rest/play or comfort, add local demo food.
   - Show recent activity/diary as the pet's life log.
   - Keep chat/task/memory views usable but secondary.
   - Mobile and desktop must not have overlapping text, clipped controls, or layout shift.

3. Copy and commercial boundary:
   - Food should be framed as compute food/token energy with transparent balance/estimated spend.
   - Do not add manipulative payment copy or pet distress pressure.
   - Do not implement real billing or purchase flows.

## Non-Goals

- No Live2D/3D rigging.
- No voice system.
- No real payment provider.
- No desktop/mobile native app.
- No LLM-driven pet state mutation.
- No marketplace or plugin pack UI.

## Safety Boundaries

- All pet state mutations must continue to use `PetStore`.
- Mutation endpoints must keep existing HTTP auth behavior when `NORA_API_TOKEN` is set.
- Default identity must not contain secret-like text.
- UI/API output must remain bounded and no-leak.
- Do not touch unrelated CLI/TUI code.

## Scope

Primary files:

- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py` only for focused implementation-adjacent coverage
- `tests/test_webui_smoke.py` only for focused implementation-adjacent coverage
- `agent_tasks/A_DONE.md`

Do not edit:

- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

If full evals fail because of pre-existing unrelated state, report the exact failure and still run the targeted API/UI tests.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-160 needs to adjust tests for your public contract.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
