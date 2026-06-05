# Nora Knowledge Base

This directory is the persistent project memory for Nora development.

New Codex or Claude Code windows should read these files before starting work:

1. `PROJECT_WAKEUP.md`
2. `DECISIONS.md`
3. `AGENT_OS_DURABLE_RUNTIME.md`
4. `NORA_FRAMEWORK_ARCHITECTURE.md`
5. `CHAT_INDEX.md`
6. The current task file under `agent_tasks/`

## What Belongs Here

- Project direction and strategy.
- Agent OS / Durable Runtime architecture decisions.
- Nora framework architecture and PM task-generation contracts.
- Stable decisions from chats.
- Daily AI agent radar summaries.
- Imported Codex conversation transcripts for this repository.
- Handoff notes that help a fresh window resume without relying on hidden chat context.

## What Does Not Belong Here

- API keys, tokens, secrets, private credentials, or `.env` contents.
- Raw tool dumps that do not affect project decisions.
- Large generated artifacts that can be reproduced.

## Importing Codex Sessions

Run:

```bash
python3 scripts/import_codex_sessions.py
```

The importer reads local Codex active sessions and archived sessions, then imports only sessions whose recorded `cwd` exactly matches this repository root.

For this project, the scope is:

```text
/Users/mac/Documents/agent
```

It does not import other Codex projects, global chats, or unrelated sessions.

It intentionally skips system/developer instructions and tool outputs by default.
