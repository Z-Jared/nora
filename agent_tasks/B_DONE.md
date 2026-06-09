# B DONE — TASK-184B

**Status:** Complete — all status_chips evals PASS

## Summary

Added 5 deterministic evals for Status Chips module extraction. All evals active/pass when combined with TASK-184A.

## Evals Added

1. **`status_chips_module_file_present`** — `status-chips.js` exists with native ES module exports, no build tooling.
2. **`status_chips_module_wired`** — `status-chips.js` wired in `pet-room-canvas.js` or `index.html` via native module import.
3. **`status_chips_markers_preserved`** — Required chip markers present: `pet-room-status-chip`, `chip-mood-value`, `chip-presence-value`, `chip-energy-value`, `chip-bond-value`.
4. **`status_chips_read_only_no_api_or_fetch`** — No `fetch(`, `petapi.`, `/pet/`, or mutation calls in code (comments excluded).
5. **`status_chips_no_external_or_scope_drift`** — No external URLs, build system markers, or scope drift.

## Verification

### Own worktree (no TASK-184A)

```
python3 evals/run_evals.py           → 734 passed, 0 failed, 5 skipped
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 393 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-184A)

```
python3 evals/run_evals.py           → 5/5 status_chips evals PASS
```
