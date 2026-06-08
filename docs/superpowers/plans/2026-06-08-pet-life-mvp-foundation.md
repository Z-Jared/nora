# Pet Life MVP Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Nora's first deterministic Pet Agent foundation: pet identity, pet state, token food ledger, feed/care transitions, safe registry tools, and deterministic eval coverage.

**Architecture:** Add a focused `mini_agent/pets.py` module with SQLite and JSONL storage following the existing durable task and memory record patterns. Register pet tools through `build_default_registry()` so the current CLI/Web/model tool surfaces can inspect and mutate pet state through bounded, permissioned APIs. Keep all balance, state, and memory mutations deterministic; future LLM output may propose state changes but must not directly own persistence.

**Tech Stack:** Python dataclasses, SQLite via `NoraDB`, JSONL fallback, `ToolRegistry`, `unittest`, existing deterministic eval runner.

---

## File Structure

- Create `mini_agent/pets.py`
  - Owns `PetIdentity`, `PetState`, `FoodLedgerEntry`, `PetActivityEvent`, and `PetStore`.
  - Provides deterministic operations: create pet, get pet, list pets, feed pet, care pet, record activity, list activities.
  - Supports SQLite via `NoraDB` and JSONL fallback for tests and local compatibility.

- Modify `mini_agent/database.py`
  - Add `pets`, `pet_food_ledger`, and `pet_activity_events` tables and indexes.

- Modify `mini_agent/toolkits/registry_builder.py`
  - Instantiate `PetStore`.
  - Attach `registry.pet_store`.
  - Register pet tools with explicit permissions.

- Create `tests/test_pets.py`
  - Unit tests for dataclass round trips, SQLite persistence, JSONL fallback, feed/care transitions, bounds, no-leak behavior, and registry wiring.

- Modify `evals/run_evals.py`
  - Add deterministic offline evals covering registry tools, feed/care state changes, token-food no-leak/no-negative-balance, and no accidental mutation from read tools.

- Modify docs only if implementation reveals a stable contract change:
  - `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
  - `docs/knowledge/PROJECT_WAKEUP.md`

---

## Task 1: Pet Identity And State Store

**Files:**
- Create: `mini_agent/pets.py`
- Modify: `mini_agent/database.py`
- Test: `tests/test_pets.py`

- [ ] **Step 1: Write failing dataclass and SQLite persistence tests**

Add `tests/test_pets.py` with tests shaped like:

```python
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.pets import PetIdentity, PetState, PetStore


class PetDataStructureTests(unittest.TestCase):
    def test_identity_round_trip(self):
        identity = PetIdentity(
            pet_id="pet_1",
            name="Nora",
            species="digital_cat",
            personality_traits=["curious", "gentle"],
            relationship_role="companion",
            speech_style="warm",
            voice_profile={"voice_id": "soft_1", "speed": "normal"},
            taste_profile={"likes": ["sweet"], "dislikes": ["bitter"]},
            skills=["memory", "read_file"],
            created_at="2026-06-08T00:00:00+00:00",
            updated_at="2026-06-08T00:00:00+00:00",
        )
        restored = PetIdentity.from_dict(identity.to_dict())
        self.assertEqual(restored.pet_id, "pet_1")
        self.assertEqual(restored.name, "Nora")
        self.assertEqual(restored.personality_traits, ["curious", "gentle"])

    def test_state_round_trip(self):
        state = PetState(
            pet_id="pet_1",
            hunger=40,
            energy=70,
            mood=55,
            bond=10,
            growth_level=1,
            compute_food_balance=1000,
            updated_at="2026-06-08T00:00:00+00:00",
        )
        restored = PetState.from_dict(state.to_dict())
        self.assertEqual(restored.compute_food_balance, 1000)
        self.assertEqual(restored.hunger, 40)


class PetStoreSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = NoraDB(Path(self.tmpdir) / "test.db")
        self.store = PetStore(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_create_pet_persists_identity_and_default_state(self):
        pet = self.store.create_pet(
            name="Mochi",
            species="digital_cat",
            personality_traits=["playful"],
            relationship_role="pet",
            speech_style="short",
        )
        self.assertEqual(pet.identity.pet_id, "pet_1")
        self.assertEqual(pet.identity.name, "Mochi")
        self.assertEqual(pet.state.hunger, 30)
        self.assertEqual(pet.state.energy, 60)
        self.assertEqual(pet.state.mood, 60)
        self.assertEqual(pet.state.compute_food_balance, 0)

        restored = self.store.get_pet("pet_1")
        self.assertIsNotNone(restored)
        self.assertEqual(restored.identity.name, "Mochi")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_pets
```

Expected: FAIL because `mini_agent.pets` does not exist.

- [ ] **Step 3: Add SQLite tables**

Extend `mini_agent/database.py` `_TABLES` with:

```sql
CREATE TABLE IF NOT EXISTS pets (
    pet_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    species TEXT NOT NULL,
    personality_traits_json TEXT NOT NULL DEFAULT '[]',
    relationship_role TEXT NOT NULL DEFAULT 'companion',
    speech_style TEXT NOT NULL DEFAULT '',
    voice_profile_json TEXT NOT NULL DEFAULT '{}',
    taste_profile_json TEXT NOT NULL DEFAULT '{}',
    skills_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pet_states (
    pet_id TEXT PRIMARY KEY,
    hunger INTEGER NOT NULL DEFAULT 30,
    energy INTEGER NOT NULL DEFAULT 60,
    mood INTEGER NOT NULL DEFAULT 60,
    bond INTEGER NOT NULL DEFAULT 0,
    growth_level INTEGER NOT NULL DEFAULT 1,
    compute_food_balance INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pet_food_ledger (
    entry_id TEXT PRIMARY KEY,
    pet_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pet_activity_events (
    event_id TEXT PRIMARY KEY,
    pet_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
```

Extend `_INDEXES` with:

```sql
CREATE INDEX IF NOT EXISTS idx_pet_updated ON pets(updated_at);
CREATE INDEX IF NOT EXISTS idx_pet_food_pet ON pet_food_ledger(pet_id);
CREATE INDEX IF NOT EXISTS idx_pet_food_created ON pet_food_ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_pet_activity_pet ON pet_activity_events(pet_id);
CREATE INDEX IF NOT EXISTS idx_pet_activity_created ON pet_activity_events(created_at);
```

- [ ] **Step 4: Implement `mini_agent/pets.py` minimal store**

Implement dataclasses and these methods:

```python
store.create_pet(...)
store.get_pet(pet_id)
store.list_pets(limit=20)
```

Bound numeric state fields to safe ranges:

```text
hunger, energy, mood, bond: 0..100
growth_level: >= 1
compute_food_balance: >= 0
```

Reject sensitive text in name/species/personality/speech fields using existing `is_sensitive_text`.

- [ ] **Step 5: Run unit tests**

Run:

```bash
python3 -m unittest tests.test_pets
```

Expected: PASS.

---

## Task 2: Token Food Ledger And Feed/Care Transitions

**Files:**
- Modify: `mini_agent/pets.py`
- Test: `tests/test_pets.py`

- [ ] **Step 1: Write failing transition tests**

Add tests for:

```python
def test_add_food_increases_compute_balance_and_records_ledger(self):
    pet = self.store.create_pet(name="Mochi")
    result = self.store.add_food("pet_1", amount=500, kind="basic_food", reason="daily grant")
    self.assertEqual(result.state.compute_food_balance, 500)
    ledger = self.store.list_food_ledger("pet_1")
    self.assertEqual(ledger[0].amount, 500)
    self.assertEqual(ledger[0].balance_after, 500)

def test_feed_pet_spends_compute_food_and_improves_state(self):
    self.store.create_pet(name="Mochi")
    self.store.add_food("pet_1", amount=500, kind="basic_food", reason="test")
    result = self.store.feed_pet("pet_1", food_kind="basic_food", amount=120)
    self.assertEqual(result.state.compute_food_balance, 380)
    self.assertLess(result.state.hunger, 30)
    self.assertGreater(result.state.energy, 60)
    self.assertGreater(result.state.mood, 60)

def test_feed_pet_rejects_insufficient_balance_without_mutation(self):
    self.store.create_pet(name="Mochi")
    result = self.store.feed_pet("pet_1", food_kind="basic_food", amount=120)
    self.assertFalse(result.ok)
    self.assertIn("insufficient_compute_food", result.reason_label)
    self.assertEqual(self.store.get_pet("pet_1").state.compute_food_balance, 0)

def test_care_pet_is_free_and_updates_mood_bond(self):
    self.store.create_pet(name="Mochi")
    result = self.store.care_pet("pet_1", action="pat")
    self.assertTrue(result.ok)
    self.assertGreater(result.state.mood, 60)
    self.assertGreater(result.state.bond, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_pets
```

Expected: FAIL because ledger and transitions are not implemented.

- [ ] **Step 3: Implement food and care operations**

Implement:

```python
store.add_food(pet_id, amount, kind="basic_food", reason="")
store.feed_pet(pet_id, food_kind="basic_food", amount=100)
store.care_pet(pet_id, action="pat")
store.list_food_ledger(pet_id, limit=20)
store.list_activity_events(pet_id, limit=20)
```

Rules:

- `add_food` only accepts positive amount, clamps huge input to a safe error rather than storing it.
- `feed_pet` requires enough `compute_food_balance`.
- `feed_pet` subtracts from compute balance.
- Feeding reduces hunger and increases energy/mood/bond within 0..100.
- Care actions do not spend compute food.
- Supported `care_pet` actions: `pat`, `comfort`, `rest`, `play`.
- Every successful feed/care writes a bounded activity event.
- Activity summaries must not include raw secrets or unbounded user text.

- [ ] **Step 4: Run unit tests**

Run:

```bash
python3 -m unittest tests.test_pets
```

Expected: PASS.

---

## Task 3: Registry Tools For Pet MVP

**Files:**
- Modify: `mini_agent/toolkits/registry_builder.py`
- Modify: `mini_agent/pets.py`
- Test: `tests/test_pets.py`

- [ ] **Step 1: Write failing registry tests**

Add tests:

```python
from mini_agent.tools import build_default_registry

def test_pet_tools_registered_with_expected_permissions(self):
    registry = build_default_registry(workspace_root=Path(self.tmpdir), db=self.db, confirm_action=lambda prompt: True)
    expected = {
        "create_pet": ("pet", "write"),
        "get_pet": ("pet", "read"),
        "list_pets": ("pet", "read"),
        "add_pet_food": ("pet", "write"),
        "feed_pet": ("pet", "write"),
        "care_pet": ("pet", "write"),
        "list_pet_activity": ("pet", "read"),
    }
    for tool, permission in expected.items():
        actual = registry.permission_for(tool)
        self.assertIsNotNone(actual)
        self.assertEqual((actual.category, actual.risk), permission)

def test_registry_feed_pet_returns_bounded_json(self):
    registry = build_default_registry(workspace_root=Path(self.tmpdir), db=self.db, confirm_action=lambda prompt: True)
    created = registry.call("create_pet", name="Mochi")
    self.assertIn('"pet_id": "pet_1"', created)
    registry.call("add_pet_food", pet_id="pet_1", amount=300, kind="basic_food")
    fed = registry.call("feed_pet", pet_id="pet_1", food_kind="basic_food", amount=100)
    self.assertIn('"ok": true', fed)
    self.assertNotIn("sk-", fed)
```

- [ ] **Step 2: Run targeted tests to verify failure**

Run:

```bash
python3 -m unittest tests.test_pets
```

Expected: FAIL because registry tools are not registered.

- [ ] **Step 3: Register tools**

In `registry_builder.py`:

- import `PetStore`
- instantiate `pet_store = PetStore(db=db)`
- attach `registry.pet_store = pet_store`
- register these JSON-returning wrappers:

```text
create_pet
get_pet
list_pets
add_pet_food
feed_pet
care_pet
list_pet_activity
```

Permissions:

```text
create_pet: pet/write
get_pet: pet/read
list_pets: pet/read
add_pet_food: pet/write
feed_pet: pet/write
care_pet: pet/write
list_pet_activity: pet/read
```

Do not require confirmation yet for low-risk local pet state writes; token purchase and external billing are not in scope.

- [ ] **Step 4: Run tests**

Run:

```bash
python3 -m unittest tests.test_pets tests.test_mini_agent
```

Expected: PASS.

---

## Task 4: Deterministic Eval Coverage

**Files:**
- Modify: `evals/run_evals.py`
- Test: `evals/run_evals.py`

- [ ] **Step 1: Add eval cases**

Add evals that exercise:

```text
pet_create_and_get
pet_feed_requires_balance
pet_food_ledger_no_negative_balance
pet_care_free_state_change
pet_registry_permissions
pet_read_tools_no_mutation
pet_sensitive_name_rejected
pet_activity_bounded_no_secret_leak
```

Each eval should create a temp DB/root, use `build_default_registry(...)`, and assert JSON output. Follow existing eval style near other registry/no-leak evals.

- [ ] **Step 2: Run evals**

Run:

```bash
python3 evals/run_evals.py
```

Expected: all evals pass, count increases by the number added.

---

## Task 5: Documentation And Final Verification

**Files:**
- Modify if needed: `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- Modify if needed: `README.md`

- [ ] **Step 1: Update docs only for implemented facts**

If the implementation names differ from the direction doc, update the doc to match exact names.

- [ ] **Step 2: Run focused verification**

Run:

```bash
python3 -m unittest tests.test_pets tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

Expected: all pass.

---

## Self-Review

Spec coverage:

- Pet Identity: Task 1.
- Pet State: Task 1 and Task 2.
- Token Food Economy foundation: Task 2.
- Registry/API surface: Task 3.
- Deterministic eval and safety: Task 4.
- Documentation sync: Task 5.

Intentional non-goals:

- No billing provider integration.
- No Web pet room in this first foundation plan.
- No voice, Live2D, desktop floating pet, mobile widget, or multimodal runtime.
- No model-generated state deltas yet.

Placeholder scan: no task uses placeholder implementation steps; every task has exact files, commands, and expected outcomes.
