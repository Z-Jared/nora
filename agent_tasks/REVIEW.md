# CCB Code Review Report

Reviewed: TASK-054 Durable recovery plan tool v1
Worker: Claude A
Status: **APPROVED**

---

## Review Scope

### 1. Read-Only Verification

**Verdict: ✅ STRICTLY READ-ONLY**

`_plan_durable_recovery_json()` implementation (lines 1178-1268):

- ✅ No task state mutation (no `upsert_task()`, no `update_status()`)
- ✅ No worker execution (no worker status changes)
- ✅ No model calls (no LLMClient usage)
- ✅ No git/file recovery (no file system operations)
- ✅ Registered with `risk="read"` permission (line 1292)
- ✅ Test `test_no_mutation_of_task_state` verifies read-only (lines 1969-1981):
  - Compares task state before and after multiple plan calls
  - Verifies status, current_step, checkpoints, steps all unchanged

### 2. Checkpoint Selection Logic

**Verdict: ✅ CORRECT**

Checkpoint selection priority (lines 1192-1216):

1. **Explicit checkpoint_id** (lines 1195-1202):
   - ✅ Iterates through task.checkpoints to find matching checkpoint_id
   - ✅ Returns JSON error if not found (line 1201)
   - ✅ Sets reason="checkpoint_selected"

2. **Step_id latest checkpoint** (lines 1203-1209):
   - ✅ Iterates checkpoints in reverse (latest first) to find step_id match
   - ✅ Sets reason="checkpoint_selected" if found, "step_checkpoint_missing" if not

3. **Latest overall checkpoint** (lines 1211-1214):
   - ✅ Selects `task.checkpoints[-1]` (most recent)
   - ✅ Sets reason="checkpoint_selected"

4. **No checkpoint fallback** (lines 1215-1216):
   - ✅ Sets reason="no_checkpoint"
   - ✅ selected_cp remains None

**PM-identified fix (noted in A_DONE.md lines 6-9):**
- ✅ Problem: resume_policy always returned "from_step" even when checkpoint selected
- ✅ Fix: resume_policy returns "from_checkpoint" when checkpoint selected (lines 1249-1250)
- ✅ Fix: resume_policy returns task.resume_policy or "from_step" for no-checkpoint fallback (line 1252)

### 3. next_step_id, can_resume, resume_policy, Reason Labels

**Verdict: ✅ CORRECT AND DETERMINISTIC**

**next_step_id computation (lines 1226-1245):**
- ✅ Prefers checkpoint step if not done/skipped (lines 1230-1233)
- ✅ Falls back to first incomplete step (lines 1235-1239)
- ✅ Falls back to task.current_step if all steps done (lines 1241-1245)
- ✅ Uses StepStatus.DONE and StepStatus.SKIPPED for done_skipped set (line 1227)

**can_resume logic (lines 1218-1224):**
- ✅ False for terminal statuses: completed, cancelled (lines 1219-1222)
- ✅ True for all other statuses: pending, running, paused, blocked, failed (line 1224)
- ✅ Terminal status overrides checkpoint selection (checked after checkpoint selection)

**resume_policy logic (lines 1249-1252):**
- ✅ Returns "from_checkpoint" when checkpoint selected (line 1250)
- ✅ Returns task.resume_policy or "from_step" for no-checkpoint fallback (line 1252)

**Reason labels (deterministic):**
- ✅ "checkpoint_selected" — checkpoint found and selected
- ✅ "step_checkpoint_missing" — step_id provided but no checkpoint for that step
- ✅ "no_checkpoint" — no checkpoints exist
- ✅ "terminal_status" — task completed or cancelled (overrides other reasons)
- ✅ "all_steps_done" — all steps done/skipped, can_resume=True

### 4. Bounded Output Safety

**Verdict: ✅ SAFE**

Output contains only bounded safe metadata (lines 1254-1268):

```python
{
    "task_id": task.task_id,
    "status": task.status,
    "can_resume": can_resume,
    "resume_policy": resume_policy,
    "selected_checkpoint_id": selected_cp.checkpoint_id if selected_cp else None,
    "checkpoint_step_id": selected_cp.step_id if selected_cp else None,
    "next_step_id": next_step_id,
    "checkpoint_count": len(task.checkpoints),
    "step_count": len(task.steps),
    "incomplete_step_count": incomplete_count,
    "trace_ref_count": len(task.trace_refs),
    "worker_id_present": bool(task.worker_id),
    "reason": reason,
}
```

