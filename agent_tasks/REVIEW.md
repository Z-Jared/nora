# CCB Code Review Report

Reviewed: TASK-056 Durable recovery plan event logging v1
Worker: Claude A
Status: **APPROVED**

---

## Review Scope

### 1. RECOVERY_PLANNED Event Model Compliance

**Verdict: ✅ COMPLIANT**

`mini_agent/durable_events.py`:
- ✅ `RECOVERY_PLANNED = "recovery_planned"` constant (line 54)
- ✅ Added to `VALID_EVENT_TYPES` (line 93)
- ✅ Event type is queryable via `list_events(event_type=RECOVERY_PLANNED)`
- ✅ Consistent with other durable event types (CHECKPOINT_ADDED, TASK_STATUS_CHANGED, etc.)

### 2. Event Logging Scope (Success Only)

**Verdict: ✅ CORRECT**

`mini_agent/toolkits/registry_builder.py` lines 1255-1281:
- ✅ Event recorded only after successful plan computation (line 1255)
- ✅ Error responses (unknown task/checkpoint/bad step_id) skip event logging (errors return early)
- ✅ Event logging wrapped in try/except (lines 1255-1281) — failure doesn't prevent plan return
- ✅ Error paths (lines 1181, 1189, 1201) return JSON error before reaching event logging

**Event properties:**
- ✅ `event_type=RECOVERY_PLANNED`
- ✅ `task_id` set to task id
- ✅ `checkpoint_id` set top-level: selected checkpoint id when present, empty string otherwise (line 1259)
- ✅ `summary="recovery planned"`
- ✅ `source="registry"`
- ✅ `severity="info"`

### 3. Safe Event Payload

**Verdict: ✅ SAFE**

Payload contains only bounded safe metadata (lines 1261-1275):

```python
{
    "operation": "plan_recovery",
    "can_resume": can_resume,
    "resume_policy": resume_policy,
    "reason": reason,
    "selected_checkpoint_present": selected_cp is not None,
    "checkpoint_step_id": selected_cp.step_id if selected_cp else None,
    "next_step_id": next_step_id,
    "checkpoint_count": len(task.checkpoints),
    "step_count": len(task.steps),
    "incomplete_step_count": incomplete_count,
    "trace_ref_count": len(task.trace_refs),
    "worker_id_present": bool(task.worker_id),
    "requested_checkpoint_id_present": bool(checkpoint_id),
    "requested_step_id_present": parsed_step_id is not None,
}
```

**Explicitly excluded from event payload:**
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
- ❌ Request strings
- ❌ Secret-like values

**Top-level checkpoint_id linkage:**
- ✅ `checkpoint_id` set to selected checkpoint id when present (line 1259)
- ✅ `checkpoint_id` set to empty string when no checkpoint selected (line 1259)
- ✅ Enables querying events by checkpoint

### 4. Failure Isolation

**Verdict: ✅ RELIABLE**

**Event logging failure isolation (lines 1255-1281):**
```python
try:
    registry.durable_event_store.record(...)
except Exception:
    pass
```

- ✅ Event logging wrapped in try/except with `pass`
- ✅ Broken event logging does not prevent plan generation (verified by test)
- ✅ Error responses skip event logging entirely (return early)

### 5. Read-Only Preservation

**Verdict: ✅ READ-ONLY**

Event logging addition preserves read-only semantics:
- ✅ No task state mutation (no `upsert_task()`, no `update_status()`)
- ✅ No worker execution (no worker status changes)
- ✅ No model calls (no LLMClient usage)
- ✅ No git/file recovery (no file system operations)
- ✅ Registered with `risk="read"` permission (from TASK-054)
- ✅ Test `test_plan_does_not_mutate_task_state` verifies read-only (lines 2145-2155)
  - Compares task state before and after plan with event logging
  - Verifies status, current_step, checkpoints, steps all unchanged

### 6. Test Coverage

**Verdict: ✅ COMPREHENSIVE**

`DurableRecoveryPlanEventTests` class (6 test methods, lines 2047-2155):

**Successful event recording:**
1. `test_recovery_planned_event_with_checkpoint` (line 2074)
   - Verifies event recorded with checkpoint linkage
   - Checks task_id, checkpoint_id (truthy), operation, can_resume, resume_policy, selected_checkpoint_present, source, severity

2. `test_recovery_planned_event_no_checkpoint` (line 2090)
   - Verifies event recorded when no checkpoint
   - Checks selected_checkpoint_present=False, requested_checkpoint_id_present=False, requested_step_id_present=False

**Top-level checkpoint_id linkage:**
3. `test_checkpoint_id_linked_on_event` (line 2103)
   - Verifies top-level checkpoint_id matches selected checkpoint_id
   - Checks requested_checkpoint_id_present=True

**Payload safety:**
4. `test_event_payload_no_raw_leakage` (line 2115)
   - Injects sentinel text into checkpoint description and state_snapshot via `get_task()` + `upsert_task()`
   - Verifies sentinels ABSENT from event payload:
     - `"SENTINEL_CP_DESC_999"` (line 2128)
     - `"SENTINEL_SNAPSHOT_999"` (line 2129)
     - `"secret goal"` (line 2130)
     - `"step one"` (line 2131)

**Failure isolation:**
5. `test_event_failure_does_not_prevent_plan` (line 2133)
   - Mocks event store to raise `RuntimeError("store broken")`
   - Verifies plan still returns successfully with task_id and can_resume=True

**Read-only verification:**
6. `test_plan_does_not_mutate_task_state` (line 2145)
   - Verifies task state unchanged after plan with event logging
   - Checks status, current_step, checkpoint count, step count

**Assertion quality:**
- ✅ No empty assertions (all verify specific payload fields, safety conditions, or error responses)
- ✅ Strong negative assertions (sentinels ABSENT from event payload)
- ✅ Positive assertions verify exact values (operation, can_resume, resume_policy, source, severity)

---

## Test Gaps / Residual Risk

**None identified.**

All critical event logging behaviors are covered:
- ✅ Event recorded on successful plan (with and without checkpoint)
- ✅ Top-level checkpoint_id linkage
- ✅ Payload safety (no raw text leakage)
- ✅ Failure isolation (broken event store doesn't prevent plan)
- ✅ Read-only verification (no state mutation)

---

## Checks Run

```text
python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 458 tests — OK

python3 evals/run_evals.py
198 passed, 0 failed

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

TASK-056 adds RECOVERY_PLANNED durable event logging to plan_durable_recovery while preserving read-only semantics. Event payload contains only safe metadata (no raw goal, step text, checkpoint descriptions, state_snapshot, or secrets). Error responses skip event logging, and event logging failures don't prevent plan generation. Test coverage is comprehensive with 6 focused tests. No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
