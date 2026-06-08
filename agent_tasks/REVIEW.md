# TASK-157 + TASK-158 CCB Review

**Status: APPROVED**

## Summary

Pet Room MVP (TASK-157) adds local HTTP pet API and WebUI. Eval coverage (TASK-158) adds 13 deterministic offline evals. Prior activity-limit blocker fixed with clamping + comprehensive edge-case tests.

## Security Review

| Concern | Status | Evidence |
|---------|--------|----------|
| Stored HTML injection | ✅ Safe | `loadPetActivity` uses `escapeHtml` for event data rendering (line 586-588 in index.html). `eval_pet_activity_no_html_injection` verifies. |
| API auth | ✅ Correct | POST mutation endpoints require `Authorization: Bearer <token>` when `NORA_API_TOKEN` is set. GET `/pet/current` and `/pet/activity` are public by design. `eval_pet_http_auth_guards_mutation` verifies 401/200 behavior. |
| Secret/no-leak | ✅ Safe | `eval_pet_http_no_secret_leak`, `eval_pet_activity_bounded_no_secret_leak`, `eval_pet_http_create_identity_safe` verify no `sk-`, `AKIA`, `Bearer`, `eyJ`, `api_key`, `api_token` in outputs. Secret-like pet names rejected. |
| Bounded output | ✅ Safe | `/pet/activity` limit clamped to `max(1, min(50, limit))` (line 665 in http_server.py). Eval tests default, huge (99999), zero, negative, malformed limits. |
| Path/static safety | ✅ Safe | `_serve_file` validates resolved path under `static_root` (line 596-598). |
| Rate/auth consistency | ✅ Correct | POST checks auth then rate limit. GET endpoints public by design. |

## Product/Runtime Correctness

- **PetStore sole mutation path**: All HTTP handlers delegate to `self.pet_store` methods. No direct state mutation.
- **Deterministic state**: Pet creation/feeding/care through PetStore maintains deterministic state.
- **No model-driven pet mutation**: State changes only via explicit API calls.
- **No payment-pressure copy**: UI shows "Add Demo Food", no monetization language.

## API Correctness

- **Type validation → 400**: `eval_pet_http_rejects_invalid_amount_type` verifies string/bool/negative/float amounts rejected. `eval_pet_http_rejects_invalid_identity_shape` verifies empty name, missing name, wrong types rejected.
- **Read endpoints safe**: `/pet/current` creates default pet if none (documented). `/pet/activity` read-only.

## UI Correctness

- **Pet Room isolation**: Separate div toggles visibility. Chat/task/memory views preserved.
- **Auth headers**: `eval_pet_webui_auth_header_wiring` verifies fetch calls use `authHeaders()`.

## Eval Quality (TASK-158)

- **Skip behavior**: `_skip_if_no_pet_http()` checks for `_handle_pet_current` attribute, skips gracefully when TASK-157 absent.
- **Coverage**: 13 evals (8 HTTP API + 2 WebUI smoke + 3 security hardening).
- **Assertions**: Concrete checks on status codes, field values, secret absence, limit clamping. No brittle/weak assertions.
- **Combined validation**: A+B combined → 637 passed, 0 failed, 0 skipped.

## Blocker Fix Verified

**Activity limit clamping** (`/pet/activity?limit=...`):
- Implementation: `limit = max(1, min(50, limit))` with fallback to 20 for non-integer (line 660-665 in http_server.py).
- A tests: `test_pet_activity_huge_limit_bounded`, `test_pet_activity_negative_limit_clamped`, `test_pet_activity_zero_limit_clamped`, `test_pet_activity_string_limit_no_crash`.
- B eval: `pet_http_activity_bounded` covers default, huge, zero, negative, malformed limits.

## Findings

No blocking issues. Implementation is secure, well-tested, and follows project conventions. All prior blockers resolved.

## Verification Summary

- A: 276 tests OK, 624 evals passed, git diff clean
- B: 230 tests OK (TASK-157 absent), 13 evals skipped correctly
- Combined: 637 evals passed, 0 failed, 0 skipped

## Integration Recommendation

Safe to merge. Both workers' changes are complementary (A = runtime, B = evals) and validated together.
