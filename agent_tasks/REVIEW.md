# CCB Code Review Report

Reviewed: TASK-016 Eval coverage for durable shell-command events
Worker: Codex PM (Claude B blocked by stale worktree)
Status: **APPROVED**

---

## Review Scope

### 1. Deterministic Offline Eval Coverage

**Verdict: ✅ COMPLETE**

5 new eval cases added (eval count: 103 → 108):

1. **`shell_command_event_success`** (line 2713)
   - ✅ Exercises `pwd` via `ShellRunner` with reason sentinel
   - ✅ Verifies `SHELL_COMMAND_STARTED` → `SHELL_COMMAND_FINISHED` lifecycle
   - ✅ Checks executable="pwd", exit_code=0, stdout_bytes > 0, severity="info", task_id=None
   - ✅ Exercises safe allowed-arg case: `python3 -m py_compile {sentinel}.py`
   - ✅ Calls `_assert_shell_events_safe()` for both cases

2. **`shell_command_event_blocked`** (line 2758)
   - ✅ Exercises `rm -rf /` (disallowed command)
   - ✅ Verifies `SHELL_COMMAND_BLOCKED` with error="disallowed_command", status="blocked", severity="warning"
   - ✅ Verifies no STARTED or FINISHED events
   - ✅ Exercises malformed command with sentinel arg: `'{sentinel}`
   - ✅ Asserts sentinel ABSENT from serialized events

3. **`shell_command_event_cancelled`** (line 2790)
   - ✅ Exercises confirmation denial via `confirm_action=lambda _: False`
   - ✅ Verifies `SHELL_COMMAND_BLOCKED` with error="cancelled", severity="warning"
   - ✅ Verifies no STARTED or FINISHED events
   - ✅ Calls `_assert_shell_events_safe()` with empty forbidden list

4. **`shell_command_event_error`** (line 2820)
   - ✅ **Timeout sub-case**: Sleeps 30s script with 1s timeout
   - ✅ Verifies STARTED → ERROR lifecycle with error="timeout", status="timeout", timeout=True, severity="warning"
   - ✅ Asserts sentinel stdout ABSENT from serialized events
   - ✅ **OSError sub-case**: Patches `subprocess.run` to raise `OSError(sentinel)`
   - ✅ Verifies ERROR lifecycle with error="os_error", severity="warning"
   - ✅ Asserts sentinel OSError text ABSENT from both user-visible result and serialized events

5. **`shell_command_event_failure_isolation`** (line 2872)
   - ✅ Uses BrokenEventStore that raises RuntimeError
   - ✅ Verifies `run("pwd")` succeeds with "exit_code: 0"
   - ✅ Verifies `event_store=None` also succeeds with "exit_code: 0"

### 2. Strong Safety Assertions

**Verdict: ✅ ROBUST**

**Sentinel-based verification (3 sentinels):**

```python
_SHELL_SENTINEL_CMD = "NORA_EVAL_SHELL_SENTINEL_a7c3e1f9"      # raw command arg
_SHELL_SENTINEL_OUTPUT = "NORA_EVAL_SHELL_OUTPUT_SECRET_d4b28e61" # raw stdout content
_SHELL_SENTINEL_REASON = "NORA_EVAL_SHELL_REASON_9f1e3d7a"     # raw reason text
```

**Additional sentinel:**
- `os_sentinel = "NORA_EVAL_OSERROR_SENTINEL_c8d4f2a1"` — raw OSError text (line 2854)

**Forbidden payload keys (10 keys):**

```python
_SHELL_FORBIDDEN_PAYLOAD_KEYS = {
    "command", "args", "argv",      # raw command/args
    "stdout", "stderr", "output",   # raw output
    "result",                       # raw result
    "reason",                       # user-provided reason
    "exception", "traceback",       # raw error details
}
```

**`_assert_shell_events_safe()` function (line 2704-2710):**
- ✅ Serializes all shell events to JSON
- ✅ Checks all forbidden values are ABSENT from serialized data
- ✅ Checks all 10 forbidden payload keys are ABSENT from event payloads

