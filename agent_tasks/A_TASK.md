# Claude A Task

Owner: Claude A
Status: completed

## Goal

Implement TASK-013: durable file-edit event logging.

Nora is moving toward an Agent OS / Durable Runtime. File edits must become auditable durable lifecycle events, just like task/tool/model calls, without storing raw file contents or patches.

## Scope

Add durable event logging for workspace file-edit operations:

1. Add event constants in `mini_agent/durable_events.py`:
   - `FILE_EDIT_STARTED`
   - `FILE_EDIT_FINISHED`
   - `FILE_EDIT_ERROR`
   - `FILE_EDIT_BLOCKED`
   - Include them in valid event type validation.

2. Hook file-edit lifecycle events in `mini_agent/toolkits/workspace.py`:
   - `write`
   - `replace`
   - `apply_unified_diff`
   - `apply_multi_file_patch`

3. Wire `DurableEventStore` into `WorkspaceFiles`, likely through `mini_agent/toolkits/registry_builder.py`.
   - Current construction order may need to change because `WorkspaceFiles` is built before `DurableEventStore`.
   - Keep the wiring small and compatible with existing direct `WorkspaceFiles(...)` tests.

## Payload Requirements

Event payloads must contain safe metadata only. Good examples:

- operation name
- path or paths
- file count
- bytes before / bytes after when easy and bounded
- status
- error type or blocked reason
- short sanitized reason preview if useful

Do not store:

- raw file content
- old/new replacement text
- full patch
- raw diff
- secrets or sentinel secret strings
- unbounded stdout/stderr/output

Event writes must be failure-isolated. A broken durable event store must not change the existing return behavior of file operations.

Blocked, denied, cancelled, or permission-rejected paths should be auditable as `FILE_EDIT_BLOCKED`, not `FILE_EDIT_FINISHED`.

Keep this task narrow. Do not add replay, rollback engine, scheduler work, broad refactors, or UI changes.

## Suggested Tests

Add focused coverage in `tests/test_durable_events.py` and/or existing workspace test files:

1. Successful `write` emits started + finished events with safe metadata.
2. `replace` and/or patch operations emit file metadata without raw content, raw replacement text, full patch, or raw diff.
3. Sensitive path denial emits blocked metadata without unsafe payloads.
4. Confirmation cancellation emits blocked metadata.
5. OS/write failure emits error metadata without changing existing return behavior.
6. Broken event store does not break write/replace/patch behavior.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_durable_events tests.test_workspace tests.test_workspace_patch
python3 evals/run_evals.py
```

If the implementation touches shared registry or durable event behavior, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with:

- summary
- diff stat
- exact checks run and pass/fail result
- known risks or limitations

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```

Do not commit or push.
