# Nora Project Wakeup

Last updated: 2026-06-03

## Mission

Nora is being built to catch and eventually surpass Claude Code and Codex by becoming an Agent OS / Durable Runtime, not just a local coding assistant.

The project direction is not "chatbot plus tools" and not merely "coding agent plus UI." Nora should evolve into a local-first operating layer for durable agents: persistent task state, resumable execution, event-sourced traces, permissioned tools, worker scheduling, review gates, context compilation, and fast adaptation to current AI agent research.

Nora should also become a professional agent platform that can serve personal and enterprise users across industries. The long-term architecture is:

```text
Nora = Agent OS Core + Skill Packs + Plugin Runtime + Capability Router
```

Industry ability should be embedded as a system mechanism, not as one giant prompt. Skill packs teach Nora how an industry works; plugins let Nora operate industry tools through permissioned, auditable connectors.

## Target Architecture North Star

Use `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` as the architecture north star. Every major task should be judged by whether it advances Nora toward:

- Durable tasks that can pause, resume, replay, inspect, and recover.
- A runtime kernel with scheduler, event log, state store, permission manager, tool broker, context compiler, and model router.
- A skill registry, plugin runtime, and capability router for professional and industry workflows.
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

- `main` was aligned with `origin/main`.
- Recent completed work reached TASK-059: durable worker auto-dispatch, durable task lifecycle controls, checkpoints, recovery planning, recovery-plan events, and durable task timeline inspection all landed with deterministic eval coverage.
- `agent_tasks/BACKLOG.md` had no pending or in-progress tasks at this update.
- The working tree contained only knowledge-documentation updates about skill packs, plugin runtime, and capability routing.

Do not assume this state is still current. Verify before editing.

## Recent Decisions

- Nora's north star is Agent OS / Durable Runtime, above ordinary coding-agent or RAG-app positioning.
- Nora should keep lightweight RAG as an auxiliary feature, not as the core coding-agent brain.
- Code understanding should prioritize agentic search, AST/symbol search, import/call relationships, task-specific context compilation, trace memory, and review gates.
- Nora should support industry and professional workflows through modular skill packs plus governed plugins/connectors. Skill packs provide terminology, workflows, templates, risk boundaries, and evals. Plugins provide external system access with auth, permissions, sensitivity labels, confirmation rules, and event logging.
- Personal Nora should optimize for a local-first professional workbench with low friction, strong memory, private data, resumable tasks, and useful deliverables.
- Enterprise Nora should optimize for governed agent runtime needs: RBAC, SSO, audit logs, policy controls, isolated worker pools, internal connectors, approvals, cost metrics, reliability, and compliance.
- The 2026-06-03 frontier scan pushes Nora's next runtime priorities toward scheduler automation, hook/policy kernel, graph-shaped traces, plugin manifests, skill manifests, capability routing, Agent OS dashboard, end-to-end workflow evals, and minimal model routing.
- Nora's orchestration complexity now justifies comparing LangChain, LangGraph, and OpenAI Agents SDK as references, but the default remains Nora's custom local-first durable runtime unless a specific subsystem clearly outgrows it.
- Every daily frontier scan should answer how Codex, Claude Code, MCP, OpenAI Agents SDK, and new research should change Nora's roadmap.
- The project needs a persistent knowledge base because new Codex windows do not automatically inherit prior conversation context.

## Current Product Maturity

Nora is a usable local alpha approaching beta:

- CLI, HTTP server, Web UI, SSE, WebSocket, OpenAPI docs.
- OpenAI-compatible, Anthropic, and Gemini providers.
- Toolkits, permission categories, file/Git/shell/browser/web/RAG/log/process tools.
- Short-term memory, long-term memory, task management, session save/load.
- Durable task/worker runtime primitives: worker registry/heartbeat/claim/auto-dispatch, lifecycle pause/resume/cancel, checkpoints, recovery planning, recovery events, and timeline inspection.
- Worker lifecycle planning and guarded run-once automation are in progress; the next step is turning them into a scheduler loop with durable decision events.
- A large Python test suite; recent full run reported 1963 tests passing, and deterministic evals reported 304 passed.

Main gap versus an Agent OS / Durable Runtime:

- Deeper runtime execution semantics beyond state tools: actual isolated worker execution, automatic scheduling, replay, and rollback.
- Worker isolation, sandboxing, scheduling, and merge workflow.
- Permission kernel, policy hooks, review gates, and rollback.
- Evaluation harness for real coding and operating-system-like agent tasks.
- Real model routing and cost/latency/reliability policy.
- UI redesign for inspecting tasks, traces, workers, approvals, diffs, tests, recovery points, and timelines.
- Skill pack runtime for industry-specific professional workflows.
- Plugin runtime and capability routing for external industry tools.

## Near-Term Priority

Shift from feature accumulation to deeper agent-runtime foundations:

1. Finish worker lifecycle planner/run-once work, then promote it into a scheduler loop that can periodically plan, dry-run, safely execute closeouts, dispatch eligible work, retry with backoff, and explain blocked work.
2. Add a hook and policy kernel for filesystem, shell, browser, network, Git, plugin, model, test, handoff, compact, commit, and high-risk actions.
3. Upgrade durable events into graph-shaped traces/spans for task, worker, model, tool, plugin, approval, review, test, handoff, and recovery activity.
4. Add plugin manifests and runtime foundations: auth, tool schemas, permission mapping, sensitivity labels, confirmation rules, output bounding, and event logging.
5. Add skill manifests and context-compiler integration for industry workflows: terminology, workflows, templates, deliverable formats, required plugins, risk boundaries, and evals.
6. Add capability routing that chooses skills, plugins, model policy, risk level, and expected deliverables from the user's goal.
7. Redesign the UI into an Agent OS dashboard for task state, traces, approvals, workers, leases/workspaces, timelines, checkpoints, recovery plans, diffs, tests, plugin permissions, and enabled skills.
8. Build end-to-end durable-runtime evals, not only unit-level registry behavior.
9. Add minimal model routing by task type, tool-calling quality, cost, latency, context length, reliability, and risk level.

Initial skill pack priority should stay close to Nora's strengths: software engineering, product/project management, research/consulting, spreadsheet/finance/operations analysis, and content creation. Higher-risk domains such as legal, healthcare, investment, tax, and regulated finance need stronger source tracking, disclaimers, human confirmation, and policy gates.

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
