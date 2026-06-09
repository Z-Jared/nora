# TASK-177A: Pet Room deterministic room-load greeting — DONE

## Summary

Added a deterministic room-load greeting to the Pet Room that derives from bounded pet state (mood, energy, hunger, bond) and a coarse local time bucket. Greeting is text-only, read-only, and uses DOM text APIs.

## Changes

### `mini_agent/static/index.html`

**New JS functions:**
- `roomGreetingFromState(state, date)` — returns `{key, text, meta}` from bounded state + time bucket
  - Time buckets: `morning` (5-12), `midday` (12-17), `evening` (17-21), `night` (21-5)
  - State-sensitive variants: hungry (snack mention), low-energy (tired), high-mood+bond (cheerful), high-mood (good mood), low-mood (company), neutral (simple greeting)
  - Uses `clampState()` for numeric normalization (NaN/Infinity/negative/over-100/strings/booleans → safe defaults)
- `applyRoomGreeting(state, date)` — sets DOM markers via textContent + data-greeting attribute

**New CSS:**
- `.pet-room-greeting`, `.pet-room-greeting-text`, `.pet-room-greeting-meta`

**New DOM markers:**
- `pet-room-greeting` — root element with `data-greeting` attribute
- `pet-room-greeting-text` — greeting text
- `pet-room-greeting-meta` — state detail meta text

**Integration:**
- `applyRoomGreeting(st)` called in `renderPet()` after `applyPresence()`

### `tests/test_webui_smoke.py`

16 new tests:
- `test_room_greeting_dom_markers_exist` — DOM markers exist
- `test_room_greeting_morning_happy` — morning + high mood/bond → cheerful
- `test_room_greeting_midday_default` — midday + neutral → simple greeting
- `test_room_greeting_evening` — evening bucket
- `test_room_greeting_night` — night bucket
- `test_room_greeting_hungry_variant` — high hunger → snack mention
- `test_room_greeting_low_energy_variant` — low energy → tired
- `test_room_greeting_low_mood_variant` — low mood → company-seeking
- `test_room_greeting_high_mood_no_bond` — high mood without bond
- `test_room_greeting_null_state` — null state defaults safely
- `test_room_greeting_undefined_state` — undefined state defaults safely
- `test_room_greeting_malformed_state` — NaN/Infinity/negative/string → safe defaults, no raw values
- `test_room_greeting_no_date_defaults_to_now` — missing date → current time
- `test_apply_room_greeting_sets_dom` — sets text + data-greeting
- `test_apply_room_greeting_uses_dom_text` — uses textContent
- `test_room_greeting_text_is_plain` — no HTML tags

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server
Ran 333 tests in 121.716s — OK

git diff --check
(clean)

rg -n "voice clone|clone voice|..." mini_agent/static/index.html tests/test_webui_smoke.py
(no matches)
```
