# TASK-157: Pet room MVP and local HTTP pet API

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora has pivoted to a customizable electronic pet agent. TASK-155/156 landed the deterministic pet backend foundation in `4d239bb`. The next product step must make the pet visible and usable in the local Web app.

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

Build the first visible Pet Room MVP backed by deterministic local HTTP endpoints.

Required behavior:

1. HTTP API in `mini_agent/http_server.py`:
   - `GET /pet/current`: return the current/default pet if present; if none exists, create a default bounded pet and return it.
   - `POST /pet/create`: create a pet with identity fields supported by `PetStore.create_pet`.
   - `POST /pet/add-food`: add local demo compute food to a pet using `PetStore.add_food`.
   - `POST /pet/feed`: feed a pet using `PetStore.feed_pet`.
   - `POST /pet/care`: perform `pat`, `comfort`, `rest`, or `play`.
   - `GET /pet/activity?pet_id=...`: return recent activity events.
   - Add pet feature flag to `/status`.
   - Add concise docs entries to `/docs`.

2. Web UI in `mini_agent/static/index.html`:
   - Make the first viewport feel like a pet room, not an Agent OS dashboard.
   - Show a modular 2D placeholder avatar or pet body built with HTML/CSS.
   - Show pet name/species, hunger, energy, mood, bond, growth level, compute food balance.
   - Add actions: feed, pat, rest/play or comfort, add local demo food.
   - Show recent pet activity/diary.
   - Keep existing chat/task/memory functionality usable, but do not let it dominate the first screen.
   - Fit desktop and mobile without overlapping text or controls.

3. Use the existing `PetStore` as the only state mutation path. Do not duplicate pet state rules in JS.

## Product Constraints

- This is a local MVP room. It is acceptable to use a CSS/HTML 2D avatar placeholder.
- Do not implement Live2D, 3D, voice, billing provider, mobile native app, or model-driven state deltas.
- Do not add payment pressure copy. Food can be labeled as local demo compute food for this MVP.
- Keep API output bounded and no-leak.

## Safety Boundaries

- Mutation endpoints must require existing HTTP auth when `NORA_API_TOKEN` is set.
- `GET /pet/current` and `GET /pet/activity` must be read-safe except the explicit first default-pet creation behavior for `/pet/current`.
- Model output must not mutate pet state.
- Sensitive identity text must continue to be rejected by `PetStore`.

## Scope

Primary files:

- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py` only for focused API coverage needed by your implementation
- `agent_tasks/A_DONE.md`

Do not edit:

- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`

Avoid touching unrelated CLI/TUI code.

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

If full evals fail because of pre-existing unrelated state, report the exact failure and still run the targeted API/UI tests.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-158 needs to adjust tests for your API shape.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
