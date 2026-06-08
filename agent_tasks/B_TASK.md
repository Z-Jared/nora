# TASK-162: Token food economy deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Nora is now a customizable electronic pet agent. TASK-161 should add a deterministic Token Food Economy MVP: transparent food/token balance, cost estimates, can-run checks, and non-manipulative insufficient-balance explanations. Your job is to lock that public contract with deterministic coverage.

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

Add deterministic offline coverage for token food estimate/status and transparent spend boundaries.

Required coverage:

1. HTTP/API:
   - Food estimate/status endpoint is read-only and bounded.
   - Response includes balance, estimated cost, `can_run`/equivalent, reason label, and safe copy.
   - Known actions have deterministic costs.
   - Unknown/bad actions are bounded and do not leak raw secret-like input.
   - Insufficient balance does not mutate state or create negative ledger entries.
   - Existing mutation auth and no-negative feed behavior remain covered.

2. Web UI smoke:
   - Pet Room shows balance and estimated costs.
   - Insufficient-balance copy is present and non-manipulative.
   - UI does not contain purchase pressure, suffering threats, hidden-cost wording, or raw secret-like text.

3. Evals:
   - Add deterministic evals to `evals/run_evals.py` if TASK-161 is present.
   - If TASK-161 is missing in your worktree, add guarded evals or focused test scaffolding with explicit skip/dependency reporting.
   - Preserve existing pet/Nora-01/CLI/TTY evals.

## Non-Goals

- No product implementation except tiny testability fixes directly required by observed failures.
- No real payment, subscription, third-party billing, voice, Live2D, 3D, desktop/mobile native shell, or LLM calls.
- No changes to unrelated CLI/TUI code.

## Safety Boundaries

- Tests/evals must prove estimate/status is read-only.
- Tests/evals must prove insufficient balance does not spend food.
- Tests/evals must reject manipulative monetization copy such as forced purchase language, pet suffering threats, or hidden-cost wording.
- Tests/evals must prove no raw API-key/token-like string is rendered by pet API/UI outputs.

## Scope

Primary files:

- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `evals/run_evals.py`
- `tests/test_pets.py` only if a small economy assertion is needed
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

If TASK-161 is missing, run the most relevant targeted checks and report the dependency explicitly.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-161 was present in your worktree.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
