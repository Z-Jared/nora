# TASK-160: Nora-01 robot identity/UI deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Nora has pivoted to a customizable electronic pet agent. TASK-157/158 added the Pet Room API/UI MVP in commit `93e495c`. Claude A owns TASK-159, which should make the default example character `Nora-01`, a robot electronic pet, and improve the visible Pet Room experience. Your job is to lock that public contract with deterministic coverage.

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

Add deterministic offline coverage for the Nora-01 robot default identity and living Pet Room redesign.

Required coverage:

1. HTTP/default identity:
   - `GET /pet/current` creates/returns `Nora-01` when no pet exists.
   - Default species is robot/electronic-life oriented and is not fox/cat.
   - Default identity includes bounded personality, relationship role, speech style, voice/taste profile, and skills.
   - Custom `POST /pet/create` identities still work and are not forced to be robot.

2. Web UI smoke:
   - Pet Room contains stable robot/electronic-pet DOM markers/classes or text that tests can assert.
   - Pet Room shows identity, state metrics, compute food balance, feeding controls, care controls, and activity/diary area.
   - The default first-screen copy frames food as transparent compute food/token energy.
   - The UI does not contain manipulative purchase pressure or pet-distress monetization copy.

3. Evals:
   - Add deterministic evals to `evals/run_evals.py` for the Nora-01 default identity and robot Pet Room contract if TASK-159 is present.
   - If TASK-159 is missing in your worktree, add guarded evals or focused test scaffolding with explicit skip/dependency reporting.
   - Preserve existing TASK-158 pet HTTP/UI evals and CLI/TTY evals.

## Non-Goals

- No product implementation except tiny testability fixes directly required by observed failures.
- No real billing/payment.
- No voice, Live2D, 3D, desktop/mobile native shell, or LLM calls.
- No changes to unrelated CLI/TUI code.

## Safety Boundaries

- Tests/evals must prove default identity is not fox/cat.
- Tests/evals must prove no raw API-key/token-like string is rendered by pet API/UI outputs.
- Tests/evals must prove mutation auth and no-negative balance behavior do not regress.
- Tests/evals must reject manipulative monetization copy such as forced purchase language, pet suffering threats, or hidden-cost wording.

## Scope

Primary files:

- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `evals/run_evals.py`
- `tests/test_pets.py` only if a small identity assertion is needed
- `agent_tasks/B_DONE.md`

Do not edit:

- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
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

If TASK-159 is missing, run the most relevant targeted checks and report the dependency explicitly.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-159 was present in your worktree.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
