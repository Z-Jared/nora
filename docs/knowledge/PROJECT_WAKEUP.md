# Nora Project Wakeup

Last updated: 2026-06-08

## Mission

Nora is pivoting toward a customizable electronic pet agent: a digital lifeform each user can define, feed, talk to, grow with, and ask for real help.

The user-facing product direction is not "chatbot plus avatar" and not merely "Agent OS dashboard." Nora should feel like a living pet companion with identity, hunger, energy, mood, bond, taste, voice, room presence, and long-term relationship memory.

The existing Agent OS / Durable Runtime work remains important, but it becomes the hidden runtime that powers the pet's skills, memory, safety, tasks, and tool execution. The long-term product architecture is:

```text
Nora Pet Agent
  = customizable electronic lifeform
  + token food economy
  + multimodal brain
  + 2D/Live2D avatar and room
  + voice and expression system
  + agent skill runtime
  + long-term relationship memory
```

The pet should be commercially viable: food represents token-backed compute energy, membership expands memory/voice/room/pet slots, and skill/avatar/voice/plugin packs create marketplace upside. Nora must not use pet distress to manipulate purchases; token balance and estimated consumption must be transparent.

## Target Architecture North Star

Use `docs/knowledge/NORA_PET_AGENT_DIRECTION.md` as the product-direction contract for the pivot. Every major user-facing task should be judged by whether it advances Nora toward:

- A pet room as the first screen.
- User-defined pet identity, appearance, personality, voice, taste, relationship role, and skills.
- Deterministic pet state: hunger, energy, mood, bond, growth, compute food balance, and relationship memories.
- Token-backed food economy with transparent balance and estimated cost.
- Multimodal cognition for text, voice, image, and screen understanding.
- Voice and expression systems tied to the pet identity.
- Agent skills presented as pet abilities rather than raw tools.
- Cross-device pet presence on desktop, phone, tablet, and web.

Use `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` and `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md` as runtime contracts underneath the pet product. Runtime work remains valuable when it supports:

- Durable tasks that can pause, resume, replay, inspect, and recover.
- A runtime kernel with scheduler, event log, state store, permission manager, tool broker, context compiler, and model router.
- A skill registry, plugin runtime, and capability router for professional and industry workflows.
- Multi-agent execution with isolated workers, review gates, and deterministic handoff artifacts.
- Auditable local-first operation where every model call, tool call, file edit, test, approval, and error is traceable.

PM-generated tasks for the pivot must name the product layer they affect: Pet Identity, Pet State Engine, Token Food Economy, Avatar/Room UI, Voice/Expression System, Multimodal Cognition, Skill Runtime, Memory/Relationship System, Monetization/Billing, Safety/Policy, or Cross-Device Presence. Runtime-heavy tasks should still reference the relevant Agent OS architecture layer.

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

- Nora's product north star is now a customizable electronic pet agent. Agent OS / Durable Runtime becomes the hidden runtime foundation rather than the default user-facing product.
- The first user impression should be a pet room and living companion, not a terminal, task dashboard, or raw tool list.
- Food represents token-backed compute energy. The pet remains alive and available for light care when balance is empty, but expensive chat, voice, screen, coding, research, browser, and plugin actions require compute food.
- Multimodal models are feasible as the pet's cognition layer, but deterministic systems must own balances, payments, life state, permissions, and durable memory writes.
- MVP avatar work should start with modular 2D / Live2D-style expression. Full 3D/VRM, AR, and immersive rooms are later-stage expansions.
- Nora should keep lightweight RAG as an auxiliary feature, not as the core coding-agent brain.
- Code understanding should prioritize agentic search, AST/symbol search, import/call relationships, task-specific context compilation, trace memory, and review gates.
- Nora should support industry and professional workflows through modular skill packs plus governed plugins/connectors. Skill packs provide terminology, workflows, templates, risk boundaries, and evals. Plugins provide external system access with auth, permissions, sensitivity labels, confirmation rules, and event logging.
- Personal Nora should optimize for a local-first professional workbench with low friction, strong memory, private data, resumable tasks, and useful deliverables.
- Enterprise Nora should optimize for governed agent runtime needs: RBAC, SSO, audit logs, policy controls, isolated worker pools, internal connectors, approvals, cost metrics, reliability, and compliance.
- The 2026-06-03 frontier scan pushes Nora's next runtime priorities toward scheduler automation, hook/policy kernel, graph-shaped traces, plugin manifests, skill manifests, capability routing, Agent OS dashboard, end-to-end workflow evals, and minimal model routing.
- Nora's orchestration complexity now justifies comparing LangChain, LangGraph, and OpenAI Agents SDK as references, but the default remains Nora's custom local-first durable runtime unless a specific subsystem clearly outgrows it.
- `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md` is now the PM task-generation contract. Future PM loops should issue tasks according to its architecture layers, core objects, workflow, and review checklist.
- Every daily frontier scan should answer how Codex, Claude Code, MCP, OpenAI Agents SDK, and new research should change Nora's roadmap.
- The project needs a persistent knowledge base because new Codex windows do not automatically inherit prior conversation context.