**Explicitly excluded from output:**
- ❌ Raw goal text
- ❌ Raw step text
- ❌ Notes
- ❌ Summaries
- ❌ Checkpoint description
- ❌ Raw state_snapshot
- ❌ Prompts
- ❌ Diffs
- ❌ Shell output
- ❌ Env vars
- ❌ Secret-like values

**Verified by tests:**
- ✅ `test_no_goal_or_step_text_leakage` (lines 1953-1967): goal, step text ABSENT
- ✅ `test_checkpoint_description_and_snapshot_not_leaked` (lines 2030-2043): sentinel description, snapshot, nested values ABSENT

### 5. Test Coverage

**Verdict: ✅ COMPREHENSIVE**

`DurableRecoveryPlanToolTests` class (19 test methods, lines 1824-2044):

**Checkpoint selection:**
1. `test_latest_checkpoint_selected` (line 1850) — auto-selects most recent checkpoint
2. `test_explicit_checkpoint_id_selection` (line 1862) — selects exact checkpoint by id
3. `test_step_id_selection` (line 1874) — selects checkpoint for given step
4. `test_step_id_missing_checkpoint` (line 1882) — returns step_checkpoint_missing reason
5. `test_no_checkpoint_fallback` (line 1890) — returns no_checkpoint reason with null checkpoint_id

**Terminal status:**
6. `test_completed_task_can_resume_false` (line 1903) — terminal status, can_resume=False
7. `test_cancelled_task_can_resume_false` (line 1914) — terminal status, can_resume=False
8. `test_failed_task_can_resume_true` (line 1925) — failed is resumable, can_resume=True

**Error handling:**
9. `test_unknown_task_returns_error` (line 1936)
10. `test_unknown_checkpoint_returns_error` (line 1941)
11. `test_non_integer_step_id_returns_error` (line 1947)

**Output safety:**
12. `test_no_goal_or_step_text_leakage` (line 1953) — goal, step text ABSENT
13. `test_checkpoint_description_and_snapshot_not_leaked` (line 2030) — sentinels ABSENT

**Read-only verification:**
14. `test_no_mutation_of_task_state` (line 1969) — verifies no state changes

**next_step_id logic:**
15. `test_next_step_prefers_checkpoint_step_when_not_done` (line 1983)
16. `test_next_step_skips_done_steps` (line 1990) — step 1 done, next_step=2

**PM fix verification:**
17. `test_resume_policy_from_checkpoint_when_latest_selected` (line 2008)
18. `test_resume_policy_from_checkpoint_when_explicit_id` (line 2014)
19. `test_resume_policy_from_step_when_no_checkpoint` (line 2022)

**Assertion quality:**
- ✅ No empty assertions (all verify specific payload fields, safety conditions, or error responses)
- ✅ Strong negative assertions (goal, step text, checkpoint description, state_snapshot ABSENT)
- ✅ Positive assertions verify exact values (resume_policy, next_step_id, reason, can_resume)

---

## Test Gaps / Residual Risk

**None identified.**

All critical recovery plan behaviors are covered:
- ✅ Checkpoint selection priority (explicit > step-based > latest > none)
- ✅ next_step_id computation logic
- ✅ can_resume logic for all status types
- ✅ resume_policy logic (PM fix verified)
- ✅ Error handling (unknown task, checkpoint, step_id)
- ✅ Output safety (no raw text leakage)
- ✅ Read-only verification

---

## Checks Run

```text
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 452 tests — OK

python3 evals/run_evals.py
194 passed, 0 failed

git diff --check
clean
```

---

## Findings

### Must Fix

**None** — implementation is production-ready.

### Suggestions

**None** — code quality is high, no technical debt introduced.

---

## Recommendation

**APPROVE and merge.**

TASK-054 provides a strictly read-only recovery plan tool that correctly implements checkpoint selection priority, next_step_id computation, can_resume logic, and resume_policy semantics. All PM-identified fixes (resume_policy logic, checkpoint description/snapshot leakage tests) are correctly implemented and tested. Output is bounded to safe metadata with no raw text leakage. No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
