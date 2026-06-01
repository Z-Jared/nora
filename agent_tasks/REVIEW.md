# CCB Code Review Report

Reviewed: TASK-057 Deterministic eval coverage for recovery-plan events
Worker: Claude B
Status: **APPROVED**

---

## Review Scope

### 1. Eval Coverage Completeness

**Verdict: ✅ COMPLETE**

4 eval cases added (eval count: 198 → 202):

1. **`eval_recovery_event_basics`** (line 7446-7483)
   - Creates task with checkpoint, calls plan_durable_recovery
   - Verifies RECOVERY_PLANNED event recorded with:
     - ✅ `severity=info`, `source=registry` (lines 7465-7466)
     - ✅ `checkpoint_id` top-level linkage matches selected checkpoint (line 7467)
     - ✅ Payload fields: operation, can_resume, resume_policy, reason, selected_checkpoint_present, checkpoint_step_id, checkpoint_count, step_count, requested_checkpoint_id_present, requested_step_id_present (lines 7468-7477)
     - ✅ Bounded payload: goal, steps, description, state_snapshot, notes, summary_text keys ABSENT (lines 7480-7481)

2. **`eval_recovery_event_selection_fallback`** (line 7486-7534)
   - ✅ Explicit checkpoint_id selection: checkpoint_id linkage matches, requested_checkpoint_id_present=True (lines 7504-7505)
   - ✅ step_id selection: requested_step_id_present=True, checkpoint_id linkage (lines 7511-7512)
   - ✅ No-checkpoint fallback: checkpoint_id="", reason=no_checkpoint, selected_checkpoint_present=False (lines 7521-7523)
   - ✅ Terminal status: can_resume=False, reason=terminal_status (lines 7531-7532)

3. **`eval_recovery_event_safety`** (line 7537-7587)
   - Injects sentinels into task state via `get_task()` + `upsert_task()` (lines 7550-7559):
     - ✅ `step.note` with sentinel (line 7551)
     - ✅ `step.summary` with sentinel (line 7552)
     - ✅ `checkpoint.description` with sentinel (line 7553)
     - ✅ `checkpoint.state_snapshot` with nested sentinel + secret-like `api_token` key (lines 7554-7558)
   - Verifies all sentinels ABSENT from serialized `event.to_dict()` (lines 7568-7573):
     - ✅ `_RECOVERY_EVENT_SENTINEL_GOAL` (line 7569)
     - ✅ `_RECOVERY_EVENT_SENTINEL_STEP` (line 7570)
     - ✅ `_RECOVERY_EVENT_SENTINEL_NOTE` (line 7571)
     - ✅ `_RECOVERY_EVENT_SENTINEL_SECRET` (line 7572)
     - ✅ `"ghp_recv_abc123def456"` (line 7573)
   - Allowed-fields-only check: verifies payload contains only expected keys (lines 7577-7585)
     - ✅ 14 allowed keys verified (lines 7577-7583)

4. **`eval_recovery_event_compatibility`** (line 7590-7633)
   - ✅ Snapshots task state before planning: status, steps, checkpoint_count (lines 7609-7612)
   - ✅ Broken event store doesn't prevent planning (lines 7615-7619)
   - ✅ Task state unchanged after planning: status, steps, checkpoints (lines 7622-7625)
   - ✅ Existing tools still work after broken store: get_durable_task, list_durable_tasks, update_durable_task (lines 7628-7631)

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

Evals prevent key TASK-056 regressions:

**RECOVERY_PLANNED event model:**
- ✅ `eval_recovery_event_basics` lines 7461-7462: RECOVERY_PLANNED event recorded
- ✅ `eval_recovery_event_basics` lines 7465-7466: source=registry, severity=info
- ✅ Catches regression where event type or metadata would change

**Top-level checkpoint_id linkage:**
- ✅ `eval_recovery_event_basics` line 7467: checkpoint_id matches selected checkpoint
- ✅ `eval_recovery_event_selection_fallback` lines 7504, 7512: checkpoint_id linkage for explicit/step selection
- ✅ `eval_recovery_event_selection_fallback` line 7521: checkpoint_id="" for no-checkpoint fallback
- ✅ Catches regression where checkpoint_id linkage would break

**Payload fields:**
- ✅ `eval_recovery_event_basics` lines 7468-7477: all 14 payload fields verified
- ✅ `eval_recovery_event_selection_fallback` lines 7505, 7511, 7523: requested_checkpoint_id_present, requested_step_id_present, selected_checkpoint_present verified
- ✅ Catches regression where payload fields would change

**Event-store failure isolation:**
- ✅ `eval_recovery_event_compatibility` lines 7615-7619: broken event store doesn't prevent planning
- ✅ Catches regression where event logging failure would block plan generation

**Read-only/no mutation:**
- ✅ `eval_recovery_event_compatibility` lines 7622-7625: task state unchanged after planning
- ✅ Catches regression where event logging would mutate task state

