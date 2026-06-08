# B DONE — TASK-162

**Status:** Complete — combined check PASSED

## Summary

Fixed all evals to match TASK-161's actual contract: `/pet/food-status` endpoint with `_handle_pet_food_status` handler. Added deterministic cost assertions. Combined A+B eval passes all 7 token_food evals.

## Fixes Applied

1. **Guard**: `_handle_pet_food_status` instead of `_handle_pet_estimate`
2. **Endpoint**: `/pet/food-status` instead of `/pet/estimate`
3. **Response shape**: Asserts `balance`, `cost`, `can_run`, `shortfall`, `reason_label`, `message`
4. **Deterministic costs**: `feed=100`, `chat=25`, `voice=80`, `work=150`
5. **New eval**: `token_food_deterministic_costs` verifies all 4 known action costs

## Evals (7)

1. **`token_food_estimate_read_only`** — Repeated `/pet/food-status` calls do not mutate balance.
2. **`token_food_estimate_response_shape`** — Response includes all required fields, cost=100 for feed, can_run=True with sufficient balance.
3. **`token_food_deterministic_costs`** — Known actions have exact costs: feed=100, chat=25, voice=80, work=150.
4. **`token_food_insufficient_no_mutation`** — Zero balance: can_run=False, shortfall>0, feed rejected, balance unchanged.
5. **`token_food_unknown_action_bounded`** — Unknown action bounded (<2000 chars), secret-like input not leaked.
6. **`token_food_webui_balance_visible`** — Pet Room HTML shows balance markers.
7. **`token_food_no_manipulative_copy`** — No manipulative food/token purchase copy.

## Verification Results

### Own worktree (ccb/claude-b, no TASK-161)

```
python3 evals/run_evals.py           → 629 passed, 22 failed, 7 skipped
                                      (7 skipped = token_food evals)
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke → 276 tests OK
git diff --check                     → clean
```

### Combined check (applied onto Claude A's TASK-161)

```
python3 evals/run_evals.py           → 636 passed, 22 failed, 0 skipped

All 7 token_food evals PASS:
  PASS token_food_estimate_read_only
  PASS token_food_estimate_response_shape
  PASS token_food_deterministic_costs
  PASS token_food_insufficient_no_mutation
  PASS token_food_unknown_action_bounded
  PASS token_food_webui_balance_visible
  PASS token_food_no_manipulative_copy

(22 failures = pre-existing prompt_toolkit errors, unrelated)
```
