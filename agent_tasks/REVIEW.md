# TASK-179A/179B Review — Pet Room Deterministic Skill Ability Shelf

**Status: APPROVED**

## Summary

TASK-179A adds a read-only skill ability shelf derived from `identity.skills`. TASK-179B adds 6 evals covering markers, mapping rules, read-only, no marketplace/surveillance copy, stale content cleanup, and secret-like filtering. All review criteria satisfied.

## Findings

### 1. Read-Only, DOM/Text-Only, Derived from identity.skills

- `skillCardsFromIdentity(identity, state)` is a pure function: reads `identity.skills` array, filters/sanitizes, returns card objects. No fetch, no mutation.
- `renderSkillShelf` builds HTML with `escapeHtml()` for icon and name, sets `innerHTML` and `data-skill-count`.
- Called from `renderPet()` — no extra HTTP calls, no food debit, no activity/memory writes.

### 2. Stale Card Cleanup Fix

`renderSkillShelf` handles empty/malformed skills correctly:
- When `cards.length === 0`: clears `listEl.innerHTML = ''`, shows empty state, returns.
- When cards exist: hides empty state, rebuilds HTML.
- `eval_skill_shelf_no_stale_content_on_empty` uses brace-counting to verify `innerHTML` clear happens BEFORE return in the empty branch.

### 3. Secret-Like Skill Filtering

`isSecretLike(text)` checks against 9 patterns: `sk-`, `bearer`, `api_key`, `token`, `secret`, `password`, `credential`, `private_key`, `auth`.

`skillCardsFromIdentity` rejects:
- Non-string items
- Empty/whitespace-only strings
- Names > 50 chars
- Names with non-alphanumeric characters (except dash/underscore/space)
- Secret-like names (via `isSecretLike`)

`eval_skill_shelf_rejects_secret_like_skills` verifies `SECRET_PATTERNS` or `isSecretLike` exists in code, covers required patterns, and is called in the mapping function.

### 4. Eval Coverage (6 evals)

| Eval | What it locks |
|------|---------------|
| `pet_skill_shelf_markers_present` | 6 required DOM markers |
| `skill_shelf_mapping_rules` | Skills reference, fallback, sanitization, escapeHtml/textContent |
| `skill_shelf_read_only_no_tool_execution` | No fetch/plugin/food/voice/memory/activity/microphone/camera/service-worker |
| `skill_shelf_no_marketplace_native_pwa_or_surveillance_copy` | No marketplace/plugin-store/premium/voice/recording/3D/VRM copy |
| `skill_shelf_no_stale_content_on_empty` | Empty branch clears innerHTML before return |
| `skill_shelf_rejects_secret_like_skills` | Secret patterns exist and are called in mapping function |

### 5. Smoke Tests (15 tests)

DOM markers, valid skills, unknown skill default icon, empty/null/undefined/non-string/long-name/special-chars inputs, render with skills, empty state, stale card cleanup, secret-like filtering.

### 6. No Weakening of TASK-178

TASK-178 interaction reaction evals (4) remain unchanged in the diff. No coverage regression.

### 7. B_DONE Report Mismatch

B_DONE says "4 deterministic evals" but code has 6. Code diff is authoritative — not blocking.

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 372 tests OK
python3 evals/run_evals.py → 714 passed, 0 failed, 0 skipped
git diff --check → clean
rg forbidden-copy → only negative safety assertions
```
