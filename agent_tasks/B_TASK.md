# Claude B Task

Owner: Claude B
Status: assigned

## Goal

Fix the two review findings from the task/memory Web UI/API work.

## Finding 1: `/memory/save` Returns Wrong Record

Current problem:
- `POST /memory/save` saves successfully.
- Then `http_server.py` calls `list_records(max_results=1)`.
- With JSONL storage, that returns the first old record, not the newly saved record.

Required behavior:
- `POST /memory/save` must return the exact record that was just saved.
- This must work for both JSONL and SQLite-backed memory.

Acceptable approaches:
- Have `LongTermMemory.save()` return a structured result or memory id, then read that exact record.
- Or add `get_record(memory_id)` and use it after save.

Important:
- Preserve compatibility with existing tool usage if other code expects `LongTermMemory.save()` to return a string. If changing the return type, update all callers and tests deliberately.

Add a regression test:
- Save first memory.
- Save second memory.
- Assert the second response body `memory.text` is the second memory.

## Finding 2: Finish Task Summary Mismatch

Current problem:
- Web UI prompt says `Task summary (optional)`.
- Backend requires non-empty `summary` and returns 400 otherwise.

Required behavior:
- Keep backend summary required.
- Update desktop and mobile UI so empty summary is not submitted.
- The prompt/copy must not say optional.
- Show a clear UI state message if user tries to finish without summary.

## Tests

Required checks before writing `B_DONE.md`:

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('mini_agent/static/index.html','utf8'); const m=html.match(/<script>([\s\S]*)<\/script>/); new Function(m[1]); console.log('script syntax ok')"
python3 -m unittest tests.test_http_server.HTTPServerStaticTests tests.test_http_server.HTTPTaskTests tests.test_http_server.HTTPTaskAuthTests tests.test_http_server.HTTPMemoryTests tests.test_http_server.HTTPMemoryAuthTests
python3 -m unittest discover -s tests
git diff --check
```

## Completion Report

Write `agent_tasks/B_DONE.md` with:
- Summary of changes.
- `git diff --stat`.
- Exact test commands and results.
- Any known issues or skipped tests.
- Confirmation that no push was performed.

Then run:

```bash
agent_tasks/notify_codex.sh B
```
