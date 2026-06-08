# TASK-163 + TASK-164 CCB Review

**Status: APPROVED**

## Summary

TASK-163 adds Relationship Memory MVP: store model, HTTP API, and Pet Room UI. TASK-164 adds 7 deterministic evals to lock the contract. All review criteria satisfied.

## Review Findings

### 1. Pet Relationship Memory Store/Model (TASK-163)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Bounded model | ✅ | `PetRelationshipMemory` dataclass with memory_id, pet_id, kind, summary, source, importance, metadata, created_at |
| Supported kinds | ✅ | `shared_moment`, `preference`, `task_outcome` — validated in `add_relationship_memory()` |
| Secret rejection | ✅ | `is_sensitive_text(summary)`, `is_sensitive_text(source)`, metadata values checked |
| Summary bounded | ✅ | `_RELATIONSHIP_MEMORY_SUMMARY_MAX = 500`, `_RELATIONSHIP_MEMORY_SOURCE_MAX = 200` |
| Importance clamped | ✅ | `max(1, min(10, importance))` |
| List recent-first | ✅ | `ORDER BY created_at DESC` (SQLite), `reversed(matching[-limit:])` (JSONL) |
| Limit clamped | ✅ | `max(1, min(50, limit))` in both HTTP handler and store |
| SQLite/JSONL consistent | ✅ | Both backends implemented, `PetRelationshipMemoryJsonlTests` verifies |

### 2. HTTP API (TASK-163)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| GET read-only | ✅ | List endpoint, no mutation |
| POST mutation auth | ✅ | Uses existing `_check_auth()` pattern |
| Invalid kind rejection | ✅ | Returns 400 with `valid_kinds` list |
| Empty summary rejection | ✅ | Returns 400 |
| Secret input rejection | ✅ | `add_relationship_memory()` returns None → 400 error |
| Bounded errors | ✅ | No raw secret-like input echoed |
| /docs includes entry | ✅ | `test_relationship_memory_in_docs` verifies |

### 3. Pet Room UI (TASK-163)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Relationship Memories section | ✅ | `pet-memory-section` with list and Record Shared Moment button |
| Memory text escaped | ✅ | Uses `escapeHtml(m.summary)`, `escapeHtml(m.kind)` |
| No manipulative copy | ✅ | `eval_relmem_webui_no_fake_intimacy` verifies no "misses you", "lonely", "buy to unlock", etc. |
| No secret leak | ✅ | Eval checks for `sk-`, `AKIA`, `Bearer `, `api_key` in memory section |

### 4. Eval Quality (TASK-164)

| Eval | Coverage |
|------|----------|
| `relmem_write_supported_kinds` | All 3 kinds write and list successfully |
| `relmem_list_bounded_response` | Default list bounded, huge limit clamped to ≤50 |
| `relmem_response_fields` | memory_id, pet_id, kind, summary, source, created_at present |
| `relmem_rejects_secret_input` | Secret summary and source rejected, not echoed |
| `relmem_auth_enforced` | Without auth → 401, with auth → 200 |
| `relmem_webui_section_exists` | HTML contains memory section markers |
| `relmem_webui_no_fake_intimacy` | No fake intimacy/guilt/pressure/secret leak |

Guard `_skip_if_no_relmem()` properly skips when TASK-163 absent. Combined check: 7/7 PASS.

### 5. No Regressions

- 315 unit tests OK
- 664 evals passed (1 failure = pre-existing TTY baseline, unrelated)
- No auth/no-negative/no-secret regressions
- No out-of-scope changes

## Verification Summary

- Unit tests: 315 OK
- Evals: 664 passed, 1 failed (pre-existing TTY baseline), 0 skipped
- git diff --check: clean
- Combined A+B patch applies cleanly
