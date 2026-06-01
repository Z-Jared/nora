# CCB Code Review Report

Reviewed: TASK-055 Deterministic eval coverage for durable recovery plans
Worker: Claude B
Status: **APPROVED**

---

## Review Scope

### 1. Eval Coverage Completeness

**Verdict: ✅ COMPLETE**

4 eval cases added (eval count: 194 → 198):

1. **`eval_recovery_plan_basics`** (line 7227)
   - Creates task with 3 steps, adds checkpoint for step 1 and step 2
   - Plans with latest checkpoint (default): verifies task_id, can_resume=True, selected_checkpoint_id=cp2, checkpoint_step_id=2, resume_policy="from_checkpoint", checkpoint_count=2, step_count=3, incomplete_step_count=3, reason="checkpoint_selected"
   - Bounded output: checks goal, steps, description, state_snapshot, notes keys ABSENT
   - Marks step 1 done, re-plans: verifies incomplete_step_count=2
   - PM fix applied: strict `next_step_id == 2` assertion (line 7272) with explanatory comment

2. **`eval_recovery_plan_selection_fallback`** (line 7277)
   - ✅ Explicit checkpoint_id selection (lines 7291-7295)
   - ✅ step_id selection: latest checkpoint for that step (lines 7297-7300)
   - ✅ Missing step checkpoint fallback: selected_checkpoint_id=None, reason="step_checkpoint_missing" (lines 7302-7308)
   - ✅ No-checkpoint fallback: selected_checkpoint_id=None, reason="no_checkpoint", can_resume=True (lines 7310-7316)
   - ✅ Unknown task returns error (lines 7318-7320)
   - ✅ Unknown checkpoint returns error (lines 7322-7324)
   - ✅ Bad step_id returns error (lines 7326-7328)
   - ✅ Terminal status: can_resume=False, reason="terminal_status" (lines 7330-7335)

3. **`eval_recovery_plan_safety`** (line 7340)
   - PM fix applied: direct state injection of sentinels via `get_task()` + `upsert_task()`
   - Injects sentinels into (lines 7356-7364):
     - `step.note` with sentinel (line 7356)
     - `step.summary` with sentinel (line 7357)
     - `checkpoint.description` with sentinel (line 7359)
     - `checkpoint.state_snapshot` with nested sentinel + secret-like `api_token` key (lines 7360-7364)
   - Verifies all sentinels ABSENT from plan output (lines 7368-7371):
     - `_RECOVERY_SENTINEL_GOAL` (line 7368)
     - `_RECOVERY_SENTINEL_STEP` (line 7369)
     - `_RECOVERY_SENTINEL_SECRET` (line 7370)
     - `"ghp_abc123def456"` (line 7371)
   - Allowed-fields-only check: verifies output contains only expected keys (lines 7374-7382)

4. **`eval_recovery_plan_compatibility`** (line 7387)
   - Snapshots task state before planning: status, step_count, checkpoint_count, current_step (lines 7400-7404)
   - Plans and verifies no error (line 7408)
   - Verifies task state unchanged after planning (lines 7411-7418):
     - status unchanged
     - step count unchanged
     - checkpoint count unchanged
     - current_step unchanged
     - step statuses unchanged
     - step checkpoint_refs unchanged
   - Error plans don't break existing tools (lines 7420-7423):
     - Unknown task error
     - Unknown checkpoint error
     - Bad step_id error
   - Existing tools still work after error plans (lines 7426-7429):
     - `get_durable_task` returns no error
     - `list_durable_tasks` returns list
     - `update_durable_task` returns no error

### 2. Deterministic and Offline

**Verdict: ✅ DETERMINISTIC**

All 4 eval cases are deterministic and offline:

- ✅ Uses `tempfile.TemporaryDirectory()` for isolation
- ✅ No live LLM calls — uses `build_default_registry` with `confirm_action=lambda _: True`
- ✅ No interactive terminal prompts
- ✅ No external state dependencies
- ✅ No network calls
- ✅ No timing dependencies
- ✅ Reproducible — same results every run

### 3. Regression Prevention Quality

**Verdict: ✅ STRONG**

Evals prevent key TASK-054 regressions:

**resume_policy logic (PM fix in TASK-054):**
- ✅ `eval_recovery_plan_basics` line 7253: `resume_policy == "from_checkpoint"` when checkpoint selected
- ✅ Catches regression where resume_policy would always return "from_step"

**Checkpoint selection priority:**
- ✅ `eval_recovery_plan_selection_fallback` lines 7291-7308: explicit checkpoint_id, step_id, missing step fallback
- ✅ `eval_recovery_plan_basics` lines 7251-7252: latest checkpoint selected
- ✅ Catches regression where checkpoint selection logic would break

