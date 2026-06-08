# TASK-155: Pet Identity / Pet State deterministic foundation

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora's product direction has pivoted from an Agent OS control surface to a customizable electronic pet agent. The Agent OS runtime remains the hidden backend, but the first user-facing product loop is now:

```text
create pet -> see pet state -> feed token food -> care/chat -> pet remembers -> pet uses skills
```

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/superpowers/plans/2026-06-08-pet-life-mvp-foundation.md`
- `mini_agent/database.py`
- `mini_agent/durable_tasks.py`
- `mini_agent/memory_records.py`
- `mini_agent/toolkits/registry_builder.py`
- `tests/test_durable_tasks.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Implement the first deterministic Pet Agent backend foundation.

Required behavior:

1. Add `mini_agent/pets.py` with:
   - `PetIdentity`
   - `PetState`
   - `FoodLedgerEntry`
   - `PetActivityEvent`
   - `PetRecord` or equivalent return wrapper
   - `PetActionResult` or equivalent result wrapper
   - `PetStore`

2. Support SQLite through `NoraDB` and JSONL fallback.

3. Add SQLite tables/indexes in `mini_agent/database.py`:
   - `pets`
   - `pet_states`
   - `pet_food_ledger`
   - `pet_activity_events`

4. Implement deterministic store operations:
   - `create_pet(...)`
   - `get_pet(pet_id)`
   - `list_pets(limit=20)`
   - `add_food(pet_id, amount, kind="basic_food", reason="")`
   - `feed_pet(pet_id, food_kind="basic_food", amount=100)`
   - `care_pet(pet_id, action="pat")`
   - `list_food_ledger(pet_id, limit=20)`
   - `list_activity_events(pet_id, limit=20)`

5. Register pet tools in `build_default_registry()`:
   - `create_pet`
   - `get_pet`
   - `list_pets`
   - `add_pet_food`
   - `feed_pet`
   - `care_pet`
   - `list_pet_activity`

6. Attach `registry.pet_store = pet_store`.

## State Rules

Initial default state:

```text
hunger = 30
energy = 60
mood = 60
bond = 0
growth_level = 1
compute_food_balance = 0
```

Bounds:

```text
hunger, energy, mood, bond: 0..100
growth_level: >= 1
compute_food_balance: >= 0
```

Feeding:

- Requires enough `compute_food_balance`.
- Subtracts `amount` from `compute_food_balance`.
- Reduces `hunger`.
- Increases `energy`, `mood`, and `bond`.
- Records a food ledger entry and activity event.
- Must not allow negative balance.

Care:

- Supported actions: `pat`, `comfort`, `rest`, `play`.
- Does not spend compute food.
- Updates mood/bond/energy according to deterministic rules.
- Records an activity event.

Sensitive input:

- Reject or safely bound sensitive pet identity text, reasons, and activity summaries.
- Do not store API keys, tokens, `.env` contents, or secret-like strings.

## Scope

Primary files:

- `mini_agent/pets.py`
- `mini_agent/database.py`
- `mini_agent/toolkits/registry_builder.py`
- `tests/test_pets.py`
- `agent_tasks/A_DONE.md`

Do not edit:

- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`
- `mini_agent/static/`

## Non-Goals

- No billing provider.
- No Web pet room.
- No voice.
- No Live2D or 3D avatar.
- No desktop/mobile companion app.
- No LLM-generated state deltas.
- No model calls.
- No changing existing durable task semantics.

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_mini_agent
git diff --check
```

If feasible, also run:

```bash
python3 -m unittest discover tests
```

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-156 depends on anything you left incomplete.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
