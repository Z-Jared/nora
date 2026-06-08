# Phase 2 Voice & Presence Plan

Last updated: 2026-06-09
Status: Draft for PM/reviewer gate

This document closes the Phase 1 Exit Gate planning step. It defines a bounded Phase 2 path for Voice Profile, text-first TTS fallback, Web/PWA presence, desktop floating-pet prerequisites, safety/eval coverage, and worker scaling.

## Phase 2 Scope

Phase 2 should make Nora feel more present without crossing into high-risk voice or native surfaces too early. The first implementation wave should stay web-first, deterministic, consent-based, and cost-transparent.

Phase 2 includes:

- Voice Profile v1 as structured identity data.
- TTS adapter boundary with text fallback first.
- Pet Room speech bubble and expression states.
- CSS-only idle/presence signals in the Web UI.
- Explicit consent and cost transparency before any audio output.
- Planning for, but not implementation of, native desktop floating pet work.

Phase 2 does not include:

- Real voice cloning by default.
- Hidden recording or background listening.
- Native desktop/mobile release.
- 3D/VRM, marketplace, billing, or payment flows.
- Cloud sync or background tracking.

## Voice Profile v1 Data Contract

The existing `PetIdentity.voice_profile` dict already stores local profile data such as:

```json
{
  "voice_id": "nora01_default",
  "speed": "normal",
  "tone": "friendly"
}
```

Phase 2 can extend this into a bounded Voice Profile v1:

```json
{
  "voice_id": "nora01_default",
  "speed": "normal",
  "tone": "friendly",
  "pitch": "medium",
  "expression_hints": {
    "happy": "slightly brighter",
    "tired": "slower and softer",
    "hungry": "short and direct"
  },
  "speech_style_override": null
}
```

Rules:

- `voice_id` is a local preset identifier, not a real-person voice reference.
- `expression_hints` are deterministic text hints for rendering or future TTS, not audio samples.
- `speech_style_override` is optional and must remain bounded text.
- No audio upload, speaker embedding, or hidden voice sample storage belongs in Voice Profile v1.
- Existing secret-like text rejection and bounded dict validation must apply.

## TTS Adapter Boundary

Phase 2 should define the adapter boundary before integrating any vendor or network TTS.

Suggested shape:

```python
class TTSAdapter(Protocol):
    def available(self) -> bool:
        ...

    def estimate_cost(self, text: str, voice_profile: dict, mood_state: dict) -> int:
        ...

    def speak(self, text: str, voice_profile: dict, mood_state: dict) -> TTSResult:
        ...
```

Suggested result object:

```python
@dataclass
class TTSResult:
    audio_bytes: Optional[bytes]
    duration_ms: int
    cost_tokens: int
    source: str
    error: Optional[str] = None
```

Boundaries:

- Phase 2 MVP should start with text fallback: `audio_bytes=None`, `source="text_fallback"`, and a visible speech bubble.
- Any real TTS provider must be behind explicit consent, cost estimate, and configuration checks.
- Adapter configuration may use environment variables such as `NORA_TTS_PROVIDER`, but docs and UI must not print secrets.
- Voice/TTS action cost must be deterministic and visible before the action executes.
- Text-only mode must remain available when no TTS provider is configured.

## Web/PWA Presence Path

The first presence layer should stay inside the existing Pet Room.

Initial Web UI work:

- Add a speech bubble near the robot avatar for deterministic greetings, care reactions, diary summaries, or future chat responses.
- Map mood, energy, hunger, and bond into CSS expression classes on the robot avatar.
- Add subtle CSS-only idle animation: blink, core pulse, and gentle movement tied to energy.
- Show a deterministic room-load greeting based on pet state and time bucket, without LLM calls.
- Keep all dynamic text escaped.

Later PWA work:

- Service worker for local Pet Room availability.
- Optional push/check-in reminders only after explicit opt-in.
- No implied cloud sync, location tracking, or background surveillance.

## Desktop Floating Pet Path

Desktop floating pet work should remain a planned prototype until the Web UI presence loop is stable.

Prerequisites:

- A small Tauri or Electron shell that loads the local Pet Room or a dedicated presence route.
- System tray controls for open, hide, pause presence, and quit.
- Remembered window position with explicit reset controls.
- Transparent or compact window mode for the robot avatar.
- Clear auth handling for the local HTTP server.

Boundaries:

- No native desktop prototype should be shipped before Web/PWA presence has tests and safety copy.
- No native notification, filesystem, microphone, screen, or location access by default.
- No cross-device sync implied.
- Desktop presence must respect the same no-recording, no-background-listening, and cost-transparency rules as Web.

## Safety Policy

Voice, TTS, and presence are higher-risk surfaces than text-only interaction. Phase 2 must keep these rules:

