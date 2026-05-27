# Claude A Task

Owner: Claude A
Status: assigned

## Goal

Improve Web UI session management without touching task or memory API logic.

## Scope

Implement a clearer session workflow in `mini_agent/static/index.html`:
- Save current conversation with a user-provided session name.
- Display saved sessions clearly.
- Load a session by clicking/selecting it.
- Keep New conversation, Save, and Load status messages accurate.
- Preserve and reuse current auth recovery behavior when token auth fails.

## Auth Requirements

Every session request must include the existing Authorization header helper:
- `GET /session/list`
- `POST /session/save`
- `POST /session/load`

If auth fails, reuse existing token recovery logic. Do not silently fail.

## Do Not Touch

- `mini_agent/memory.py`
- `mini_agent/task_runner.py`
- `/memory/*` backend behavior
- `/task/*` backend behavior

B is working on those areas.

## Tests

Add or update focused tests. Prefer existing `tests/test_http_server.py` static tests unless backend behavior truly changes.

Required checks before writing `A_DONE.md`:

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('mini_agent/static/index.html','utf8'); const m=html.match(/<script>([\s\S]*)<\/script>/); new Function(m[1]); console.log('script syntax ok')"
python3 -m unittest tests.test_http_server.HTTPServerStaticTests
python3 -m unittest discover -s tests
git diff --check
```

## Completion Report

Write `agent_tasks/A_DONE.md` with:
- Summary of changes.
- `git diff --stat`.
- Exact test commands and results.
- Any known issues or skipped tests.
- Confirmation that no push was performed.

Then run:

```bash
agent_tasks/notify_codex.sh A
```
