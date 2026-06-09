# TASK-176A: Pet Room CSS-only idle presence signals

## Summary

Added deterministic CSS-only idle/presence signals to the Pet Room robot avatar. Presence is derived solely from existing bounded pet state (`energy`, `hunger`, `mood`, `bond`) with no network calls, no state mutation, and no provider dependencies.

## Changes

### CSS Presence Classes (`mini_agent/static/index.html`)

Added 5 presence CSS classes that modify robot avatar animation pacing and opacity:

| Class | Trigger Condition | Visual Effect |
|-------|------------------|---------------|
| `presence-charging` | energy ≥ 80, hunger ≤ 30 | Fast core pulse, cyan eye glow, bright antenna |
| `presence-resting` | energy ≤ 25 | Slow blink (6s), dim core, dim antenna, faded arms |
| `presence-alert` | mood ≥ 70, energy ≥ 50 | Fast blink (1.5s), bright core, pulsing antenna |
| `presence-drifting` | mood < 40, energy < 50 | Slow eye fade (4s), drifting antenna rotation |
| `presence-waiting` | default/neutral | Moderate blink (2s), waiting antenna opacity cycle |

### JavaScript Functions

- `clampState(val, defaultVal)` — Bounded numeric normalizer: coerces finite numbers, clamps 0..100, rejects NaN/Infinity/strings/booleans
- `presenceFromState(st)` — Returns `{key, icon, label, detail}` from bounded numeric state via `clampState`
- `applyPresence(st)` — Applies CSS class, `data-presence` attribute, and updates DOM markers

### DOM Markers

- `pet-presence-state` — Container for presence display
- `pet-presence-icon` — Emoji icon (⚡🌙👁️🌀⏳)
- `pet-presence-label` — Text label (Charging/Resting/Alert/Drifting/Waiting)
- `pet-presence-detail` — Numeric detail text (e.g., "Energy at 85/100, hunger at 20/100 — fully charged.")
- `data-presence` attribute on `pet-avatar` root

### Integration

- `applyPresence(st)` called from `renderPet()` alongside existing `applyExpression(st)`
- No interaction with expression state, speech bubble, voice consent, food, activity, or relationship memory

## Test Results

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server
Ran 317 tests in 136.259s — OK

git diff --check
(clean)

rg scan for forbidden copy
(no matches)
```

## New Tests (20 tests added total)

### Original presence tests (12)
- `test_presence_state_dom_markers_exist` — Verifies all DOM markers exist
- `test_presence_from_state_charging` — High energy, low hunger → charging
- `test_presence_from_state_resting` — Very low energy → resting
- `test_presence_from_state_alert` — High mood, decent energy → alert
- `test_presence_from_state_drifting` — Low mood, low energy → drifting
- `test_presence_from_state_waiting` — Neutral state → waiting
- `test_presence_from_state_missing_fields` — Missing fields default safely
- `test_presence_from_state_null_state` — Null state defaults safely
- `test_apply_presence_sets_data_attribute` — Sets `data-presence` and CSS class
- `test_apply_presence_updates_dom_markers` — Updates icon/label/detail
- `test_presence_class_cycling` — Swaps classes on state change
- `test_presence_detail_uses_dom_text` — Uses textContent, not innerHTML

### Malformed state safety tests (8) — PM review fix
- `test_presence_from_state_string_values` — String values coerce to defaults
- `test_presence_from_state_nan_values` — NaN values coerce to defaults
- `test_presence_from_state_infinity_values` — Infinity clamps to 100
- `test_presence_from_state_negative_values` — Negative values clamp to 0
- `test_presence_from_state_over_100_values` — Values >100 clamp to 100
- `test_presence_from_state_boolean_values` — Boolean values coerce to defaults
- `test_presence_from_state_undefined_values` — Undefined values use defaults
- `test_clamp_state_normalizes_values` — Comprehensive clampState normalization

## Safety Boundaries

- ✅ CSS-only, deterministic — no LLM or provider calls
- ✅ No pet state/food/activity/relationship-memory/voice-preview mutation
- ✅ No microphone/camera/screen/location access
- ✅ No PWA/service worker, desktop floating pet, 3D/VRM, billing, marketplace
- ✅ Dynamic text escaped via DOM text APIs (textContent)
- ✅ Malformed state (NaN, Infinity, negatives, >100, strings, booleans) normalized via clampState
- ✅ Existing expression state, speech bubble, voice consent behavior preserved
