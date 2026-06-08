# TASK-165 + TASK-166 CCB Review

**Status: APPROVED**

## Summary

TASK-165 adds Identity Editor MVP: `PetStore.update_identity()` with full field support, HTTP API endpoint, and Pet Room UI. TASK-166 adds 6 deterministic evals to lock the contract. All review criteria satisfied.

## Review Findings

### 1. PetStore.update_identity() Correctness

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Preserves pet_id | ✅ | `pet_id=old.pet_id` (pets.py:620) |
| Preserves created_at | ✅ | `created_at=old.created_at` (pets.py:629) |
| Preserves state (food balance) | ✅ | Only identity updated, state untouched |
| Preserves activity | ✅ | No activity table mutations |
| Preserves relationship memories | ✅ | No memory table mutations |
| Updates updated_at | ✅ | `updated_at=now` (pets.py:630) |
| Partial update preserves other fields | ✅ | Only provided kwargs override, others keep old values |

### 2. Secret-Like Text Rejection

| Field Type | Validation | Evidence |
|------------|------------|----------|
| String fields (name, species, etc.) | `_validate_text_fields` → `is_sensitive_text()` | `ValueError` raised → 400 error |
| List fields (personality_traits, skills) | `_validate_list_fields` | Each item checked |
| Dict values (voice_profile, taste_profile) | `_validate_dict_values` | Each value checked |
| HTTP handler catches ValueError | ✅ | Returns 400 with error message |

### 3. POST /pet/update-identity

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Mutation auth enforced | ✅ | POST handler uses `_check_auth()` |
| Bounded JSON response | ✅ | Returns `pet.to_dict()` |
| Docs entry | ✅ | Added to `/docs` OpenAPI spec |
| Invalid type → bounded error | ✅ | TypeError caught → 400 "invalid field types" |
| Missing pet_id → 400 | ✅ | Handler validates pet_id |
| Nonexistent pet → 400 | ✅ | `update_identity()` returns None → 400 |

### 4. Pet Room Identity Editor UI

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Escape rendering | ✅ | DOM `.value` property used (auto-escaped), `escapeHtml()` for display |
| Invalid JSON handling | ✅ | `JSON.parse()` try/catch for voice/taste profiles, shows "invalid JSON" error |
| No fake intimacy | ✅ | `eval_idedit_webui_no_marketplace_copy` checks forbidden phrases |
| No marketplace/voice cloning | ✅ | Same eval checks "marketplace", "buy avatar", "voice clone", "nft", etc. |
| No purchase pressure | ✅ | Same eval checks "pay to customize", "premium identity", "token sale" |

### 5. TASK-166 Eval Quality (6 evals)

| Eval | What it locks |
|------|---------------|
| `idedit_update_preserves_identity` | pet_id and created_at unchanged, name updated |
| `idedit_update_preserves_state` | Food balance preserved after identity update |
| `idedit_rejects_secret_input` | Secret name and personality traits rejected (400) |
| `idedit_auth_enforced` | 401 without auth, 200 with auth |
| `idedit_webui_editor_markers` | HTML contains identity editor markers |
| `idedit_webui_no_marketplace_copy` | No marketplace/voice clone/purchase copy |

All evals are deterministic, offline, and use concrete assertions. No weak/vacuous checks.

### 6. Out-of-Scope Changes

None. All changes are within TASK-165/166 scope:
- `mini_agent/pets.py` — `update_identity()` + JSONL helper
- `mini_agent/http_server.py` — `/pet/update-identity` endpoint + docs
- `mini_agent/static/index.html` — Identity Editor UI section
- `tests/test_pets.py` — 14 unit tests for update_identity
- `tests/test_http_server.py` — 7 HTTP tests for update-identity endpoint
- `evals/run_evals.py` — 6 idedit evals

## Verification Summary

- 337 unit tests OK
- 671 evals passed, 0 failed, 0 skipped
- git diff --check: clean
