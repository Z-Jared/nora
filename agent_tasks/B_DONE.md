# B DONE — TASK-178B

**Status:** Complete — PM second review coverage-strengthening revision

## Summary

Strengthened `interaction_reaction_mapping_rules` to lock the add-food integration-path contract using brace-counting extraction of `petAction` function. All 4 evals active/pass when combined with TASK-178A.

## Strengthened Eval: `interaction_reaction_mapping_rules`

**Problem:** First fix checked for `add-food`/`food_added` anywhere in the mapper body, but the real bug was in the UI integration path: `petAction` derived `actionName = 'add-food'` and passed it directly to `applyReaction`, which didn't have an `add-food` branch → neutral fallback.

**Fix:** Now uses brace-counting to extract the full `petAction` function body and requires:
- Both `add-food` AND `food_added` present (proves the bridge `actionName === 'add-food' ? 'food_added' : actionName` exists)
- `applyReaction` is called with the normalized key
- Mapper function handles `food_added`, `feed`, 2+ care actions, state/result reference, and fallback

**Verification the eval catches the broken implementation:**
- Broken impl: `add-food` present (from `endpoint.split('/').pop()`), `food_added` NOT present → eval FAILS ✅
- Fixed impl: both `add-food` and `food_added` present (bridge exists) → eval PASSES ✅

## Read-Only Eval Fix

Removed `add-food` from forbidden list in `interaction_reaction_read_only_no_extra_fetch` — it's a safe normalization string, not an extra fetch/mutation.

## Verification

### Own worktree (no TASK-178A)

```
python3 evals/run_evals.py           → 704 passed, 0 failed, 4 skipped
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 333 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-178A)

```
python3 evals/run_evals.py           → 4/4 reaction evals PASS
```

### `rg` scan

All hits are negative safety assertions. No promotional or enabling language.
