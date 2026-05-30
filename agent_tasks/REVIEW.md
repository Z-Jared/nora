# CCB Code Review Report

Reviewed: TASK-014 Eval coverage for durable file-edit events
Worker: Codex PM (Claude B blocked by stale worktree)
Status: **APPROVED**

---

## Review Scope

### 1. Eval Coverage Completeness

**Verdict: ✅ COMPLETE**

5 new eval cases added (eval count: 98 → 103):

1. **`file_edit_event_success`** (line 2501)
   - ✅ Exercises registry-wired `write_project_file`
   - ✅ Verifies `FILE_EDIT_STARTED` → `FILE_EDIT_FINISHED` lifecycle
   - ✅ Checks operation="write", status, path, paths list, bytes_before=0, bytes_after, severity="info"
   - ✅ Asserts `task_id is None` for all events
   - ✅ Calls `_assert_file_edit_events_safe()` for safety checks

2. **`file_edit_event_patch_metadata`** (line 2533)
   - ✅ Exercises `apply_project_patch` (single file) and `apply_project_multi_patch` (2 files)
   - ✅ Verifies both patch and multi-patch started→finished lifecycles
   - ✅ Checks path(s), file_count=2, byte metadata
   - ✅ Asserts raw patch text and multi-patch text NOT in serialized events
   - ✅ Calls `_assert_file_edit_events_safe()` for safety checks

3. **`file_edit_event_blocked_or_cancelled`** (line 2588)
   - ✅ Exercises denied `.env` write → blocked-only (no STARTED emitted)
   - ✅ Verifies status="blocked", error="denied_path", severity="warning"
   - ✅ Exercises confirmation cancellation → started→blocked
   - ✅ Verifies status="cancelled", error="cancelled", no FINISHED event
   - ✅ Calls `_assert_file_edit_events_safe()` for both scenarios

4. **`file_edit_event_error`** (line 2634)
   - ✅ Simulates `Path.write_text` OSError with sentinel error text
   - ✅ Verifies started→error lifecycle
   - ✅ Checks status="error", error="write_failed" (generic label), severity="warning"
   - ✅ Asserts user-visible error behavior preserved (raw OSError in result string)
   - ✅ Asserts raw OSError sentinel NOT in serialized events
   - ✅ Calls `_assert_file_edit_events_safe()` for safety checks

5. **`file_edit_event_failure_isolation`** (line 2657)
   - ✅ Uses BrokenEventStore that raises RuntimeError
   - ✅ Verifies `write()` succeeds and file is written correctly
   - ✅ Verifies `replace()` succeeds and file is modified correctly
   - ✅ Confirms event store failure doesn't break workspace operations

### 2. Strong Safety Assertions

**Verdict: ✅ ROBUST**

**Sentinel-based verification (5 sentinels):**

```python
_FILE_EDIT_SENTINELS = [
    "RAW_FILE_CONTENT_SHOULD_NOT_BE_STORED_6C2D",
    "RAW_REPLACEMENT_TEXT_SHOULD_NOT_BE_STORED_8E4A",
    "RAW_PATCH_TEXT_SHOULD_NOT_BE_STORED_1B7F",
    "RAW_OS_ERROR_SHOULD_NOT_BE_STORED_9D3E",
    "RAW_REASON_SHOULD_NOT_BE_STORED_2A5C",
]
```

**Additional sentinel:**
- `PATCH_REPLACEMENT_MARKER_8E4A` — replacement text in patch

**`_assert_file_edit_events_safe()` function (line 2491):**
- ✅ Serializes all events to JSON
- ✅ Checks all 6 sentinels are ABSENT from serialized data
- ✅ Checks forbidden payload keys are ABSENT:
  - `content`, `old_text`, `new_text` — raw file content
  - `patch`, `diff` — patch/diff text
  - `reason` — user-provided reason
  - `exception`, `traceback` — raw error details

**Coverage in each eval:**
- ✅ `file_edit_event_success` — content sentinel + reason sentinel checked
- ✅ `file_edit_event_patch_metadata` — patch text + replacement marker checked explicitly
- ✅ `file_edit_event_blocked_or_cancelled` — content + reason sentinels checked
- ✅ `file_edit_event_error` — OS error sentinel + forbidden keys checked
- ✅ `file_edit_event_failure_isolation` — uses sentinels (isolation test, not safety-focused)

### 3. Deterministic and Offline

**Verdict: ✅ DETERMINISTIC**

