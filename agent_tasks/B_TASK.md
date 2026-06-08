# TASK-156: Pet foundation deterministic eval and safety coverage

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Nora is pivoting to a customizable electronic pet agent. Claude A owns TASK-155, the first deterministic pet backend foundation. Your job is to add deterministic eval and safety coverage for that foundation, or prepare the eval patch and report the dependency clearly if TASK-155 is not present in your worktree yet.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/superpowers/plans/2026-06-08-pet-life-mvp-foundation.md`
- `agent_tasks/A_TASK.md`
- `evals/run_evals.py`
- `tests/test_pets.py` if present
- `mini_agent/pets.py` if present
- `mini_agent/toolkits/registry_builder.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic offline eval coverage for the Pet Agent foundation.

Required eval coverage:

1. `pet_create_and_get`
   - create pet through registry
   - get pet through registry
   - output includes bounded identity and default state

2. `pet_feed_requires_balance`
   - create pet
   - attempt feed without food
   - result is safe failure with `insufficient_compute_food`
   - balance remains zero

3. `pet_food_ledger_no_negative_balance`
   - add food
   - feed part of balance
   - attempt overfeed
   - balance never goes negative
   - ledger contains bounded entries

4. `pet_care_free_state_change`
   - care action updates mood/bond
   - care does not consume compute food

5. `pet_registry_permissions`
   - assert exact permissions:
     - `create_pet`: `pet/write`
     - `get_pet`: `pet/read`
     - `list_pets`: `pet/read`
     - `add_pet_food`: `pet/write`
     - `feed_pet`: `pet/write`
     - `care_pet`: `pet/write`
     - `list_pet_activity`: `pet/read`

6. `pet_read_tools_no_mutation`
   - read/list tools do not mutate pet state, food ledger, or activity count

7. `pet_sensitive_name_rejected`
   - secret-like pet names or reasons are rejected or safely redacted
   - raw secret does not appear in output

8. `pet_activity_bounded_no_secret_leak`
   - activity output is bounded
   - raw API keys/tokens/.env-like strings do not appear

## Coordination

TASK-156 depends on TASK-155 for full green integration.

If your worktree does not contain `mini_agent/pets.py` or pet registry tools:

- Do not invent a conflicting pet implementation.
- Prepare evals around the expected public API only if practical.
- Otherwise write the exact blocker in `agent_tasks/B_DONE.md`.

If TASK-155 is present:

- Add evals to `evals/run_evals.py`.
- Add narrowly scoped unit assertions to `tests/test_pets.py` only if needed for behavior that evals cannot cover cleanly.

## Scope

Primary files:

- `evals/run_evals.py`
- `tests/test_pets.py` only if needed
- `agent_tasks/B_DONE.md`

Do not edit:

- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`

## Non-Goals

- No feature implementation unless required to make evals observe an existing TASK-155 API.
- No billing provider.
- No Web room UI.
- No voice/avatar/desktop/mobile work.
- No LLM calls.
- No model-driven pet state mutation.

## Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_pets tests.test_mini_agent
git diff --check
```

If full evals cannot run because TASK-155 is missing, run the most relevant targeted checks and report the dependency explicitly.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-155 was present in your worktree.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
