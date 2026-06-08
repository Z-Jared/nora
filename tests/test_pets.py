"""Tests for Pet Identity / Pet State store."""

import json
import tempfile
import unittest
from pathlib import Path

from mini_agent.database import NoraDB
from mini_agent.pets import (
    FoodLedgerEntry,
    PetActivityEvent,
    PetIdentity,
    PetRecord,
    PetState,
    PetStore,
)


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
        self.assertEqual(restored.skills, ["memory", "read_file"])

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

    def test_state_clamped(self):
        state = PetState(pet_id="p", hunger=-5, energy=150, mood=50, bond=0,
                         growth_level=0, compute_food_balance=-10)
        clamped = state.clamped()
        self.assertEqual(clamped.hunger, 0)
        self.assertEqual(clamped.energy, 100)
        self.assertEqual(clamped.growth_level, 1)
        self.assertEqual(clamped.compute_food_balance, 0)

    def test_food_ledger_round_trip(self):
        entry = FoodLedgerEntry(
            entry_id="fde_1", pet_id="pet_1", kind="basic_food",
            amount=500, balance_after=500, reason="daily grant",
            created_at="2026-06-08T00:00:00+00:00",
        )
        restored = FoodLedgerEntry.from_dict(entry.to_dict())
        self.assertEqual(restored.amount, 500)
        self.assertEqual(restored.balance_after, 500)

    def test_activity_event_round_trip(self):
        event = PetActivityEvent(
            event_id="evt_1", pet_id="pet_1", event_type="fed",
            summary="fed 100 basic_food",
            metadata={"food_kind": "basic_food", "amount": 100},
            created_at="2026-06-08T00:00:00+00:00",
        )
        d = event.to_dict()
        self.assertIn("metadata_json", d)
        restored = PetActivityEvent.from_dict(event.to_dict())
        self.assertEqual(restored.metadata["food_kind"], "basic_food")


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

    def test_create_second_pet_gets_incremented_id(self):
        self.store.create_pet(name="A")
        pet2 = self.store.create_pet(name="B")
        self.assertEqual(pet2.identity.pet_id, "pet_2")

    def test_get_pet_returns_none_for_missing(self):
        self.assertIsNone(self.store.get_pet("pet_999"))

    def test_list_pets_returns_all(self):
        self.store.create_pet(name="A")
        self.store.create_pet(name="B")
        self.store.create_pet(name="C")
        pets = self.store.list_pets()
        self.assertEqual(len(pets), 3)

    def test_list_pets_respects_limit(self):
        for i in range(5):
            self.store.create_pet(name=f"P{i}")
        pets = self.store.list_pets(limit=2)
        self.assertEqual(len(pets), 2)

    def test_add_food_increases_balance_and_records_ledger(self):
        self.store.create_pet(name="Mochi")
        result = self.store.add_food("pet_1", amount=500, kind="basic_food", reason="daily grant")
        self.assertTrue(result.ok)
        self.assertEqual(result.state.compute_food_balance, 500)

        ledger = self.store.list_food_ledger("pet_1")
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0].amount, 500)
        self.assertEqual(ledger[0].balance_after, 500)

    def test_add_food_rejects_zero_amount(self):
        self.store.create_pet(name="Mochi")
        result = self.store.add_food("pet_1", amount=0)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "invalid_amount")

    def test_add_food_rejects_negative_amount(self):
        self.store.create_pet(name="Mochi")
        result = self.store.add_food("pet_1", amount=-100)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "invalid_amount")

    def test_add_food_rejects_missing_pet(self):
        result = self.store.add_food("pet_999", amount=100)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "pet_not_found")

    def test_feed_pet_spends_food_and_improves_state(self):
        self.store.create_pet(name="Mochi")
        self.store.add_food("pet_1", amount=500, kind="basic_food", reason="test")
        result = self.store.feed_pet("pet_1", food_kind="basic_food", amount=120)
        self.assertTrue(result.ok)
        self.assertEqual(result.state.compute_food_balance, 380)
        self.assertLess(result.state.hunger, 30)
        self.assertGreater(result.state.energy, 60)
        self.assertGreater(result.state.mood, 60)

    def test_feed_pet_rejects_insufficient_balance(self):
        self.store.create_pet(name="Mochi")
        result = self.store.feed_pet("pet_1", food_kind="basic_food", amount=120)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "insufficient_compute_food")
        # Balance must not be mutated
        self.assertEqual(self.store.get_pet("pet_1").state.compute_food_balance, 0)

    def test_feed_pet_rejects_missing_pet(self):
        result = self.store.feed_pet("pet_999", amount=100)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "pet_not_found")

    def test_feed_pet_rejects_zero_amount(self):
        self.store.create_pet(name="Mochi")
        result = self.store.feed_pet("pet_1", amount=0)
        self.assertFalse(result.ok)

    def test_feed_pet_records_food_ledger_and_activity(self):
        self.store.create_pet(name="Mochi")
        self.store.add_food("pet_1", amount=500)
        self.store.feed_pet("pet_1", amount=100)

        ledger = self.store.list_food_ledger("pet_1")
        self.assertEqual(len(ledger), 2)  # add + feed
        events = self.store.list_activity_events("pet_1")
        self.assertTrue(any(e.event_type == "fed" for e in events))

    def test_care_pet_is_free_and_updates_mood_bond(self):
        self.store.create_pet(name="Mochi")
        result = self.store.care_pet("pet_1", action="pat")
        self.assertTrue(result.ok)
        self.assertGreater(result.state.mood, 60)
        self.assertGreater(result.state.bond, 0)
        # Balance unchanged
        self.assertEqual(result.state.compute_food_balance, 0)

    def test_care_pet_all_actions(self):
        self.store.create_pet(name="Mochi")
        for action in ("pat", "comfort", "rest", "play"):
            result = self.store.care_pet("pet_1", action=action)
            self.assertTrue(result.ok, f"care action {action} should succeed")

    def test_care_pet_rejects_invalid_action(self):
        self.store.create_pet(name="Mochi")
        result = self.store.care_pet("pet_1", action="invalid")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "invalid_care_action")

    def test_care_pet_rejects_missing_pet(self):
        result = self.store.care_pet("pet_999", action="pat")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "pet_not_found")

    def test_care_pet_records_activity_event(self):
        self.store.create_pet(name="Mochi")
        self.store.care_pet("pet_1", action="play")
        events = self.store.list_activity_events("pet_1")
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[0].event_type, "care")
        self.assertIn("play", events[0].summary)

    def test_state_bounds_never_exceed_0_100(self):
        self.store.create_pet(name="Mochi")
        # Add huge food
        self.store.add_food("pet_1", amount=100000)
        # Feed many times to try to overflow
        for _ in range(50):
            self.store.feed_pet("pet_1", amount=100)
        pet = self.store.get_pet("pet_1")
        self.assertGreaterEqual(pet.state.hunger, 0)
        self.assertLessEqual(pet.state.hunger, 100)
        self.assertGreaterEqual(pet.state.energy, 0)
        self.assertLessEqual(pet.state.energy, 100)
        self.assertGreaterEqual(pet.state.mood, 0)
        self.assertLessEqual(pet.state.mood, 100)
        self.assertGreaterEqual(pet.state.bond, 0)
        self.assertLessEqual(pet.state.bond, 100)
        self.assertGreaterEqual(pet.state.compute_food_balance, 0)

    def test_sensitive_name_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_pet(name="sk-secret-key-12345")

    def test_sensitive_species_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_pet(name="ok", species="Bearer abcdefghijklmnopqrstuvwxyz123456")

    def test_sensitive_personality_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_pet(name="ok", personality_traits=["sk-12345"])

    def test_sensitive_voice_profile_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_pet(name="Ok", voice_profile={"voice_id": "sk-secret-key-12345"})

    def test_sensitive_taste_profile_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_pet(name="Ok", taste_profile={"likes": ["sk-secret-key-12345"]})

    def test_sensitive_nested_profile_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_pet(
                name="Ok",
                voice_profile={"preset": {"api_key": "sk-secret-key-12345"}},
            )
        with self.assertRaises(ValueError):
            self.store.create_pet(
                name="Ok",
                taste_profile={"private": {"token": "Bearer abcdefghijklmnopqrstuvwxyz123456"}},
            )

    def test_add_food_rejects_sensitive_reason(self):
        self.store.create_pet(name="Mochi")
        result = self.store.add_food("pet_1", amount=50, reason="sk-secret-key-12345")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "rejected_sensitive_input")

    def test_add_food_rejects_sensitive_kind(self):
        self.store.create_pet(name="Mochi")
        result = self.store.add_food("pet_1", amount=50, kind="sk-secret-key-12345")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "rejected_sensitive_input")

    def test_feed_pet_rejects_sensitive_food_kind(self):
        self.store.create_pet(name="Mochi")
        self.store.add_food("pet_1", amount=500)
        result = self.store.feed_pet("pet_1", food_kind="sk-secret-key-12345", amount=100)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason_label, "rejected_sensitive_input")

    def test_no_secret_in_json_output(self):
        self.store.create_pet(name="Mochi")
        self.store.add_food("pet_1", amount=500)
        self.store.feed_pet("pet_1", amount=100)
        result = self.store.feed_pet("pet_1", amount=100)
        output = json.dumps(result.to_dict())
        self.assertNotIn("sk-", output)
        self.assertNotIn("Bearer", output)


class PetStoreJsonlFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.jsonl_path = Path(self.tmpdir) / "pet_data"
        self.store = PetStore(jsonl_path=self.jsonl_path)

    def test_create_and_get_pet(self):
        self.store.create_pet(name="Mochi", species="digital_cat")
        pet = self.store.get_pet("pet_1")
        self.assertIsNotNone(pet)
        self.assertEqual(pet.identity.name, "Mochi")

    def test_list_pets(self):
        self.store.create_pet(name="A")
        self.store.create_pet(name="B")
        pets = self.store.list_pets()
        self.assertEqual(len(pets), 2)

    def test_add_food_and_feed(self):
        self.store.create_pet(name="Mochi")
        self.store.add_food("pet_1", amount=500)
        result = self.store.feed_pet("pet_1", amount=100)
        self.assertTrue(result.ok)
        self.assertEqual(result.state.compute_food_balance, 400)

    def test_care_pet(self):
        self.store.create_pet(name="Mochi")
        result = self.store.care_pet("pet_1", action="pat")
        self.assertTrue(result.ok)
        self.assertGreater(result.state.mood, 60)

    def test_food_ledger_persists(self):
        self.store.create_pet(name="Mochi")
        self.store.add_food("pet_1", amount=300, reason="test")
        ledger = self.store.list_food_ledger("pet_1")
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0].amount, 300)

    def test_activity_events_persist(self):
        self.store.create_pet(name="Mochi")
        self.store.care_pet("pet_1", action="play")
        events = self.store.list_activity_events("pet_1")
        self.assertTrue(len(events) >= 1)

    def test_food_ledger_ids_are_unique(self):
        """JSONL fallback must generate unique IDs by scanning existing file."""
        self.store.create_pet(name="Mochi")
        self.store.add_food("pet_1", 100, reason="a")
        self.store.add_food("pet_1", 100, reason="b")
        ledger = self.store.list_food_ledger("pet_1")
        ids = [e.entry_id for e in ledger]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate IDs: {ids}")
        self.assertEqual(ids, ["fde_2", "fde_1"])  # most recent first

    def test_activity_event_ids_are_unique(self):
        """JSONL fallback must generate unique event IDs."""
        self.store.create_pet(name="Mochi")
        self.store.care_pet("pet_1", "pat")
        self.store.care_pet("pet_1", "play")
        events = self.store.list_activity_events("pet_1")
        ids = [e.event_id for e in events]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate IDs: {ids}")


