# Nora Development Decisions

## 2026-06-08: Product North Star Pivots To Customizable Electronic Pet Agent

Nora's product direction pivots from an Agent OS control surface to a customizable electronic pet agent. The existing Agent OS / Durable Runtime work remains useful as the hidden runtime, but the default user-facing product should become a pet room, identity, feeding, voice, memory, growth, and skill experience.

The new product formula is:

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

Implication:

- Treat `docs/knowledge/NORA_PET_AGENT_DIRECTION.md` as the product-direction contract for the pivot.
- User-facing work should prioritize pet identity, pet room, feeding, life state, voice, relationship memory, avatar expression, and skill use through the pet metaphor.
- Existing durable tasks, tools, traces, policy hooks, model routing, skill manifests, and plugin manifests should be reframed as pet runtime internals: shared goals, skills, diary, safety boundaries, thinking modes, skill packs, and equipment.
- Food represents token-backed compute energy. The product must show balance and estimated cost clearly and must not use pet distress to manipulate payment.
- Multimodal models may power cognition, voice, vision, screen understanding, and expression proposals, but deterministic systems must own balances, payments, life state, memory writes, permissions, and commercial rules.
- MVP avatar work should start with modular 2D / Live2D-style expression rather than blocking on full 3D. 3D/VRM, AR, and immersive rooms are later-stage expansions.
- PM-generated tasks for this pivot should name the affected layer: Pet Identity, Pet State Engine, Token Food Economy, Avatar/Room UI, Voice/Expression System, Multimodal Cognition, Skill Runtime, Memory/Relationship System, Monetization/Billing, Safety/Policy, or Cross-Device Presence.

## 2026-06-05: Framework Architecture Should Be Continuously Optimized

Nora's framework architecture is a living contract, not a one-time document. Codex PM and reviewer loops should continuously refine it from implementation evidence, eval results, review findings, user feedback, and frontier agent platform signals.

Implication:

- After PM review/integration, check whether the task revealed missing architecture layers, weak boundaries, repeated patterns, unsafe workflows, or eval gaps.
- After daily radar or user-requested information gathering, decide whether `NORA_FRAMEWORK_ARCHITECTURE.md`, `DECISIONS.md`, `PROJECT_WAKEUP.md`, or `DAILY_AI_AGENT_RADAR.md` need updates.
- Architecture updates should be small and explicit: trigger, affected layer, changed design rule, PM impact, reviewer impact, and verification evidence.
- Do not interrupt active worker implementation or expand task scope just because a new architecture idea appears, unless the active work violates safety, durability, or scope boundaries.
- Convert architecture changes into PM candidate tasks only when they include architecture layer, non-goals, safety boundaries, durable evidence, and verification path.

## 2026-06-05: Framework Architecture Becomes The PM Task Contract

`docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md` is the architecture contract for Nora development. Future Codex PM loops should use it when generating tasks, reviewing scope, and deciding whether work belongs on the roadmap.

Implication:

- PM-generated tasks must name the affected architecture layer: Durable Kernel, Scheduler, Worker Runtime, Policy Hook Kernel, Trace Graph, Tool/Plugin Broker, Skill/Capability Router, Context Compiler, Model Router, Eval/Review System, or Agent OS Dashboard.
- Tasks must include non-goals, safety boundaries, durable evidence, verification, and architecture references.
- Runtime work should prefer narrow vertical slices through the architecture over broad refactors.
- New automation should start read-only or dry-run, then add guarded execution only after deterministic eval coverage exists.
- Reviewers should use the architecture checklist when approving or requesting changes.

## 2026-06-03: Frontier Signals Push Nora Toward Scheduler, Policy Hooks, Trace Graphs, And Pluggable Capabilities

Current AI agent platform signals from Codex, Claude Code, OpenAI Agents SDK, MCP, and agent research reinforce Nora's existing Agent OS direction. The next improvement wave should convert Nora's durable primitives into a running, governed, observable runtime.

Implication:

