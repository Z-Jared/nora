# TASK-178A/178B Review — Deterministic Interaction Reaction Surface

**Status: APPROVED**

## Summary

TASK-178A adds deterministic interaction reactions derived from bounded pet state and action type. TASK-178B adds 4 evals locking the reaction contract. All review criteria satisfied.

## Findings

### Deterministic & Read-Only
- `reactionFromInteraction(action, state, result)` is pure: bounded state + action key → reaction text. No fetch, no state mutation, no provider calls.
- Uses `clampState()` for numeric normalization (NaN/Infinity/negative/over-100/strings/booleans → safe defaults).
- `applyReaction` uses `textContent` for all dynamic text, sets `data-reaction` attribute.

### Bounded to Pet State + Action
- Maps specific actions (feed, pat, comfort, rest, play, food_added, shared_moment) to deterministic text based on state thresholds.
- Falls back to "neutral" for unknown actions. Failed result → "failed" reaction.
- No LLM calls, no dynamic content beyond state + action.

### add-food Normalization Bridge
- `petAction('/pet/add-food', ...)` normalizes `add-food` endpoint to `food_added` reaction key via `reactionKey` variable before calling `applyReaction`.
- Locked by `eval_interaction_reaction_mapping_rules` with brace-counting validation of the full `petAction` function body.

### Eval Coverage (4 evals)
1. **`pet_room_reaction_markers_present`** — DOM markers: pet-room-reaction, text, meta
2. **`interaction_reaction_mapping_rules`** — petAction normalization bridge (add-food→food_added), reaction mapper handles all required action branches (feed, pat, comfort, rest, play, food_added), references state/result, has fallback
3. **`interaction_reaction_read_only_no_extra_fetch`** — No forbidden patterns in reaction function bodies (fetch, voice-preview, relationship-memory, activity, microphone, camera, service-worker, etc.)
4. **`interaction_reaction_no_voice_native_pwa_or_surveillance_copy`** — No voice clone/recording/microphone/camera/screen/location/marketplace/3D/VRM/service-worker/notification copy

### Smoke Tests (24 tests)
- DOM markers, 6 action variants (feed×3, pat×2, comfort, rest, play×2, food_added, shared_moment), failed, neutral/unknown, null/undefined/malformed state, null result, meta content, textContent, add-food normalization bridge.

### Scope Compliance
- ✅ No new HTTP endpoint, real TTS, audio, recording, PWA/service worker, notification, desktop/native, billing, marketplace, 3D/VRM
- ✅ B_DONE says "4 deterministic evals" — code has 4. Consistent.

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 356 tests OK
python3 evals/run_evals.py → 708 passed, 0 failed, 0 skipped
git diff --check → clean
rg forbidden-copy → only negative safety assertions
```