**Coverage in each eval:**
- ✅ `shell_command_event_success` — reason sentinel + cmd sentinel + path sentinel checked
- ✅ `shell_command_event_blocked` — cmd sentinel checked
- ✅ `shell_command_event_cancelled` — no new sentinels, but safety assertion still runs
- ✅ `shell_command_event_error` — output sentinel (timeout) + os_sentinel (OSError) checked
- ✅ `shell_command_event_failure_isolation` — isolation test, not safety-focused

### 3. Lifecycle and Payload Verification

**Verdict: ✅ SUBSTANTIVE**

All evals verify specific behaviors, not just "events exist":

**Lifecycle verification:**
- ✅ Exact event sequences: `[STARTED, FINISHED]`, `[BLOCKED]`, `[STARTED, ERROR]`
- ✅ No unexpected events: `assert len(started) == 0`, `assert len(finished) == 0`

**Payload field verification:**
- ✅ Executable: `started[0].payload["executable"] == "pwd"`
- ✅ Exit code: `finished[0].payload["exit_code"] == 0`
- ✅ Status: `errors[0].payload["status"] == "timeout"`, `blocked[0].payload["status"] == "blocked"`
- ✅ Error labels: `errors[0].payload["error"] == "timeout"`, `"os_error"`, `"disallowed_command"`, `"cancelled"`
- ✅ Byte counts: `finished[0].payload["stdout_bytes"] > 0`
- ✅ Boolean timeout: `errors[0].payload["timeout"] is True`
- ✅ Severity: `started[0].severity == "info"`, `blocked[0].severity == "warning"`, `errors[0].severity == "warning"`
- ✅ Task ID: `started[0].task_id is None`, `finished[0].task_id is None`

**Negative assertions (sentinel absence):**
- ✅ All 4 sentinels checked absent from serialized events
- ✅ 10 forbidden payload keys checked absent from event payloads

**Behavioral assertions:**
- ✅ User-visible return preserved: `assert "exit_code: 0" in result`, `assert "拒绝" in result`, `assert "已取消" in result`
- ✅ Raw OSError not leaked to user: `assert os_sentinel not in result`

### 4. No Runtime Behavior Changes

**Verdict: ✅ CLEAN**

From `B_DONE.md`:
- ✅ "No runtime code changed (TASK-015 was already complete at b1794fa)"
- ✅ "No fallback imports or shims added"
- ✅ "Eval count increased from 103 to 108"

**Code review confirms:**
- ✅ Only `evals/run_evals.py` modified (214 lines added, 1 removed)
- ✅ No changes to runtime code (shell.py, durable_events.py, registry_builder.py)
- ✅ No compatibility shims or workarounds
- ✅ Clean separation: eval-only changes

### 5. Deterministic and Offline

**Verdict: ✅ DETERMINISTIC**

- ✅ No live LLM calls — uses `ShellRunner` directly
- ✅ No interactive terminal prompts — uses `require_confirmation=False` or auto-deny lambda
- ✅ No external state dependencies — uses `tempfile.TemporaryDirectory()`
- ✅ No network calls — purely local subprocess execution
- ✅ No timing dependencies — timeout test uses 1s timeout for deterministic behavior
- ✅ Reproducible — same results every run

---

## Checks Run

```text
python3 evals/run_evals.py
108 passed, 0 failed

python3 -m unittest tests.test_durable_events tests.test_mini_agent
Ran 203 tests — OK

git diff --check
OK
```

---

## Findings

### Must Fix

**None** — implementation is production-ready.

### Suggestions

**None** — eval coverage is comprehensive and well-structured.

### Risk Assessment

- ✅ **Coverage**: All shell-command lifecycle paths covered (success, blocked, cancelled, timeout, OSError, isolation)
- ✅ **Safety**: Strong sentinel-based assertions prevent raw data leakage (4 sentinels + 10 forbidden keys)
- ✅ **Determinism**: No live LLM, no interactive prompts, no external state
- ✅ **Clean Separation**: Eval-only changes, no runtime modifications
- ✅ **Test Quality**: Substantive assertions verify specific lifecycle sequences, payload fields, and sentinel absence

---

## Verdict

**APPROVED**

TASK-016 is ready for commit and merge. Eval coverage is comprehensive, deterministic, and includes strong safety assertions. No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
