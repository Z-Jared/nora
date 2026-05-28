# Durable Task Schema — v1 Spec

Last updated: 2026-05-29

Status: specification only (not yet implemented)

## Purpose

This document defines the data model for Nora's durable task runtime. It replaces the ad-hoc `current_task.json` / `task_history.jsonl` model with a structured schema that supports pause/resume, checkpointing, multi-worker coordination, and replayable execution.

## Task Record

A **DurableTask** is the top-level unit of work. It owns one or more **runs** (attempts) and tracks lifecycle state across interruptions, retries, and handoffs.

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `task_id` | `string` | yes | Globally unique task identifier, e.g. `dtask_1`. |
| `run_id` | `string` | yes | Identifier for the current execution attempt, e.g. `run_1`. A new `run_id` is generated on each resume. |
| `parent_task_id` | `string \| null` | no | Links a subtask to its parent. `null` for top-level tasks. |
| `status` | `enum` | yes | Current lifecycle state (see below). |
| `goal` | `string` | yes | Human-readable task objective. |
| `steps` | `Step[]` | yes | Ordered list of planned steps. |
| `current_step` | `int \| null` | no | Index (1-based) of the step currently being executed. `null` when not actively executing. |
| `checkpoints` | `Checkpoint[]` | no | Ordered list of saved execution checkpoints. |
| `input_summary` | `string` | no | Truncated preview of the original user input that created this task. |
| `context_pack_ref` | `string \| null` | no | Reference to a compiled `ContextPack` (e.g. `cpack_1`). |
| `trace_refs` | `string[]` | no | List of `trace_id` values from the trace store that are linked to this task. |
| `worker_id` | `string \| null` | no | Identifier of the worker (Claude A, Claude B, etc.) currently assigned. |
| `created_at` | `string` | yes | ISO-8601 UTC timestamp of task creation. |
| `updated_at` | `string` | yes | ISO-8601 UTC timestamp of last state change. |
| `finished_at` | `string \| null` | no | ISO-8601 UTC timestamp when task reached a terminal state. |
| `failure_reason` | `string` | no | Free-text reason when status is `failed` or `cancelled`. |
| `resume_policy` | `enum` | no | How the task should behave on resume: `from_checkpoint`, `from_step`, `from_beginning`. Default: `from_checkpoint` if checkpoints exist, else `from_step`. |

### Status Enum

```
pending     — created, not yet started
running     — actively executing a step
paused      — intentionally suspended; can be resumed
blocked     — waiting on external input or dependency
completed   — all steps done successfully
failed      — unrecoverable error
cancelled   — user or system cancelled the task
```

Valid transitions:

```
pending   → running, cancelled
running   → paused, blocked, completed, failed, cancelled
paused    → running, cancelled
blocked   → running, cancelled
completed → (terminal)
failed    → (terminal)
cancelled → (terminal)
```

### Step Record

Each step within a `DurableTask`:

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `int` | yes | 1-based step index. |
| `text` | `string` | yes | Human-readable step description. |
| `status` | `enum` | yes | `pending`, `in_progress`, `done`, `blocked`, `skipped`. |
| `note` | `string` | no | Worker note or blocker explanation. |
| `summary` | `string` | no | Completion summary. |
| `tool_hint` | `string` | no | Suggested tool category for this step. |
| `checkpoint_ref` | `string \| null` | no | Reference to the checkpoint saved after this step. |

### Checkpoint Record

A **Checkpoint** captures resumable execution state at a point in time.

| Field | Type | Required | Description |
|---|---|---|---|
| `checkpoint_id` | `string` | yes | Unique identifier, e.g. `cp_1`. |
| `step_id` | `int` | yes | The step that was current when this checkpoint was created. |
| `run_id` | `string` | yes | The run that produced this checkpoint. |
| `created_at` | `string` | yes | ISO-8601 UTC timestamp. |
| `state_snapshot` | `object` | yes | Serialized runtime state (model context, tool results, variables). |
| `description` | `string` | no | Human-readable checkpoint description. |

## Task Lifecycle

```
intake → plan → execute → checkpoint → [pause/resume] → review → complete
                                      ↘ fail
                                      ↘ cancel
```