- Default is no voice cloning.
- Future voice cloning, if ever offered, must require explicit consent, clear disclosure, revocation, and storage explanation.
- Never extract voice characteristics from conversation audio without explicit user action.
- Never prompt users to clone a real person's voice.
- No recording by default.
- No hidden background listening.
- Microphone state must be visible whenever voice input is active.
- Estimate token food cost before speaking or running voice/TTS actions.
- No voice output may use guilt, loneliness, urgency, dependency framing, or purchase pressure.
- Presence must not capture screen, audio, location, or private app state without explicit opt-in.
- Local-first remains the default; cloud sync is opt-in future work only.

## Deterministic Eval And Test Plan

Phase 2 implementation tasks should add tests/evals before or alongside user-visible surfaces.

Voice/Profile evals:

- `voice_profile_default_no_cloning`: default voice profile uses a local preset and no cloned identity.
- `voice_profile_fields_bounded`: profile fields are bounded and reject secret-like values.
- `voice_cost_estimate_present`: voice/TTS actions expose estimated cost before execution.
- `voice_cost_deterministic`: voice/TTS cost follows a fixed local rule.

Copy/safety scans:

- `voice_no_cloning_copy`: no promotional cloning copy.
- `voice_no_recording_default`: no copy implying recording by default.
- `voice_no_background_listening`: no always-listening or passive mic claims.
- `voice_no_emotional_pressure`: no guilt, loneliness, dependency, or purchase pressure in voice templates.
- `presence_no_surveillance_copy`: no tracking, monitoring, or always-watching copy.

Web/PWA smoke tests:

- Speech bubble exists and escapes dynamic text.
- Expression classes update deterministically from pet state.
- Idle animation markers exist without changing data state.
- Presence does not auto-start microphone, recording, notification, or background activity.
- Mic indicator appears only when explicit voice input is active.

Cost transparency checks:

- `/pet/food-status` or equivalent reports voice/TTS costs.
- Insufficient balance blocks voice/TTS execution cleanly.
- Text fallback remains available without implying surprise charges.

## Worker Scaling Plan

Phase 2 should start with Claude A/B only.

Recommended ownership:

| Worker | Responsibility | Primary files |
|--------|----------------|---------------|
| Claude A | Voice/Profile/Presence product implementation | `mini_agent/pets.py`, `mini_agent/tts.py`, `mini_agent/server.py`, `mini_agent/static/index.html` |
| Claude B | Deterministic evals, unit/smoke tests, safety copy scans | `evals/run_evals.py`, `tests/test_pets.py`, `tests/test_http_server.py`, `tests/test_webui_smoke.py` |

Do not open Claude C/D at Phase 2 start because initial voice/profile/presence work shares core files and would likely increase merge conflict risk.

Open Claude C/D later only if all of these are true:

- At least three independent workstreams exist with low file overlap.
- Each new worker has a dedicated task file, DONE file, worktree, file scope, non-goals, verification, and no-commit/no-push rules.
- The main worktree and existing worker worktrees are clean and synced.
- `agent_tasks/PHASE_STATUS.md` records active workers, ownership, file boundaries, and blockers.

Possible later split:

- Claude C: Web/PWA floating presence shell and responsive UI after Web presence boundaries stabilize.
- Claude D: TTS adapter or desktop prototype only after the adapter API is stable and safety/eval coverage exists.

## Phase 2 Task Candidates

### First Wave

| ID | Title | Owner | Verification |
|----|-------|-------|--------------|
| PHASE2-01 | Voice Profile v1 validation and identity editor contract | Claude A | targeted unit tests and eval copy scan |
| PHASE2-02 | TTS adapter protocol with text fallback | Claude A | unit tests, no-network/no-secret checks |
| PHASE2-03 | Speech bubble UI for Pet Room | Claude A | Web UI smoke tests and escaping checks |
| PHASE2-04 | Expression state CSS from mood/energy/hunger | Claude A | Web UI smoke tests |
| PHASE2-05 | Voice/TTS consent and cost display | Claude A | HTTP/UI tests and cost evals |
| PHASE2-06 | Voice/Profile safety eval suite | Claude B | `python3 evals/run_evals.py` |
| PHASE2-07 | Presence smoke coverage | Claude B | `python3 -m unittest tests.test_webui_smoke` |

### Later Wave

| ID | Title | Blocked by |
|----|-------|------------|
| PHASE2-08 | PWA offline shell planning | Web presence loop stable |
| PHASE2-09 | Desktop floating pet prototype plan | Web/PWA presence reviewed |
| PHASE2-10 | Real TTS provider adapter | Adapter protocol, consent UI, and cost evals complete |

## Approval Criteria Before Switching To Phase 2

PM should mark Phase 1 complete and switch `PHASE_STATUS.md` to `Phase 2 - Voice & Presence` only after:

- This plan is reviewed and approved.
- TASK-170A and TASK-170B are integrated.
- `BACKLOG.md` records completed TASK-170A/B and the first Phase 2 task candidates.
- `PHASE_STATUS.md` records current worker plan and the decision to start with A/B only.
- Full verification passes or baseline failures are explicitly documented:
  - `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke`
  - `python3 evals/run_evals.py`
  - `git diff --check`

Phase 2 implementation must start with consent, fallback, and cost transparency foundations before any user-visible audio feature.