- ✅ No live LLM calls — uses `confirm_action=lambda _prompt: True` for auto-confirmation
- ✅ No interactive terminal prompts — all confirmations auto-accepted
- ✅ No external state dependencies — uses tempfile.TemporaryDirectory()
- ✅ No network calls — purely in-memory/file-based
- ✅ No timing dependencies — deterministic assertions
- ✅ Reproducible — same results every run

### 4. No Stale Worktree Fallback Imports/Shims

**Verdict: ✅ CLEAN**

From `B_DONE.md`:
- ✅ "Claude B reported a stale-worktree blocker"
- ✅ "Codex PM took over TASK-014 in the main worktree to avoid duplicating runtime or adding fallback shims"
- ✅ "No runtime changes were added for TASK-014"
- ✅ "No fallback imports or shims were added"
- ✅ "Claude B's stale worktree was not modified"

**Code review confirms:**
- ✅ Only `evals/run_evals.py` modified (217 lines added, 7 removed)
- ✅ No changes to runtime code (controller.py, workspace.py, durable_events.py)
- ✅ No compatibility shims or workarounds
- ✅ Clean separation: eval-only changes

### 5. Test Quality — Not Empty Assertions

**Verdict: ✅ SUBSTANTIVE**

All evals verify specific behaviors, not just "events exist":

**Lifecycle verification:**
- ✅ Exact event sequences: `[FILE_EDIT_STARTED, FILE_EDIT_FINISHED]`, `[FILE_EDIT_BLOCKED]`, `[FILE_EDIT_STARTED, FILE_EDIT_BLOCKED]`, `[FILE_EDIT_STARTED, FILE_EDIT_ERROR]`
- ✅ No unexpected events: `assert not any(event.event_type == FILE_EDIT_FINISHED for event in cancel_events)`

**Payload field verification:**
- ✅ Operation type: `started.payload["operation"] == "write"`, `"patch"`, `"multi_patch"`
- ✅ Status values: `started.payload["status"] == "started"`, `"finished"`, `"blocked"`, `"cancelled"`, `"error"`
- ✅ Path data: `started.payload["path"] == "notes.txt"`, `finished.payload["paths"] == ["b.txt", "c.txt"]`
- ✅ File count: `multi_events[1].payload["file_count"] == 2`
- ✅ Byte metadata: `finished.payload["bytes_before"] == 0`, `finished.payload["bytes_after"] == len(sentinel.encode("utf-8"))`
- ✅ Error labels: `events[1].payload["error"] == "write_failed"`, `"denied_path"`, `"cancelled"`
- ✅ Severity: `finished.severity == "info"`, `denied_events[0].severity == "warning"`, `events[1].severity == "warning"`
- ✅ Task ID: `all(event.task_id is None for event in events)`

**Negative assertions (sentinel absence):**
- ✅ All 6 sentinels checked absent from serialized events
- ✅ 8 forbidden payload keys checked absent
- ✅ Specific patch text explicitly checked absent: `assert patch_text not in serialized`

**Behavioral assertions:**
- ✅ User-visible return preserved: `assert "写入失败" in result`
- ✅ Raw error in result: `assert _FILE_EDIT_SENTINELS[3] in result`
- ✅ File actually written: `assert (tmpdir / "ok.txt").read_text(...) == sentinel`
- ✅ File actually modified: `assert (tmpdir / "replace.txt").read_text(...) == "new\n"`

---

## Checks Run

```text
python3 evals/run_evals.py
103 passed, 0 failed

python3 -m unittest tests.test_durable_events tests.test_workspace tests.test_workspace_patch
Ran 104 tests — OK

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

- ✅ **Coverage**: All file-edit lifecycle paths covered (success, patch, multi-patch, blocked, cancelled, error, isolation)
- ✅ **Safety**: Strong sentinel-based assertions prevent raw data leakage
- ✅ **Determinism**: No live LLM, no interactive prompts, no external state
- ✅ **Clean Separation**: Eval-only changes, no runtime modifications
- ✅ **Test Quality**: Substantive assertions verify specific behaviors, not just event existence
- ✅ **Maintainability**: Clear eval structure with shared safety assertion helper

---

## Verdict

**APPROVED**

TASK-014 is ready for commit and merge. Eval coverage is comprehensive, deterministic, and includes strong safety assertions. No blockers, no technical debt, no known risks.

**Next Action**: PM can proceed with git commit and push.