### 1. Intake

- User provides a goal (natural language).
- Runtime creates a `DurableTask` with status `pending`.
- `input_summary` is populated (truncated, sensitive-redacted).
- Worker is assigned (`worker_id`).

### 2. Plan

- Runtime generates ordered steps from the goal.
- Steps are stored in the `steps` array, all initially `pending`.
- Optionally, a `context_pack_ref` is compiled via `ContextCompiler`.

### 3. Execute

- Runtime transitions task to `running`.
- `current_step` points to the active step.
- The worker executes the step: model calls, tool calls, file edits, tests.
- Events are logged to the trace store; `trace_refs` accumulate.

### 4. Checkpoint

- After a meaningful step completes, a `Checkpoint` is created.
- The checkpoint captures enough state to resume execution.
- Steps can reference their checkpoint via `checkpoint_ref`.

### 5. Pause / Resume

- **Pause**: Task transitions from `running` → `paused`. The latest checkpoint is the resume point.
- **Resume**: A new `run_id` is generated. Task transitions from `paused` → `running`. Execution resumes from the checkpoint (or current step if no checkpoint exists), governed by `resume_policy`.

### 6. Review

- After all steps are `done` (or on demand), automated checks and review gates run.
- Review gates can block completion (e.g. tests fail, lint errors, review not approved).

### 7. Complete / Fail / Cancel

- **Complete**: All steps done, review passed. Status → `completed`, `finished_at` set.
- **Fail**: Unrecoverable error. Status → `failed`, `failure_reason` populated.
- **Cancel**: User or system cancels. Status → `cancelled`, `failure_reason` populated.

## Relationship to Existing Modules

### `mini_agent/task_runner.py`

The current `TaskManager` uses a flat `current_task.json` with `goal/status/steps` and `task_history.jsonl`. The durable task schema is a superset:

- `DurableTask.task_id` replaces the implicit single-task model.
- `DurableTask.steps[].tool_hint` formalizes `_suggest_tool_type()`.
- `DurableTask.status` adds `paused`, `blocked`, `failed`, `cancelled` (current only has `active`/`finished`).
- `DurableTask.checkpoints`, `run_id`, `resume_policy` are entirely new.

Migration path: `TaskManager` becomes a thin CLI/API wrapper over `DurableTaskStore`. The JSON/DB backends converge.

### `mini_agent/traces.py`

`TraceStore` already records `RunTrace` per turn. The durable schema links traces to tasks:

- `DurableTask.trace_refs` points to `trace_id` values in `TraceStore`.
- A single task can accumulate multiple traces (one per turn or execution attempt).
- `RunTrace` stays as-is; the link is by reference, not by embedding.

### `mini_agent/context_compiler.py`

`ContextCompiler` produces `ContextPack` objects. The durable schema references them:

- `DurableTask.context_pack_ref` points to a stored context pack.
- Context packs can be recompiled on resume if the repo state has changed.

### `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`

This schema implements Priority 2 ("Durable task state") from the architecture north star. It enables:

- Pause/resume/cancel semantics.
- Checkpoint-based recovery.
- Multi-task and multi-worker coordination via `task_id` / `worker_id` / `parent_task_id`.
- Replay via trace linkage.

## Storage

Not yet implemented. Expected backends:

- **SQLite** (via `NoraDB`): primary store for `DurableTask`, `Step`, `Checkpoint` records.
- **JSONL**: fallback / export format.

Table sketch (not final):

```sql
CREATE TABLE durable_tasks (
    task_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    parent_task_id TEXT,
    status TEXT NOT NULL,
    goal TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    current_step INTEGER,
    checkpoints_json TEXT,
    input_summary TEXT,
    context_pack_ref TEXT,
    trace_refs_json TEXT,
    worker_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT,
    failure_reason TEXT,
    resume_policy TEXT
);
```

## Open Questions

- Should checkpoints store full model context or just pointers?
- How should `parent_task_id` interact with worker isolation (worktrees)?
- Should `resume_policy` be per-task or per-checkpoint?
- What is the maximum number of checkpoints per task before pruning?
- Should `trace_refs` support ranges (e.g. `trace_1..trace_5`) or only explicit IDs?
