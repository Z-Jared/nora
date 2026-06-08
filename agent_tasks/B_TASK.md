# TASK-158: Pet room API/UI deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Nora has pivoted to a customizable electronic pet agent. TASK-155/156 landed the deterministic pet backend foundation in `4d239bb`. Claude A owns TASK-157, which should add the local HTTP pet API and visible Pet Room MVP. Your job is to add deterministic coverage for that user-visible loop, or prepare focused tests/evals around the expected public API if TASK-157 is not present in your worktree yet.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `agent_tasks/A_TASK.md`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `evals/run_evals.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic offline coverage for the Pet Room API/UI loop.

Required coverage:

1. HTTP API:
   - `GET /pet/current` returns a bounded current/default pet.
   - `POST /pet/create` creates identity fields without leaking sensitive input.
   - `POST /pet/add-food` increases compute food balance.
   - `POST /pet/feed` spends balance, improves state, and never allows negative balance.
   - `POST /pet/care` updates mood/bond without consuming food.
   - `GET /pet/activity?pet_id=...` returns bounded recent events.
   - Mutation endpoints respect existing auth when `NORA_API_TOKEN` is configured.

2. Web UI smoke:
   - The page contains a Pet Room first-screen surface.
   - It renders avatar/body placeholder, state metrics, food balance, action buttons, and activity/diary area.
   - JS can load `/pet/current`, call feed/care/add-food, and update DOM state using mocked fetch.
   - UI output must not render raw secret-like text.

3. Evals:
   - Add deterministic evals to `evals/run_evals.py` for the API/UI loop if TASK-157 is present.
   - If TASK-157 is not present, add guarded evals or focused test scaffolding with explicit skip/dependency reporting.

## Scope

Primary files:

- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `evals/run_evals.py`
- `tests/test_pets.py` only if a small assertion is needed
- `agent_tasks/B_DONE.md`

Do not edit:

- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`

Avoid touching unrelated CLI/TUI code.

## Non-Goals

- No billing provider.
- No voice.
- No Live2D or 3D rigging.
- No native desktop/mobile app.
- No LLM calls.
- No model-driven pet state mutation.
- No feature implementation except tiny testability fixes directly required by observed failures.

## Safety Boundaries

- Tests/evals must prove model/chat output cannot directly mutate pet state.
- Tests/evals must prove auth guards mutation endpoints.
- Tests/evals must prove read tools do not mutate state except the documented first default-pet creation behavior of `GET /pet/current`.
- Tests/evals must prove no raw API-key/token-like string is rendered by pet API/UI outputs.

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

If TASK-157 is missing, run the most relevant targeted checks and report the dependency explicitly.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-157 was present in your worktree.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