- Promote worker lifecycle tools into a real scheduler loop that can periodically plan, dry-run, execute safe closeout actions, dispatch eligible work, retry with backoff, record durable events, and explain why work is blocked.
- Add a hook and policy kernel with lifecycle points such as `pre_tool`, `post_tool`, `pre_edit`, `post_edit`, `pre_shell`, `pre_git`, `pre_plugin_call`, `post_test`, `before_handoff`, and `before_commit`.
- Upgrade durable event records into inspectable trace graphs/spans across tasks, workers, model calls, tool calls, approvals, reviews, recovery actions, and plugin calls.
- Build plugin manifest/runtime foundations early, before integrating many industry tools. Plugin manifests must cover auth, tool schemas, permissions, data sensitivity, confirmation rules, output bounding, and event-log behavior.
- Build skill manifest/runtime foundations together with the context compiler, so skill packs contribute scoped terminology, workflows, templates, deliverable formats, and safety rules instead of becoming prompt dumps.
- Add a capability router that selects skills, plugins, model policy, risk level, and expected deliverables from the user's goal and available integrations.
- Redesign the UI as an Agent OS control surface: task queue, worker state, leases/workspaces, trace timeline, approvals, review gates, diffs, tests, recovery plans, plugin permissions, and enabled skills.
- Expand evals from registry/tool-level cases to end-to-end durable workflows: create task, dispatch worker, write isolated workspace, review gate, dry-run merge, apply, finalize, and recover from injected failures.
- Add a minimal model router that records why each model was selected, using cheaper models for routing/guardrails and stronger models for implementation, review, long context, or high-risk reasoning.
- Nora's orchestration complexity is now high enough to justify comparing LangChain, LangGraph, and OpenAI Agents SDK as references, but not enough to justify migrating away from Nora's local-first durable runtime by default.

## 2026-06-01: Skill Packs And Plugin Runtime Are Part Of The Product Direction

Nora should serve both personal and enterprise users across industries by combining the Agent OS / Durable Runtime with modular professional capabilities.

Implication:

- Treat `Nora = Agent OS Core + Skill Packs + Plugin Runtime + Capability Router` as the long-term product architecture.
- Embed the skill-loading, plugin-loading, permission, trace, and routing mechanisms in Nora core.
- Keep concrete industry knowledge modular as skill packs instead of hard-coding all domains into one giant prompt.
- Skill packs should contain terminology, workflows, templates, deliverable formats, risk boundaries, quality checks, and evals.
- Plugins/connectors should expose external systems through manifests that declare auth, tool schemas, permissions, data sensitivity, confirmation rules, and event-log behavior.
- Personal Nora should be a local-first professional workbench with strong memory, private data, resumable tasks, and useful deliverables.
- Enterprise Nora should be a governed agent runtime platform with RBAC, SSO, audit logs, policies, isolated worker pools, internal connectors, approvals, reliability metrics, and compliance.
- Start with lower-risk, high-fit skills: software engineering, product/project management, research/consulting, spreadsheet/finance/operations analysis, and content creation.
- Treat legal, healthcare, investment, tax, and regulated finance as high-risk domains that require stronger source tracking, disclaimers, human confirmation, and policy gates.

## 2026-05-29: North Star Is Agent OS / Durable Runtime

Nora's target is higher than "coding agent," "personal assistant," or "RAG knowledge app." The project should be steered toward an Agent OS / Durable Runtime: a local-first operating layer where agents can execute long-running tasks with durable state, replayable traces, permissioned tools, worker scheduling, review gates, and recoverable failures.

Implication:

- Treat the runtime kernel as the core product: scheduler, event log, state store, permission manager, tool broker, context compiler, model router, hooks, and eval harness.
- Build features as durable workflows, not isolated chat commands.
- Prefer event-sourced traces and resumable task state over hidden chat history.
- Use RAG only as one context source; the main memory path is structured task state, traces, context packs, and review artifacts.
- Evaluate against durable operating capabilities: pause/resume, replay, isolate workers, audit actions, recover from failures, and coordinate multiple agents.

## 2026-05-28: Build Toward Frontier Coding Agent Runtime

Nora's goal is to catch and surpass Claude Code and Codex, not merely become a general local assistant.

Implication:

- Prioritize coding-agent reliability, traceability, multi-agent workflow, safe execution, context quality, and evaluations.
- Avoid spending major effort on generic chatbot features unless they support engineering execution.

## 2026-05-28: RAG Is Auxiliary, Not The Main Code Understanding Path

Traditional vector RAG over a codebase is no longer treated as the core architecture for coding agents.

Implication:

- Keep lightweight RAG for docs, long text, logs, external knowledge, and user memory.
- Prefer agentic search, `rg`, AST/symbol indexing, import graphs, tests, diffs, and context compilation for code understanding.

## 2026-05-28: Persistent Project Memory Is Required

New Codex windows lose hidden chat context, which makes project continuity fragile.

Implication:

- Maintain `docs/knowledge/PROJECT_WAKEUP.md` as the first-read file for every new window.
- Import local Codex transcripts into `docs/knowledge/codex_sessions/`.
- Keep task files and DONE reports as part of the project record.

## 2026-05-28: Multi-Agent Workflow Uses Codex PM And Claude Workers

Codex owns planning, review, commits, and push decisions. Claude A/B are implementation workers.

Implication:

- Claude A/B only work from their assigned task files.
- Workers write DONE reports.
- Codex PM reviews, tests, and integrates.
