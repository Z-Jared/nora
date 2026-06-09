# B DONE — TASK-186B

**Status:** Complete — stale TASK-179 eval failures fixed

## Summary

Fixed 4 stale TASK-179 skill shelf evals that failed after TASK-186A moved implementation into `skill-shelf.js`. Added `_read_skill_shelf_surface()` helper that reads combined `index.html` + `skill-shelf.js` when the module exists. All 12 skill shelf evals (6 old + 6 new) PASS combined.

## Fixes Applied

Added `_read_skill_shelf_surface()` helper and updated 4 evals:

1. **`pet_skill_shelf_markers_present`** — Now reads combined surface, finds markers in skill-shelf.js
2. **`skill_shelf_mapping_rules`** — Now reads combined surface, finds `skillCardsFromIdentity` in skill-shelf.js
3. **`skill_shelf_no_stale_content_on_empty`** — Now reads combined surface, finds `renderSkillShelf` in skill-shelf.js
4. **`skill_shelf_rejects_secret_like_skills`** — Now reads combined surface, finds `SECRET_PATTERNS`/`isSecretLike` in skill-shelf.js

## Verification

### Own worktree (no TASK-186A)

```
python3 evals/run_evals.py           → 744 passed, 0 failed, 6 skipped
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 411 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-186A)

```
python3 evals/run_evals.py           → 12/12 skill_shelf evals PASS (6 old + 6 new)
```
