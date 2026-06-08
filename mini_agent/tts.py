"""TTS adapter protocol with deterministic text fallback for Nora.

Provides TTSResult, TTSAdapter protocol, TextFallbackTTSAdapter,
and deterministic cost/preview helpers.  No real TTS, audio playback,
microphone access, or provider calls are made.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Voice action cost multiplier (from PHASE_2_VOICE_PRESENCE_PLAN)
_VOICE_COST_PER_CHAR_DIVISOR = 10
_VOICE_SPEED_MULTIPLIERS = {"slow": 1.2, "normal": 1.0, "fast": 0.8}
_DEFAULT_VOICE_COST_MULTIPLIER = 1.0
VOICE_PREVIEW_TEXT_MAX_LEN = 500


@dataclass
class TTSResult:
    """Result of a TTS or text-fallback operation."""
    text: str
    audio_bytes: Optional[bytes] = None
    duration_ms: int = 0
    cost_tokens: int = 0
    source: str = "text_fallback"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "has_audio": self.audio_bytes is not None,
            "duration_ms": self.duration_ms,
            "cost_tokens": self.cost_tokens,
            "source": self.source,
            "error": self.error,
        }


def estimate_voice_cost(text: str, voice_profile: Optional[dict] = None) -> int:
    """Deterministic token cost estimate for speaking text.

    Cost = len(text) // 10 * speed_multiplier.
    Returns 0 for empty/invalid text.
    """
    if not text or not isinstance(text, str):
        return 0
    speed = "normal"
    if voice_profile and isinstance(voice_profile, dict):
        speed = voice_profile.get("speed", "normal")
    multiplier = _VOICE_SPEED_MULTIPLIERS.get(speed, _DEFAULT_VOICE_COST_MULTIPLIER)
    return max(0, int(len(text) // _VOICE_COST_PER_CHAR_DIVISOR * multiplier))


def get_mood_context(pet_state: Optional[dict] = None) -> dict:
    """Derive mood context from pet state for TTS expression hints.

    Returns a bounded dict with mood/energy/hunger levels and expression hint.
    No pet state mutation.
    """
    if not pet_state or not isinstance(pet_state, dict):
        return {"mood": "neutral", "energy": "normal", "hunger": "normal", "expression": "calm"}

    mood = pet_state.get("mood", 50)
    energy = pet_state.get("energy", 50)
    hunger = pet_state.get("hunger", 50)

    mood_label = "happy" if mood >= 70 else "neutral" if mood >= 40 else "low"
    energy_label = "high" if energy >= 70 else "normal" if energy >= 30 else "tired"
    hunger_label = "satisfied" if hunger <= 40 else "normal" if hunger <= 65 else "hungry"

    if mood >= 70 and energy >= 50:
        expression = "cheerful"
    elif energy < 30:
        expression = "tired"
    elif hunger > 65:
        expression = "hungry"
    elif mood < 40:
        expression = "subdued"
    else:
        expression = "calm"

    return {
        "mood": mood_label,
        "energy": energy_label,
        "hunger": hunger_label,
        "expression": expression,
    }


class TextFallbackTTSAdapter:
    """Deterministic text-only TTS fallback adapter.

    Always available locally. Generates no audio bytes, no network calls,
    no provider payloads, and no recordings.
    """

    def available(self) -> bool:
        """Text fallback is always available."""
        return True

    def speak(self, text: str, voice_profile: Optional[dict] = None,
              pet_state: Optional[dict] = None) -> TTSResult:
        """Return text fallback result. No audio generated, no state mutation."""
        if not text or not isinstance(text, str):
            return TTSResult(text="", source="text_fallback", error="empty text")

        cost = estimate_voice_cost(text, voice_profile)
        mood_ctx = get_mood_context(pet_state)

        return TTSResult(
            text=text,
            audio_bytes=None,
            duration_ms=0,
            cost_tokens=cost,
            source="text_fallback",
        )

    def preview(self, text: str, voice_profile: Optional[dict] = None,
                pet_state: Optional[dict] = None) -> dict:
        """Return bounded preview metadata for HTTP endpoint.

        No audio, no state mutation, no food debit.
        """
        if not text or not isinstance(text, str):
            return {"error": "empty text", "has_audio": False, "source": "text_fallback"}

        cost = estimate_voice_cost(text, voice_profile)
        mood_ctx = get_mood_context(pet_state)

        # Build safe voice profile summary (no secrets)
        safe_profile = {}
        if voice_profile and isinstance(voice_profile, dict):
            for key in ("voice_id", "speed", "tone", "pitch"):
                val = voice_profile.get(key)
                if val is not None:
                    safe_profile[key] = val

        return {
            "text": text,
            "has_audio": False,
            "source": "text_fallback",
            "cost_tokens": cost,
            "voice_profile": safe_profile,
            "mood_context": mood_ctx,
            "no_audio_reason": "text fallback only — no TTS provider configured",
            "no_network_call": True,
            "no_recording": True,
            "requires_user_confirmation": True,
            "confirmation_kind": "text_fallback_voice_preview",
            "audio_requires_confirmation": True,
            "provider_status": "not_configured_text_fallback",
            "food_debit": False,
        }