class PetRegistryToolTests(unittest.TestCase):
    """Tests for pet tools registered in the registry."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        from mini_agent.tools import build_default_registry
        self.registry = build_default_registry(
            workspace_root=Path(self.tmpdir),
            db=NoraDB(Path(self.tmpdir) / "test.db"),
            confirm_action=lambda prompt: True,
        )

    def test_pet_tools_registered(self):
        expected = {
            "create_pet": ("pet", "write"),
            "get_pet": ("pet", "read"),
            "list_pets": ("pet", "read"),
            "add_pet_food": ("pet", "write"),
            "feed_pet": ("pet", "write"),
            "care_pet": ("pet", "write"),
            "list_pet_activity": ("pet", "read"),
        }
        for tool_name, expected_perm in expected.items():
            actual = self.registry.permission_for(tool_name)
            self.assertIsNotNone(actual, f"{tool_name} not registered")
            self.assertEqual(
                (actual.category, actual.risk), expected_perm,
                f"{tool_name} permission mismatch: {(actual.category, actual.risk)} != {expected_perm}",
            )

    def test_registry_create_and_get_pet(self):
        created = self.registry.call("create_pet", name="Mochi")
        self.assertIn("pet_1", created)
        self.assertIn("Mochi", created)

        got = self.registry.call("get_pet", pet_id="pet_1")
        self.assertIn("Mochi", got)

    def test_registry_create_pet_accepts_identity_profiles_and_skills(self):
        created = self.registry.call(
            "create_pet",
            name="Mochi",
            voice_profile={"voice_id": "soft_1", "speed": "normal"},
            taste_profile={"likes": ["sweet"]},
            skills=["memory", "coding"],
        )
        data = json.loads(created)
        self.assertEqual(data["identity"]["voice_profile"]["voice_id"], "soft_1")
        self.assertEqual(data["identity"]["taste_profile"]["likes"], ["sweet"])
        self.assertEqual(data["identity"]["skills"], ["memory", "coding"])

    def test_registry_feed_pet_returns_bounded_json(self):
        self.registry.call("create_pet", name="Mochi")
        self.registry.call("add_pet_food", pet_id="pet_1", amount=300, kind="basic_food")
        fed = self.registry.call("feed_pet", pet_id="pet_1", food_kind="basic_food", amount=100)
        self.assertIn('"ok": true', fed)
        self.assertNotIn("sk-", fed)
        self.assertNotIn("Bearer", fed)

    def test_registry_care_pet(self):
        self.registry.call("create_pet", name="Mochi")
        result = self.registry.call("care_pet", pet_id="pet_1", action="pat")
        self.assertIn('"ok": true', result)

    def test_registry_list_pets(self):
        self.registry.call("create_pet", name="A")
        self.registry.call("create_pet", name="B")
        result = self.registry.call("list_pets")
        self.assertIn("A", result)
        self.assertIn("B", result)

    def test_registry_list_pet_activity(self):
        self.registry.call("create_pet", name="Mochi")
        self.registry.call("care_pet", pet_id="pet_1", action="play")
        result = self.registry.call("list_pet_activity", pet_id="pet_1")
        self.assertIn("care", result)

    def test_pet_store_attached_to_registry(self):
        self.assertIsNotNone(self.registry.pet_store)


if __name__ == "__main__":
    unittest.main()
