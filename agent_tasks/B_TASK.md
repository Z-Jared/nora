# TASK-164: Relationship memory deterministic coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Nora is now a customizable electronic pet agent. TASK-163 should add a deterministic Relationship Memory MVP so the pet can remember shared moments, preferences, and task outcomes. Your job is to lock that public contract with deterministic coverage.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `agent_tasks/A_TASK.md`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_pets.py`
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

Add deterministic offline coverage for the Relationship Memory MVP.

Expected TASK-163 contract to cover:

1. API/store:
   - Relationship memory write endpoint records supported kinds such as `shared_moment`, `preference`, `task_outcome`.
   - List endpoint returns recent memories for a pet with bounded limit.
   - Response includes stable fields such as `memory_id`, `pet_id`, `kind`, `summary`, `source`, `importance`, `created_at`.
   - Unsupported kind and invalid pet IDs are bounded.
   - Secret-like summary/source/metadata is rejected and not persisted.
   - Mutation auth remains enforced.

2. Web UI:
   - Pet Room includes a relationship memory section.
   - Recent memory text is escaped.
   - No fake intimacy, guilt, pressure, hidden purchase wording, or raw secret-like text.

3. Regression:
   - Existing pet identity, token food, auth, no-negative balance, and Nora-01 evals remain active/pass.
   - New relationship memory evals should guarded-skip if TASK-163 is absent, but be active/pass when applied with TASK-163.

## Non-Goals

- No feature implementation except tiny testability fixes directly required by observed failures.
- No external memory provider, vector RAG, LLM calls, voice, 3D/VRM, marketplace, billing, or CLI/TUI redesign.

## Safety Boundaries

- Tests/evals must prove no secret-like text is saved or rendered.
- Tests/evals must prove HTML injection is escaped.
- Tests/evals must prove mutation auth does not regress.
- Do not weaken or skip existing token_food, Nora-01, or pet HTTP evals.

## Scope

Primary files:

- `tests/test_pets.py`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`
- `evals/run_evals.py`
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

If TASK-163 is missing, run the most relevant targeted checks and report the dependency explicitly.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-163 was present in your worktree.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