## Current Product Maturity

Nora is a usable local agent-runtime alpha, but it is not yet a pet product:

- CLI, HTTP server, Web UI, SSE, WebSocket, OpenAPI docs.
- OpenAI-compatible, Anthropic, and Gemini providers.
- Toolkits, permission categories, file/Git/shell/browser/web/RAG/log/process tools.
- Short-term memory, long-term memory, task management, session save/load.
- Durable task/worker runtime primitives: worker registry/heartbeat/claim/auto-dispatch, lifecycle pause/resume/cancel, checkpoints, recovery planning, recovery events, timeline inspection, policy hook inspection, plugin/skill manifest inspection, capability routing, and model routing inspection.
- Worker lifecycle planning, guarded run-once automation, and guarded scheduler tick v1 have landed; the next step is turning scheduler ticks into a policy-backed loop with retry/backoff and blocked-reason explanations.
- A large Python test suite and deterministic eval suite.

Main gap versus the Pet Agent direction:

- No Pet Identity schema yet.
- No Pet State Engine for hunger, energy, mood, bond, taste, growth, and compute food.
- No token food balance, feeding flow, estimated consumption, or billing boundary.
- No pet room as first screen.
- No avatar, room, animation, or expression system.
- No voice profile or speech conversation layer.
- Agent tools are still exposed as tools instead of pet skills.
- Memory is not yet relationship-centered.
- Desktop/mobile presence is not designed or implemented.

## Near-Term Priority

Shift from Agent OS feature accumulation to Pet Agent MVP foundations:

1. Define `PetIdentity` and `PetState` schemas.
2. Build deterministic state transitions for feed, care, chat, rest, and work.
3. Add token food economy: balance, food types, feeding, cost estimation, recharge/API-key/local-model boundary, and no-manipulation rules.
4. Build the pet room MVP with avatar placeholder, food bowl, status, interaction buttons, activity log, and skill shelf.
5. Add relationship memory events for shared moments, taste preferences, task completion, and user preferences.
6. Add voice profile and preset voice/tone parameters.
7. Reframe existing tools as pet skills, starting with low-risk read-only skills and explicit permission prompts.
8. Add desktop floating pet and mobile widget/notification design after the room loop is usable.
9. Keep runtime safety, policy hooks, traces, model routing, and plugin/skill manifests as internal infrastructure that supports the pet product.

## Startup Protocol For A Fresh Window

1. Read this file.
2. Read `docs/knowledge/DECISIONS.md`.
3. Read `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`.
4. Read `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md`.
5. Read `docs/knowledge/CHAT_INDEX.md`.
6. Read `CLAUDE.md` or `AGENTS.md` depending on the runtime.
7. Read the assigned task file under `agent_tasks/`.
8. Run `git status --short --branch`.
9. Continue from the current task, not from stale memory.

## New Codex Window Wakeup Prompt

Paste this into a new Codex window opened in `/Users/mac/Documents/agent`:

```text
你现在接手 Nora/Agent 项目。请先读取 docs/knowledge/PROJECT_WAKEUP.md、docs/knowledge/DECISIONS.md、docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md、docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md、docs/knowledge/CHAT_INDEX.md、AGENTS.md，然后运行 git status --short --branch 和 git log --oneline --decorate -8。不要凭空假设旧聊天上下文，以项目知识库和当前仓库状态为准。
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
