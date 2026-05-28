# Nora Project Wakeup

Last updated: 2026-05-29

## Mission

Nora is being built to catch and eventually surpass Claude Code and Codex by becoming an Agent OS / Durable Runtime, not just a local coding assistant.

The project direction is not "chatbot plus tools" and not merely "coding agent plus UI." Nora should evolve into a local-first operating layer for durable agents: persistent task state, resumable execution, event-sourced traces, permissioned tools, worker scheduling, review gates, context compilation, and fast adaptation to current AI agent research.

## Target Architecture North Star

Use `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` as the architecture north star. Every major task should be judged by whether it advances Nora toward:

- Durable tasks that can pause, resume, replay, inspect, and recover.
- A runtime kernel with scheduler, event log, state store, permission manager, tool broker, context compiler, and model router.
- Multi-agent execution with isolated workers, review gates, and deterministic handoff artifacts.
- Auditable local-first operation where every model call, tool call, file edit, test, approval, and error is traceable.

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

- Nora's north star is Agent OS / Durable Runtime, above ordinary coding-agent or RAG-app positioning.
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

Main gap versus an Agent OS / Durable Runtime:

- Durable execution semantics: pause/resume/replay/recover for long-running tasks.
- Event-sourced trace store across model/tool/edit/test/review events.
- Worker isolation, scheduling, and merge workflow.
- Context compiler and project memory that are structured, scoped, and auditable.
- Permission kernel, policy hooks, review gates, and rollback.
- Evaluation harness for real coding and operating-system-like agent tasks.
- Hook/plugin/MCP ecosystem.

## Near-Term Priority

Finish the `/session/list` API compatibility fix:

- Preserve legacy `sessions` string for old HTTP clients.
- Keep structured data under `sessions_structured`.
- Update Web UI to prefer structured data and fall back to legacy string.
- Update README/OpenAPI docs.
- Run focused tests, then full unittest suite.

After that, shift from feature accumulation to agent-runtime foundations:

1. Define the durable task/event schema.
2. Trace every model/tool/edit/test/review event into a replayable store.
3. Build the context compiler.
4. Isolate workers in separate worktrees or patch queues.
5. Add lifecycle hooks, permission policies, and review gates.
6. Add an eval harness for real coding and durable-runtime tasks.
7. Add MCP/plugin support.

## Startup Protocol For A Fresh Window

1. Read this file.
2. Read `docs/knowledge/DECISIONS.md`.
3. Read `docs/knowledge/CHAT_INDEX.md`.
4. Read `CLAUDE.md` or `AGENTS.md` depending on the runtime.
5. Read the assigned task file under `agent_tasks/`.
6. Run `git status --short --branch`.
7. Continue from the current task, not from stale memory.

## New Codex Window Wakeup Prompt

Paste this into a new Codex window opened in `/Users/mac/Documents/agent`:

```text
你现在接手 Nora/Agent 项目。请先读取 docs/knowledge/PROJECT_WAKEUP.md、docs/knowledge/DECISIONS.md、docs/knowledge/CHAT_INDEX.md、AGENTS.md，然后运行 git status --short --branch 和 git log --oneline --decorate -8。不要凭空假设旧聊天上下文，以项目知识库和当前仓库状态为准。
```

If Codex Desktop shows no old conversation list, do not treat that as memory loss. The durable project memory is this repository's `docs/knowledge/` directory plus the desktop snapshot folder:

```text
/Users/mac/Desktop/nora-agent-snapshots
```

The local Codex CLI session database may still contain old chats under `~/.codex/sessions`, `~/.codex/archived_sessions`, `~/.codex/session_index.jsonl`, and `~/.codex/state_5.sqlite`; the ChatGPT/Codex Desktop UI uses separate local caches under `~/Library/Application Support/com.openai.chat`, and those Codex task cache folders can be empty even when CLI sessions still exist.

## Conversation Memory Scope

The project knowledge base should contain only Nora/Agent project conversations.

The importer must only include Codex sessions whose recorded working directory is exactly:

```text
/Users/mac/Documents/agent
```

Do not mix in unrelated Codex chats from other projects.