**Safety (no raw text leakage):**
- ✅ `eval_recovery_event_safety` lines 7569-7573: sentinels absent from serialized event
- ✅ `eval_recovery_event_safety` lines 7577-7585: only allowed keys present
- ✅ Catches regression where raw goal, step text, notes, summaries, checkpoint descriptions, state_snapshot, or secrets would leak

### 4. Safety Eval Strength

**Verdict: ✅ ROBUST**

**Sentinel values (lines 7440-7443):**
```python
_RECOVERY_EVENT_SENTINEL_GOAL = "NORA_EVAL_RECOVERY_EVT_GOAL_a1b2c3d4"
_RECOVERY_EVENT_SENTINEL_STEP = "NORA_EVAL_RECOVERY_EVT_STEP_e5f6a7b8"
_RECOVERY_EVENT_SENTINEL_NOTE = "NORA_EVAL_RECOVERY_EVT_NOTE_c9d0e1f2"
_RECOVERY_EVENT_SENTINEL_SECRET = "NORA_EVAL_RECOVERY_EVT_SECRET_sk-recv-3a4b5c6d"
```

**Direct state injection:**
- ✅ Injects sentinels into step.note, step.summary, checkpoint.description, checkpoint.state_snapshot (lines 7550-7559)
- ✅ State_snapshot contains nested sentinel + secret-like `api_token` key (lines 7554-7558)

**Serialized event verification:**
- ✅ Checks `event.to_dict()` serialized output (line 7568)
- ✅ Verifies all 4 sentinels + api_token secret ABSENT (lines 7569-7573)

**Allowed-fields-only check:**
- ✅ 14 allowed payload keys verified (lines 7577-7583)
- ✅ Unexpected keys cause assertion failure (lines 7584-7585)

**Note:** `checkpoint_id` linkage itself is allowed as a safe id (verified in eval_recovery_event_basics line 7467 and eval_recovery_event_selection_fallback lines 7504, 7512, 7521)

### 5. Assertion Quality

**Verdict: ✅ SUBSTANTIVE**

**Positive assertions verify specific values:**
- ✅ severity=info, source=registry (lines 7465-7466)
- ✅ checkpoint_id linkage matches selected checkpoint (line 7467)
- ✅ operation=plan_recovery, can_resume=True, resume_policy="from_checkpoint", reason="checkpoint_selected" (lines 7468-7471)
- ✅ selected_checkpoint_present=True, checkpoint_step_id=1, checkpoint_count=1, step_count=2 (lines 7472-7475)
- ✅ requested_checkpoint_id_present=False, requested_step_id_present=False (lines 7476-7477)

**Negative assertions verify safety:**
- ✅ 4 sentinels + api_token secret ABSENT from serialized event (lines 7569-7573)
- ✅ goal, steps, description, state_snapshot, notes, summary_text keys ABSENT from payload (lines 7480-7481)
- ✅ Only 14 allowed keys present in payload (lines 7577-7585)

**No empty or misleading assertions:**
- ✅ All assertions check specific conditions
- ✅ No assertions that always pass
- ✅ No misleading comments

### 6. No Runtime Changes by Claude B

**Verdict: ✅ CLEAN**

From `B_DONE.md`:
- ✅ "No runtime code changed (TASK-056 was already complete)"
- ✅ "No commit or push performed"
- ✅ "Known issues: none"

**Diff verification:**
- ✅ Only `evals/run_evals.py` modified (203 lines added, 1 removed)
- ✅ No changes to runtime code (durable_events.py, registry_builder.py, test_durable_tasks.py)
- ✅ No eval depends on incorrect TASK-056 behavior

---

## Test Gaps / Residual Risk

**None identified.**

All critical recovery-plan event behaviors are covered:
- ✅ RECOVERY_PLANNED event recorded with correct metadata (source, severity, operation, can_resume, resume_policy, reason, counts, presence flags)
- ✅ Top-level checkpoint_id linkage for all selection modes (explicit, step, no-checkpoint, terminal)
- ✅ Payload safety with direct sentinel injection (step.note/summary, checkpoint.description/state_snapshot, nested + api_token)
- ✅ Allowed-fields-only check on payload keys
- ✅ Event-store failure isolation
- ✅ Read-only verification (no task state mutation)

---

## Checks Run

```text
python3 evals/run_evals.py
202 passed, 0 failed

python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent
Ran 458 tests — OK

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

TASK-057 provides strong deterministic eval coverage for TASK-056 recovery-plan event logging. All critical regression scenarios are covered: RECOVERY_PLANNED event model, checkpoint_id linkage, payload fields, event-store failure isolation, read-only verification, and safety. Safety eval uses direct state injection of sentinels into step.note/summary and checkpoint.description/state_snapshot (nested + api_token), and verifies allowed-fields-only on payload keys. No runtime changes by Claude B.

**Next Action**: PM can proceed with git commit and push.
