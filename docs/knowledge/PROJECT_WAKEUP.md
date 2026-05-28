# Nora Project Wakeup

Last updated: 2026-05-28

## Mission

Nora is being built to catch and eventually surpass Claude Code and Codex as a local-first coding agent system.

The project direction is not "chatbot plus tools." Nora should evolve into a local-first, multi-agent, auditable engineering runtime with strong project memory, safe execution, review gates, traceability, and fast adaptation to current AI agent research.

## Current Operating Model

- Codex acts as project manager, reviewer, and committer.
- Claude Code windows act as implementation workers.
- Claude A reads `agent_tasks/A_TASK.md`.
- Claude B reads `agent_tasks/B_TASK.md`.
- Workers do not push or commit unless explicitly told.
- Codex PM reviews worker output, runs tests, decides commits, and controls push timing.

## Current Repository State To Verify

Fresh windows must run:

```bash
git status --short --branch
git log --oneline --decorate -8
```

Known state at this update:

- `main` was ahead of `origin/main` by 2 local commits.
- `/session/list` compatibility work was in progress.
- `agent_tasks/A_TASK.md` and `agent_tasks/B_TASK.md` were assigned for the compatibility/documentation pass.
- `AGENTS.md` existed but needed alignment with the Claude A/B worker model.

Do not assume this state is still current. Verify before editing.

## Recent Decisions

- Nora should keep lightweight RAG as an auxiliary feature, not as the core coding-agent brain.
- Code understanding should prioritize agentic search, AST/symbol search, import/call relationships, task-specific context compilation, trace memory, and review gates.
- Every daily frontier scan should answer how Codex, Claude Code, MCP, OpenAI Agents SDK, and new research should change Nora's roadmap.
- The project needs a persistent knowledge base because new Codex windows do not automatically inherit prior conversation context.

## Current Product Maturity

Nora is a usable local alpha approaching beta:

- CLI, HTTP server, Web UI, SSE, WebSocket, OpenAPI docs.
- OpenAI-compatible, Anthropic, and Gemini providers.
- Toolkits, permission categories, file/Git/shell/browser/web/RAG/log/process tools.
- Short-term memory, long-term memory, task management, session save/load.
- A large Python test suite; recent full run reported 878 tests passing.

Main gap versus Claude Code/Codex:

- Agent runtime reliability.
- Worker isolation and merge workflow.
- Context compiler.
- Trace replay and review gates.
- Evaluation harness.
- Hook/plugin/MCP ecosystem.

## Near-Term Priority

Finish the `/session/list` API compatibility fix:

- Preserve legacy `sessions` string for old HTTP clients.
- Keep structured data under `sessions_structured`.
- Update Web UI to prefer structured data and fall back to legacy string.
- Update README/OpenAPI docs.
- Run focused tests, then full unittest suite.

After that, shift from feature accumulation to agent-runtime foundations:

1. Trace every model/tool/edit/test/review event.
2. Build a context compiler.
3. Isolate workers in separate worktrees or patch queues.
4. Add lifecycle hooks.
5. Add an eval harness for real coding tasks.
6. Add MCP/plugin support.

## Startup Protocol For A Fresh Window

1. Read this file.
2. Read `docs/knowledge/DECISIONS.md`.
3. Read `docs/knowledge/CHAT_INDEX.md`.
4. Read `CLAUDE.md` or `AGENTS.md` depending on the runtime.
5. Read the assigned task file under `agent_tasks/`.
6. Run `git status --short --branch`.
7. Continue from the current task, not from stale memory.

## Conversation Memory Scope

The project knowledge base should contain only Nora/Agent project conversations.

The importer must only include Codex sessions whose recorded working directory is exactly:

```text
/Users/mac/Documents/agent
```

Do not mix in unrelated Codex chats from other projects.
