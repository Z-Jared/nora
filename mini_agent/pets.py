"""Pet Identity / Pet State deterministic store for Nora.

Provides PetIdentity, PetState, FoodLedgerEntry, PetActivityEvent,
PetRecord, PetActionResult, and PetStore with SQLite (via NoraDB) and
JSONL backends.  All state mutations are deterministic and bounded.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mini_agent.memory import is_sensitive_text
from mini_agent.tools_common import read_jsonl

_PET_PREFIX = "pet_"
_FOOD_PREFIX = "fde_"
_EVENT_PREFIX = "evt_"

_DEFAULT_STATE = {
    "hunger": 30,
    "energy": 60,
    "mood": 60,
    "bond": 0,
    "growth_level": 1,
    "compute_food_balance": 0,
}

_CARE_ACTIONS = ("pat", "comfort", "rest", "play")

# Deterministic care effects: (hunger_delta, energy_delta, mood_delta, bond_delta)
_CARE_EFFECTS = {
    "pat":     (0,  -2, +8, +5),
    "comfort": (0,  -3, +10, +6),
    "rest":    (0, +15, +3, +2),
    "play":    (+5, -10, +12, +8),
}

# Feed effects per 100 food units (scaled linearly)
_FEED_PER_100 = {
    "hunger": -25,
    "energy": +15,
    "mood":   +10,
    "bond":   +5,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(records: list[dict], prefix: str, key: str) -> int:
    max_id = 0
    for record in records:
        raw = str(record.get(key, ""))
        if raw.startswith(prefix):
            try:
                max_id = max(max_id, int(raw[len(prefix):]))
            except ValueError:
                pass
    return max_id + 1


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def _validate_text_fields(**fields) -> Optional[str]:
    """Reject sensitive text in pet identity fields."""
    for name, value in fields.items():
        if value and is_sensitive_text(str(value)):
            return f"rejected sensitive text in {name}"
    return None


def _validate_list_fields(**fields) -> Optional[str]:
    """Reject sensitive text in list-of-string fields."""
    for name, items in fields.items():
        if items:
            for item in items:
                if is_sensitive_text(str(item)):
                    return f"rejected sensitive text in {name}"
    return None


def _validate_profile_value(name: str, value) -> Optional[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            if is_sensitive_text(str(key)):
                return f"rejected sensitive text in {name}.{key}"
            err = _validate_profile_value(f"{name}.{key}", nested)
            if err:
                return err
        return None
    if isinstance(value, list):
        for index, item in enumerate(value):
            err = _validate_profile_value(f"{name}[{index}]", item)
            if err:
                return err
        return None
    if value is not None and is_sensitive_text(str(value)):
        return f"rejected sensitive text in {name}"
    return None


def _validate_dict_values(**fields) -> Optional[str]:
    """Reject sensitive text in nested dict/list profile values."""
    for name, d in fields.items():
        if d:
            err = _validate_profile_value(name, d)
            if err:
                return err
    return None


@dataclass
class PetIdentity:
    pet_id: str
    name: str
    species: str
    personality_traits: list[str] = field(default_factory=list)
    relationship_role: str = "companion"
    speech_style: str = ""
    voice_profile: dict = field(default_factory=dict)
    taste_profile: dict = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PetIdentity:
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })


@dataclass
class PetState:
    pet_id: str
    hunger: int = 30
    energy: int = 60
    mood: int = 60
    bond: int = 0
    growth_level: int = 1
    compute_food_balance: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PetState:
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })

    def clamped(self) -> PetState:
        """Return a new state with values clamped to valid ranges."""
        return PetState(
            pet_id=self.pet_id,
            hunger=_clamp(self.hunger),
            energy=_clamp(self.energy),
            mood=_clamp(self.mood),
            bond=_clamp(self.bond),
            growth_level=max(1, self.growth_level),
            compute_food_balance=max(0, self.compute_food_balance),
            updated_at=self.updated_at,
        )


@dataclass
class FoodLedgerEntry:
    entry_id: str
    pet_id: str
    kind: str
    amount: int
    balance_after: int
    reason: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> FoodLedgerEntry:
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })


@dataclass
class PetActivityEvent:
    event_id: str
    pet_id: str
    event_type: str
    summary: str
    metadata: dict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["metadata_json"] = json.dumps(d.pop("metadata", {}), ensure_ascii=False)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PetActivityEvent:
        meta = data.get("metadata")
        if meta is None:
            raw = data.get("metadata_json", "{}")
            if isinstance(raw, str):
                meta = json.loads(raw)
            else:
                meta = raw or {}
        return cls(
            event_id=data["event_id"],
            pet_id=data["pet_id"],
            event_type=data["event_type"],
            summary=data["summary"],
            metadata=meta,
            created_at=data.get("created_at", ""),
        )


_RELATIONSHIP_MEMORY_KINDS = ("shared_moment", "preference", "task_outcome")
_RELATIONSHIP_MEMORY_PREFIX = "rmem_"
_RELATIONSHIP_MEMORY_SUMMARY_MAX = 500
_RELATIONSHIP_MEMORY_SOURCE_MAX = 200


@dataclass
class PetRelationshipMemory:
    memory_id: str
    pet_id: str
    kind: str
    summary: str
    source: str = ""
    importance: int = 5
    metadata: dict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["metadata_json"] = json.dumps(d.pop("metadata", {}), ensure_ascii=False)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PetRelationshipMemory:
        meta = data.get("metadata")
        if meta is None:
            raw = data.get("metadata_json", "{}")
            if isinstance(raw, str):
                meta = json.loads(raw)
            else:
                meta = raw or {}
        return cls(
            memory_id=data["memory_id"],
            pet_id=data["pet_id"],
            kind=data["kind"],
            summary=data["summary"],
            source=data.get("source", ""),
            importance=data.get("importance", 5),
            metadata=meta,
            created_at=data.get("created_at", ""),
        )


@dataclass
class PetRecord:
    """Combined identity + state return wrapper."""
    identity: PetIdentity
    state: PetState

    def to_dict(self) -> dict:
        return {
            "pet_id": self.identity.pet_id,
            "identity": self.identity.to_dict(),
            "state": self.state.to_dict(),
        }


@dataclass
class PetActionResult:
    """Result wrapper for feed/care operations."""
    ok: bool
    reason_label: str = ""
    pet: Optional[PetRecord] = None
    state: Optional[PetState] = None

    def to_dict(self) -> dict:
        d: dict = {"ok": self.ok}
        if self.reason_label:
            d["reason_label"] = self.reason_label
        if self.pet:
            d["pet"] = self.pet.to_dict()
        if self.state:
            d["state"] = self.state.to_dict()
        return d


def _row_to_identity(row) -> PetIdentity:
    return PetIdentity(
        pet_id=row[0],
        name=row[1],
        species=row[2],
        personality_traits=json.loads(row[3]),
        relationship_role=row[4],
        speech_style=row[5],
        voice_profile=json.loads(row[6]),
        taste_profile=json.loads(row[7]),
        skills=json.loads(row[8]),
        created_at=row[9],
        updated_at=row[10],
    )


def _row_to_state(row) -> PetState:
    return PetState(
        pet_id=row[0],
        hunger=row[1],
        energy=row[2],
        mood=row[3],
        bond=row[4],
        growth_level=row[5],
        compute_food_balance=row[6],
        updated_at=row[7],
    )


def _row_to_food_entry(row) -> FoodLedgerEntry:
    return FoodLedgerEntry(
        entry_id=row[0],
        pet_id=row[1],
        kind=row[2],
        amount=row[3],
        balance_after=row[4],
        reason=row[5],
        created_at=row[6],
    )


def _row_to_activity_event(row) -> PetActivityEvent:
    return PetActivityEvent(
        event_id=row[0],
        pet_id=row[1],
        event_type=row[2],
        summary=row[3],
        metadata=json.loads(row[4]) if row[4] else {},
        created_at=row[5],
    )


def _row_to_relationship_memory(row) -> PetRelationshipMemory:
    return PetRelationshipMemory(
        memory_id=row[0],
        pet_id=row[1],
        kind=row[2],
        summary=row[3],
        source=row[4],
        importance=row[5],
        metadata=json.loads(row[6]) if row[6] else {},
        created_at=row[7],
    )


class PetStore:
    """Deterministic pet state store with SQLite and JSONL backends."""

    def __init__(self, db=None, jsonl_path: Optional[Path] = None):
        self._db = db
        self._jsonl_path = jsonl_path

    # --- helpers ---

    def _now(self) -> str:
        return _now_iso()

    def _next_pet_id(self) -> str:
        if self._db:
            rows = self._db.conn.execute("SELECT pet_id FROM pets").fetchall()
            max_id = 0
            for row in rows:
                raw = str(row[0])
                if raw.startswith(_PET_PREFIX):
                    try:
                        max_id = max(max_id, int(raw[len(_PET_PREFIX):]))
                    except ValueError:
                        pass
            return f"{_PET_PREFIX}{max_id + 1}"
        # JSONL fallback
        records = self._load_jsonl_pets()
        return f"{_PET_PREFIX}{_next_id(records, _PET_PREFIX, 'pet_id')}"

    def _next_food_id(self) -> str:
        if self._db:
            rows = self._db.conn.execute("SELECT entry_id FROM pet_food_ledger").fetchall()
            max_id = 0
            for row in rows:
                raw = str(row[0])
                if raw.startswith(_FOOD_PREFIX):
                    try:
                        max_id = max(max_id, int(raw[len(_FOOD_PREFIX):]))
                    except ValueError:
                        pass
            return f"{_FOOD_PREFIX}{max_id + 1}"
        # JSONL fallback: scan existing ledger file
        max_id = 0
        if self._jsonl_path:
            food_file = self._jsonl_path / "pet_food_ledger.jsonl"
            for entry in read_jsonl(food_file):
                raw = str(entry.get("entry_id", ""))
                if raw.startswith(_FOOD_PREFIX):
                    try:
                        max_id = max(max_id, int(raw[len(_FOOD_PREFIX):]))
                    except ValueError:
                        pass
        return f"{_FOOD_PREFIX}{max_id + 1}"

    def _next_event_id(self) -> str:
        if self._db:
            rows = self._db.conn.execute("SELECT event_id FROM pet_activity_events").fetchall()
            max_id = 0
            for row in rows:
                raw = str(row[0])
                if raw.startswith(_EVENT_PREFIX):
                    try:
                        max_id = max(max_id, int(raw[len(_EVENT_PREFIX):]))
                    except ValueError:
                        pass
            return f"{_EVENT_PREFIX}{max_id + 1}"
        # JSONL fallback: scan existing events file
        max_id = 0
        if self._jsonl_path:
            events_file = self._jsonl_path / "pet_activity_events.jsonl"
            for entry in read_jsonl(events_file):
                raw = str(entry.get("event_id", ""))
                if raw.startswith(_EVENT_PREFIX):
                    try:
                        max_id = max(max_id, int(raw[len(_EVENT_PREFIX):]))
                    except ValueError:
                        pass
        return f"{_EVENT_PREFIX}{max_id + 1}"

    # --- JSONL fallback helpers ---

    def _load_jsonl_pets(self) -> list[dict]:
        if not self._jsonl_path:
            return []
        pets_file = self._jsonl_path / "pets.jsonl"
        return read_jsonl(pets_file)

    def _save_jsonl_pet(self, identity: PetIdentity, state: PetState) -> None:
        if not self._jsonl_path:
            return
        self._jsonl_path.mkdir(parents=True, exist_ok=True)
        pets_file = self._jsonl_path / "pets.jsonl"
        record = {"identity": identity.to_dict(), "state": state.to_dict()}
        with open(pets_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _save_jsonl_food(self, entry: FoodLedgerEntry) -> None:
        if not self._jsonl_path:
            return
        self._jsonl_path.mkdir(parents=True, exist_ok=True)
        food_file = self._jsonl_path / "pet_food_ledger.jsonl"
        with open(food_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def _save_jsonl_event(self, event: PetActivityEvent) -> None:
        if not self._jsonl_path:
            return
        self._jsonl_path.mkdir(parents=True, exist_ok=True)
        events_file = self._jsonl_path / "pet_activity_events.jsonl"
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def _update_jsonl_pet_state(self, pet_id: str, new_state: PetState) -> None:
        """Update pet state in the JSONL pets file after a mutation."""
        if not self._jsonl_path:
            return
        pets_file = self._jsonl_path / "pets.jsonl"
        if not pets_file.exists():
            return
        lines = pets_file.read_text(encoding="utf-8").splitlines()
        updated_lines = []
        for line in lines:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("identity", {}).get("pet_id") == pet_id:
                record["state"] = new_state.to_dict()
            updated_lines.append(json.dumps(record, ensure_ascii=False))
        pets_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

    # --- public API ---

    def create_pet(
        self,
        name: str,
        species: str = "digital_pet",
        personality_traits: Optional[list[str]] = None,
        relationship_role: str = "companion",
        speech_style: str = "",
        voice_profile: Optional[dict] = None,
        taste_profile: Optional[dict] = None,
        skills: Optional[list[str]] = None,
    ) -> PetRecord:
        """Create a new pet with default initial state."""
        # Validate sensitive text
        err = _validate_text_fields(
            name=name, species=species,
            relationship_role=relationship_role, speech_style=speech_style,
        )
        if err:
            raise ValueError(err)
        err = _validate_list_fields(
            personality_traits=personality_traits,
            skills=skills,
        )
        if err:
            raise ValueError(err)
        err = _validate_dict_values(
            voice_profile=voice_profile or {},
            taste_profile=taste_profile or {},
        )
        if err:
            raise ValueError(err)

        now = self._now()
        pet_id = self._next_pet_id()

        identity = PetIdentity(
            pet_id=pet_id,
            name=name,
            species=species,
            personality_traits=personality_traits or [],
            relationship_role=relationship_role,
            speech_style=speech_style,
            voice_profile=voice_profile or {},
            taste_profile=taste_profile or {},
            skills=skills or [],
            created_at=now,
            updated_at=now,
        )

        state = PetState(
            pet_id=pet_id,
            updated_at=now,
        ).clamped()

        if self._db:
            self._db.conn.execute(
                "INSERT INTO pets (pet_id, name, species, personality_traits_json, "
                "relationship_role, speech_style, voice_profile_json, taste_profile_json, "
                "skills_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (identity.pet_id, identity.name, identity.species,
                 json.dumps(identity.personality_traits, ensure_ascii=False),
                 identity.relationship_role, identity.speech_style,
                 json.dumps(identity.voice_profile, ensure_ascii=False),
                 json.dumps(identity.taste_profile, ensure_ascii=False),
                 json.dumps(identity.skills, ensure_ascii=False),
                 identity.created_at, identity.updated_at),
            )
            self._db.conn.execute(
                "INSERT INTO pet_states (pet_id, hunger, energy, mood, bond, "
                "growth_level, compute_food_balance, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (state.pet_id, state.hunger, state.energy, state.mood,
                 state.bond, state.growth_level, state.compute_food_balance,
                 state.updated_at),
            )
            self._db.conn.commit()
        else:
            self._save_jsonl_pet(identity, state)

        return PetRecord(identity=identity, state=state)

    def get_pet(self, pet_id: str) -> Optional[PetRecord]:
        """Get a pet by ID, or None if not found."""
        if self._db:
            row = self._db.conn.execute(
                "SELECT * FROM pets WHERE pet_id = ?", (pet_id,)
            ).fetchone()
            if not row:
                return None
            identity = _row_to_identity(row)
            state_row = self._db.conn.execute(
                "SELECT * FROM pet_states WHERE pet_id = ?", (pet_id,)
            ).fetchone()
            state = _row_to_state(state_row) if state_row else PetState(pet_id=pet_id)
            return PetRecord(identity=identity, state=state)
        # JSONL fallback
        for record in self._load_jsonl_pets():
            ident_data = record.get("identity", {})
            if ident_data.get("pet_id") == pet_id:
                identity = PetIdentity.from_dict(ident_data)
                state = PetState.from_dict(record.get("state", {"pet_id": pet_id}))
                return PetRecord(identity=identity, state=state)
        return None

    def list_pets(self, limit: int = 20) -> list[PetRecord]:
        """List pets, most recent first."""
        if self._db:
            rows = self._db.conn.execute(
                "SELECT * FROM pets ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            results = []
            for row in rows:
                identity = _row_to_identity(row)
                state_row = self._db.conn.execute(
                    "SELECT * FROM pet_states WHERE pet_id = ?", (identity.pet_id,)
                ).fetchone()
                state = _row_to_state(state_row) if state_row else PetState(pet_id=identity.pet_id)
                results.append(PetRecord(identity=identity, state=state))
            return results
        # JSONL fallback
        all_records = self._load_jsonl_pets()
        results = []
        for record in reversed(all_records[-limit:]):
            ident_data = record.get("identity", {})
            identity = PetIdentity.from_dict(ident_data)
            state = PetState.from_dict(record.get("state", {"pet_id": identity.pet_id}))
            results.append(PetRecord(identity=identity, state=state))
        return results

    def add_food(
        self,
        pet_id: str,
        amount: int,
        kind: str = "basic_food",
        reason: str = "",
    ) -> PetActionResult:
        """Add compute food to a pet's balance."""
        if amount <= 0:
            return PetActionResult(ok=False, reason_label="invalid_amount")

        # Validate sensitive text in reason/kind
        if reason and is_sensitive_text(reason):
            return PetActionResult(ok=False, reason_label="rejected_sensitive_input")
        if kind and is_sensitive_text(kind):
            return PetActionResult(ok=False, reason_label="rejected_sensitive_input")

        pet = self.get_pet(pet_id)
        if not pet:
            return PetActionResult(ok=False, reason_label="pet_not_found")

        now = self._now()
        new_balance = pet.state.compute_food_balance + amount
        new_state = PetState(
            pet_id=pet_id,
            hunger=pet.state.hunger,
            energy=pet.state.energy,
            mood=pet.state.mood,
            bond=pet.state.bond,
            growth_level=pet.state.growth_level,
            compute_food_balance=new_balance,
            updated_at=now,
        ).clamped()

        entry = FoodLedgerEntry(
            entry_id=self._next_food_id(),
            pet_id=pet_id,
            kind=kind,
            amount=amount,
            balance_after=new_state.compute_food_balance,
            reason=reason[:200] if reason else "",
            created_at=now,
        )

        event = PetActivityEvent(
            event_id=self._next_event_id(),
            pet_id=pet_id,
            event_type="food_added",
            summary=f"added {amount} {kind}",
            metadata={"kind": kind, "amount": amount},
            created_at=now,
        )

        if self._db:
            self._db.conn.execute(
                "UPDATE pet_states SET compute_food_balance=?, updated_at=? WHERE pet_id=?",
                (new_state.compute_food_balance, now, pet_id),
            )
            self._db.conn.execute(
                "INSERT INTO pet_food_ledger (entry_id, pet_id, kind, amount, balance_after, reason, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (entry.entry_id, entry.pet_id, entry.kind, entry.amount,
                 entry.balance_after, entry.reason, entry.created_at),
            )
            self._db.conn.execute(
                "INSERT INTO pet_activity_events (event_id, pet_id, event_type, summary, metadata_json, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (event.event_id, event.pet_id, event.event_type, event.summary,
                 json.dumps(event.metadata, ensure_ascii=False), event.created_at),
            )
            self._db.conn.commit()
        else:
            self._save_jsonl_food(entry)
            self._save_jsonl_event(event)
            self._update_jsonl_pet_state(pet_id, new_state)

        pet.state = new_state
        return PetActionResult(ok=True, pet=pet, state=new_state)

    def feed_pet(
        self,
        pet_id: str,
        food_kind: str = "basic_food",
        amount: int = 100,
    ) -> PetActionResult:
        """Feed a pet, spending compute food balance."""
        if amount <= 0:
            return PetActionResult(ok=False, reason_label="invalid_amount")

        if food_kind and is_sensitive_text(food_kind):
            return PetActionResult(ok=False, reason_label="rejected_sensitive_input")

        pet = self.get_pet(pet_id)
        if not pet:
            return PetActionResult(ok=False, reason_label="pet_not_found")

        if pet.state.compute_food_balance < amount:
            return PetActionResult(ok=False, reason_label="insufficient_compute_food")

        now = self._now()
        scale = amount / 100.0

        new_hunger = _clamp(pet.state.hunger + int(_FEED_PER_100["hunger"] * scale))
        new_energy = _clamp(pet.state.energy + int(_FEED_PER_100["energy"] * scale))
        new_mood = _clamp(pet.state.mood + int(_FEED_PER_100["mood"] * scale))
        new_bond = _clamp(pet.state.bond + int(_FEED_PER_100["bond"] * scale))
        new_balance = pet.state.compute_food_balance - amount

        new_state = PetState(
            pet_id=pet_id,
            hunger=new_hunger,
            energy=new_energy,
            mood=new_mood,
            bond=new_bond,
            growth_level=pet.state.growth_level,
            compute_food_balance=max(0, new_balance),
            updated_at=now,
        )

        entry = FoodLedgerEntry(
            entry_id=self._next_food_id(),
            pet_id=pet_id,
            kind=food_kind,
            amount=-amount,
            balance_after=new_state.compute_food_balance,
            reason=f"feed {food_kind}",
            created_at=now,
        )

        event = PetActivityEvent(
            event_id=self._next_event_id(),
            pet_id=pet_id,
            event_type="fed",
            summary=f"fed {amount} {food_kind}",
            metadata={"food_kind": food_kind, "amount": amount},
            created_at=now,
        )

        if self._db:
            self._db.conn.execute(
                "UPDATE pet_states SET hunger=?, energy=?, mood=?, bond=?, "
                "compute_food_balance=?, updated_at=? WHERE pet_id=?",
                (new_state.hunger, new_state.energy, new_state.mood,
                 new_state.bond, new_state.compute_food_balance, now, pet_id),
            )
            self._db.conn.execute(
                "INSERT INTO pet_food_ledger (entry_id, pet_id, kind, amount, balance_after, reason, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (entry.entry_id, entry.pet_id, entry.kind, entry.amount,
                 entry.balance_after, entry.reason, entry.created_at),
            )
            self._db.conn.execute(
                "INSERT INTO pet_activity_events (event_id, pet_id, event_type, summary, metadata_json, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (event.event_id, event.pet_id, event.event_type, event.summary,
                 json.dumps(event.metadata, ensure_ascii=False), event.created_at),
            )
            self._db.conn.commit()
        else:
            self._save_jsonl_food(entry)
            self._save_jsonl_event(event)
            self._update_jsonl_pet_state(pet_id, new_state)

        pet.state = new_state
        return PetActionResult(ok=True, pet=pet, state=new_state)

    def care_pet(self, pet_id: str, action: str = "pat") -> PetActionResult:
        """Perform a care action on a pet (does not spend compute food)."""
        if action not in _CARE_ACTIONS:
            return PetActionResult(ok=False, reason_label="invalid_care_action")

        pet = self.get_pet(pet_id)
        if not pet:
            return PetActionResult(ok=False, reason_label="pet_not_found")

        now = self._now()
        d_hunger, d_energy, d_mood, d_bond = _CARE_EFFECTS[action]

        new_state = PetState(
            pet_id=pet_id,
            hunger=_clamp(pet.state.hunger + d_hunger),
            energy=_clamp(pet.state.energy + d_energy),
            mood=_clamp(pet.state.mood + d_mood),
            bond=_clamp(pet.state.bond + d_bond),
            growth_level=pet.state.growth_level,
            compute_food_balance=pet.state.compute_food_balance,
            updated_at=now,
        )

        event = PetActivityEvent(
            event_id=self._next_event_id(),
            pet_id=pet_id,
            event_type="care",
            summary=f"care: {action}",
            metadata={"action": action},
            created_at=now,
        )

        if self._db:
            self._db.conn.execute(
                "UPDATE pet_states SET hunger=?, energy=?, mood=?, bond=?, updated_at=? WHERE pet_id=?",
                (new_state.hunger, new_state.energy, new_state.mood,
                 new_state.bond, now, pet_id),
            )
            self._db.conn.execute(
                "INSERT INTO pet_activity_events (event_id, pet_id, event_type, summary, metadata_json, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (event.event_id, event.pet_id, event.event_type, event.summary,
                 json.dumps(event.metadata, ensure_ascii=False), event.created_at),
            )
            self._db.conn.commit()
        else:
            self._save_jsonl_event(event)
            self._update_jsonl_pet_state(pet_id, new_state)

        pet.state = new_state
        return PetActionResult(ok=True, pet=pet, state=new_state)

    def list_food_ledger(self, pet_id: str, limit: int = 20) -> list[FoodLedgerEntry]:
        """List food ledger entries for a pet."""
        if self._db:
            rows = self._db.conn.execute(
                "SELECT * FROM pet_food_ledger WHERE pet_id = ? ORDER BY created_at DESC LIMIT ?",
                (pet_id, limit),
            ).fetchall()
            return [_row_to_food_entry(row) for row in rows]
        # JSONL fallback
        if not self._jsonl_path:
            return []
        food_file = self._jsonl_path / "pet_food_ledger.jsonl"
        all_entries = read_jsonl(food_file)
        matching = [FoodLedgerEntry.from_dict(e) for e in all_entries if e.get("pet_id") == pet_id]
        return list(reversed(matching[-limit:]))

    def list_activity_events(self, pet_id: str, limit: int = 20) -> list[PetActivityEvent]:
        """List activity events for a pet."""
        if self._db:
            rows = self._db.conn.execute(
                "SELECT * FROM pet_activity_events WHERE pet_id = ? ORDER BY created_at DESC LIMIT ?",
                (pet_id, limit),
            ).fetchall()
            return [_row_to_activity_event(row) for row in rows]
        # JSONL fallback
        if not self._jsonl_path:
            return []
        events_file = self._jsonl_path / "pet_activity_events.jsonl"
        all_events = read_jsonl(events_file)
        matching = [PetActivityEvent.from_dict(e) for e in all_events if e.get("pet_id") == pet_id]
        return list(reversed(matching[-limit:]))

    # --- Relationship memory ---

    def _next_memory_id(self) -> str:
        if self._db:
            rows = self._db.conn.execute("SELECT memory_id FROM pet_relationship_memories").fetchall()
            max_id = 0
            for row in rows:
                raw = str(row[0])
                if raw.startswith(_RELATIONSHIP_MEMORY_PREFIX):
                    try:
                        max_id = max(max_id, int(raw[len(_RELATIONSHIP_MEMORY_PREFIX):]))
                    except ValueError:
                        pass
            return f"{_RELATIONSHIP_MEMORY_PREFIX}{max_id + 1}"
        max_id = 0
        if self._jsonl_path:
            mem_file = self._jsonl_path / "pet_relationship_memories.jsonl"
            for entry in read_jsonl(mem_file):
                raw = str(entry.get("memory_id", ""))
                if raw.startswith(_RELATIONSHIP_MEMORY_PREFIX):
                    try:
                        max_id = max(max_id, int(raw[len(_RELATIONSHIP_MEMORY_PREFIX):]))
                    except ValueError:
                        pass
        return f"{_RELATIONSHIP_MEMORY_PREFIX}{max_id + 1}"

    def add_relationship_memory(
        self,
        pet_id: str,
        kind: str,
        summary: str,
        source: str = "",
        importance: int = 5,
        metadata: Optional[dict] = None,
    ) -> Optional[PetRelationshipMemory]:
        """Record a relationship memory. Returns None if validation fails."""
        # Validate kind
        if kind not in _RELATIONSHIP_MEMORY_KINDS:
            return None
        # Validate and bound summary
        if not summary or not isinstance(summary, str):
            return None
        summary = summary.strip()[:_RELATIONSHIP_MEMORY_SUMMARY_MAX]
        if not summary:
            return None
        # Reject secret-like text
        if is_sensitive_text(summary):
            return None
        # Validate and bound source
        if source and isinstance(source, str):
            source = source.strip()[:_RELATIONSHIP_MEMORY_SOURCE_MAX]
            if is_sensitive_text(source):
                return None
        else:
            source = ""
        # Validate importance
        if not isinstance(importance, int):
            importance = 5
        importance = max(1, min(10, importance))
        # Validate metadata
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            return None
        # Reject secret-like text in metadata values
        for k, v in metadata.items():
            if isinstance(v, str) and is_sensitive_text(v):
                return None
        # Check pet exists
        pet = self.get_pet(pet_id)
        if not pet:
            return None

        now = self._now()
        memory_id = self._next_memory_id()
        mem = PetRelationshipMemory(
            memory_id=memory_id,
            pet_id=pet_id,
            kind=kind,
            summary=summary,
            source=source,
            importance=importance,
            metadata=metadata,
            created_at=now,
        )

        if self._db:
            self._db.conn.execute(
                "INSERT INTO pet_relationship_memories "
                "(memory_id, pet_id, kind, summary, source, importance, metadata_json, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (mem.memory_id, mem.pet_id, mem.kind, mem.summary, mem.source,
                 mem.importance, json.dumps(mem.metadata, ensure_ascii=False), mem.created_at),
            )
            self._db.conn.commit()
        else:
            if self._jsonl_path:
                self._jsonl_path.mkdir(parents=True, exist_ok=True)
                mem_file = self._jsonl_path / "pet_relationship_memories.jsonl"
                with open(mem_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(mem.to_dict(), ensure_ascii=False) + "\n")

        # Also record as activity event
        event = PetActivityEvent(
            event_id=self._next_event_id(),
            pet_id=pet_id,
            event_type="relationship_memory",
            summary=f"{kind}: {summary[:80]}",
            metadata={"kind": kind, "memory_id": memory_id},
            created_at=now,
        )
        if self._db:
            self._db.conn.execute(
                "INSERT INTO pet_activity_events (event_id, pet_id, event_type, summary, metadata_json, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (event.event_id, event.pet_id, event.event_type, event.summary,
                 json.dumps(event.metadata, ensure_ascii=False), event.created_at),
            )
            self._db.conn.commit()
        else:
            self._save_jsonl_event(event)

        return mem

    def list_relationship_memories(self, pet_id: str, limit: int = 20) -> list[PetRelationshipMemory]:
        """List relationship memories for a pet, most recent first."""
        limit = max(1, min(50, limit))
        if self._db:
            rows = self._db.conn.execute(
                "SELECT * FROM pet_relationship_memories WHERE pet_id = ? ORDER BY created_at DESC LIMIT ?",
                (pet_id, limit),
            ).fetchall()
            return [_row_to_relationship_memory(row) for row in rows]
        # JSONL fallback
        if not self._jsonl_path:
            return []
        mem_file = self._jsonl_path / "pet_relationship_memories.jsonl"
        all_mems = read_jsonl(mem_file)
        matching = [PetRelationshipMemory.from_dict(m) for m in all_mems if m.get("pet_id") == pet_id]
        return list(reversed(matching[-limit:]))
