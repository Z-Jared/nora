# Claude A Task

Owner: Claude A
Status: assigned

## Goal

TASK-036: Supermemory optional memory toolkit v1.

Add an optional Supermemory-backed memory toolkit so Nora can save and recall external long-term memories when `SUPERMEMORY_API_KEY` is configured, without making the core agent depend on a network service.

## Scope

Implement narrowly. Prefer standard-library HTTP unless the project already has a suitable dependency. Do not add a new dependency unless unavoidable.

1. Add a small Supermemory client/toolkit:
   - Suggested module: `mini_agent/toolkits/supermemory.py`.
   - Read API key from `SUPERMEMORY_API_KEY`.
   - Read base URL from optional `SUPERMEMORY_BASE_URL`, defaulting to the official API base from Supermemory docs.
   - Provide safe, bounded functions for:
     - save memory/content.
     - search or recall memory by query.
     - fetch profile/context if the API supports it cleanly.
   - Use a `container_tag` or similar project/user namespace so Nora memory can be scoped to this repository/project.

2. Register tools in the default registry only when configured:
   - `supermemory_save`
   - `supermemory_search`
   - optionally `supermemory_profile`
   - If no API key is configured, either do not register tools or return a clear JSON error. Choose the pattern that best matches this codebase.

3. Safety:
   - Do not automatically upload prompts, tool outputs, diffs, files, env vars, secrets, shell output, or raw task traces.
   - The save tool should only save user-provided content.
   - Search/profile output must be bounded and should avoid dumping huge raw payloads.
   - Redact obvious secret-looking values before returning tool output if needed.
   - Network/API failure must return JSON error, not crash the agent loop.

4. Documentation:
   - Add a short README section or config note explaining `SUPERMEMORY_API_KEY`, optional base URL, and the privacy boundary.
   - Mention that Supermemory is optional and external.

## Suggested Tests

Use fake HTTP/client stubs. Do not call the real Supermemory API.

1. Tools are available or return configured error depending on chosen no-key behavior.
2. Save sends only explicit content plus namespace metadata, not env vars or raw prompts.
3. Search returns bounded JSON summaries.
4. API errors/timeouts return JSON errors.
5. Registry wiring does not break existing memory tools.
6. No configured key keeps full offline test suite passing.

## Verification

Run at minimum:

```bash
python3 -m unittest tests.test_mini_agent tests.test_tool_cache tests.test_durable_workers
python3 evals/run_evals.py
git diff --check
```

If you touch broad registry wiring, also run:

```bash
python3 -m unittest discover -s tests
```

## Completion Report

Update `agent_tasks/A_DONE.md` with summary, diff stat, exact checks run, and known risks or limitations.

Do not commit or push.