**next_step_id computation (PM fix in TASK-055):**
- ✅ `eval_recovery_plan_basics` line 7272: strict `next_step_id == 2` after step 1 done
- ✅ Catches regression where next_step_id would incorrectly return 1

**can_resume logic:**
- ✅ `eval_recovery_plan_selection_fallback` lines 7333-7335: terminal status → can_resume=False
- ✅ `eval_recovery_plan_basics` line 7250: can_resume=True for non-terminal
- ✅ Catches regression where can_resume logic would break

**Reason labels:**
- ✅ `eval_recovery_plan_basics` line 7257: reason="checkpoint_selected"
- ✅ `eval_recovery_plan_selection_fallback` lines 7308, 7315, 7335: step_checkpoint_missing, no_checkpoint, terminal_status
- ✅ Catches regression where reason labels would change

**Bounded output/no mutation (PM fix in TASK-055):**
- ✅ `eval_recovery_plan_safety` lines 7368-7371: sentinels absent from output
- ✅ `eval_recovery_plan_safety` lines 7374-7382: only allowed keys present
- ✅ `eval_recovery_plan_compatibility` lines 7411-7418: task state unchanged after planning
- ✅ Catches regression where raw text would leak or planning would mutate state

### 4. Assertion Quality

**Verdict: ✅ SUBSTANTIVE**

**Sentinel values (lines 7222-7224):**
```python
_RECOVERY_SENTINEL_GOAL = "NORA_EVAL_RECOVERY_GOAL_SENTINEL_a9b8c7d6"
_RECOVERY_SENTINEL_STEP = "NORA_EVAL_RECOVERY_STEP_SECRET_e5f4a3b2"
_RECOVERY_SENTINEL_SECRET = "NORA_EVAL_RECOVERY_SECRET_sk-recovery-c1d2e3f4"
```

**PM-identified fixes (from B_DONE.md lines 12-19):**
1. ✅ **next_step_id assertion tightened**: Changed from `in (1, 2)` to strict `== 2` (line 7272)
2. ✅ **safety eval strengthened**: Direct state injection of sentinels into step.note, step.summary, checkpoint.description, checkpoint.state_snapshot (lines 7356-7364)

**Positive assertions verify specific values:**
- ✅ task_id, can_resume, selected_checkpoint_id, checkpoint_step_id, resume_policy
- ✅ checkpoint_count, step_count, incomplete_step_count, next_step_id
- ✅ reason labels, status

**Negative assertions verify safety:**
- ✅ 3 sentinels + api_token secret ABSENT from plan output
- ✅ goal, steps, description, state_snapshot, notes keys ABSENT from output
- ✅ Only allowed keys present in output (13 allowed keys)
- ✅ Task state unchanged after planning (6 assertions)

**No empty or misleading assertions:**
- ✅ All assertions check specific conditions
- ✅ No assertions that always pass
- ✅ No misleading comments
- ✅ PM fix explanations present in comments (lines 7264, 7272)

### 5. No Runtime Changes by Claude B

**Verdict: ✅ CLEAN**

From `B_DONE.md`:
- ✅ "No runtime code changed"
- ✅ "No commit or push performed"
- ✅ "Known issues: none"

**Diff verification:**
- ✅ Only `evals/run_evals.py` modified (218 lines added)
- ✅ No changes to runtime code (registry_builder.py, durable_tasks.py)
- ✅ No eval depends on incorrect TASK-054 behavior

---

## Test Gaps / Residual Risk

**None identified.**

All critical recovery plan behaviors are covered:
- ✅ Checkpoint selection priority (explicit > step-based > latest > none)
- ✅ resume_policy logic (from_checkpoint when checkpoint selected)
- ✅ next_step_id computation (strict == 2 after step 1 done)
- ✅ can_resume logic for terminal and non-terminal statuses
- ✅ Reason labels for all scenarios
- ✅ Bounded output with no raw text leakage (injected sentinels + allowed-fields check)
- ✅ No mutation verification
- ✅ Error handling (unknown task, checkpoint, step_id)
- ✅ Compatibility (existing tools still work after error plans)

---

## Checks Run

```text
python3 evals/run_evals.py
198 passed, 0 failed

python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 452 tests — OK

git diff --check evals/run_evals.py
OK
```

---

## Findings

### Must Fix

**None** — implementation is production-ready.

### Suggestions

**None** — eval coverage is comprehensive and well-structured.

---

## Recommendation

**APPROVE and merge.**

TASK-055 provides strong deterministic eval coverage for TASK-054 recovery plan controls. All critical regression scenarios are covered: resume_policy, checkpoint selection, next_step_id, can_resume, reason labels, bounded output, and no mutation. PM-identified fixes (strict next_step_id assertion, strengthened safety eval with direct state injection) are correctly implemented. Evals are deterministic, offline, and use substantive sentinel-based assertions. No runtime changes by Claude B.

**Next Action**: PM can proceed with git commit and push.
