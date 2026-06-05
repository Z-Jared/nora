# Nora Framework Architecture

Last updated: 2026-06-05

## Purpose

This document is the architecture contract for Nora development. Codex PM, reviewers, and worker task authors must use it when generating implementation tasks, reviewing scope, and deciding whether a change advances the project.

Nora is not a generic chatbot, a prompt library, or a thin wrapper around a third-party agent framework. Nora is a local-first Agent OS / Durable Runtime for personal and enterprise work. Its core value is durable, auditable, recoverable, permissioned execution across code, files, tools, workers, skills, and plugins.

Every PM-issued task should either:

- Strengthen one of the architecture layers below.
- Add a narrow vertical slice through those layers.
- Add deterministic eval coverage for a layer or workflow.
- Improve user-facing visibility into task, worker, trace, policy, skill, plugin, or model state.

Tasks that only add isolated features without durable state, traceability, permission semantics, or eval coverage should be treated as low priority unless they unblock the architecture.

## Core Thesis

The framework shape is:

```text
Nora Runtime
  = Durable Kernel
  + Scheduler
  + Worker Runtime
  + Policy Hook Kernel
  + Trace Graph
  + Tool/Plugin Broker
  + Skill/Capability Router
  + Context Compiler
  + Model Router
  + Eval/Review System
  + Agent OS Dashboard
```

The product shape is:

```text
Nora = Agent OS Core + Skill Packs + Plugin Runtime + Capability Router
```

The implementation strategy is:

- Keep Nora's local-first durable runtime as the core.
- Use LangChain, LangGraph, OpenAI Agents SDK, Claude Code, Codex, and MCP as references, not as default replacements.
- Compare external frameworks when orchestration complexity rises, but migrate only when a concrete subsystem clearly outgrows Nora's custom implementation and the migration improves reliability, traceability, or maintainability.

## Architecture Layers

### 1. Durable Kernel

Owns durable task identity, lifecycle state, checkpoints, artifacts, and recovery metadata.

Responsibilities:

- Create, update, pause, resume, cancel, retry, complete, and inspect durable tasks.
- Persist task state and step state.
- Link tasks to workers, traces, checkpoints, reviews, artifacts, and events.
- Preserve enough metadata for replay and handoff.

Core objects:

- `Task`
- `TaskStep`
- `Checkpoint`
- `Artifact`
- `RecoveryPlan`
- `DurableEvent`

PM guidance:

- Durable task features must include focused tests and deterministic evals.
- Do not add task behavior that exists only in chat memory.
- Every serious action should leave durable evidence.

### 2. Scheduler

Turns durable primitives into an active runtime. It decides what should happen next and why.

Responsibilities:

- Scan pending tasks, idle workers, active leases, ready closeout candidates, stale workers, blocked tasks, and retryable failures.
- Plan actions before executing them.
- Default to dry-run for new automation.
- Execute only policy-approved safe actions.
- Record scheduler decisions as durable events.
- Explain why a task was dispatched, skipped, blocked, retried, or finalized.

Core objects:

- `SchedulerTick`
- `SchedulerPlan`
- `SchedulerAction`
- `SchedulerDecision`
- `BlockedReason`
- `RetryPolicy`

PM guidance:

- Scheduler tasks should start read-only or dry-run.
- Execution tasks should be narrow and guarded.
- Every scheduler action needs a reason label and no-leak output.
- Add evals for no mutation, blocked reason labels, retry/backoff, and compatibility.

### 3. Worker Runtime

Runs specialized agents in isolated, auditable workspaces.

Responsibilities:

- Register workers and track heartbeat/offline status.
- Claim or receive tasks.
- Bind worker, task, and workspace through leases.
- Restrict reads/writes to the worker workspace.
- Export safe summaries and patches.
- Require review gates before merge/apply/finalize.
- Release or preserve leases according to policy.

Core objects:

- `Worker`
- `WorkerRole`
- `WorkspaceLease`
- `WorkspaceChangeSummary`
- `PatchExport`
- `MergeApply`
- `FinalizeResult`

PM guidance:

- Worker tasks must not write directly to project root unless explicitly in a merge/apply step.
- Workspace tools must reject traversal, absolute escape, symlink escape, sensitive paths, secrets, raw shell output, and raw task goals.
- Worker integration should remain incremental: inspect, write, summarize, review, dry-run, apply, finalize.

### 4. Policy Hook Kernel

Centralizes runtime safety. Prompt instructions are not enough.

Responsibilities:

- Evaluate lifecycle hooks before and after risky operations.
- Return `allow`, `confirm`, or `block` decisions.
- Support personal confirmations and enterprise policy rules.
- Record policy hook events.
- Keep policy outputs bounded and safe.

Required hook points:

- `pre_tool`
- `post_tool`
- `pre_edit`
- `post_edit`
- `pre_shell`
- `pre_git`
- `pre_plugin_call`
- `post_test`
- `before_handoff`
- `before_commit`
- `before_merge_apply`
- `compact`
- `stop`
- `recovery`

Core objects:

- `PolicyHook`
- `PolicyRule`
- `PolicyDecision`
- `ApprovalRequest`
- `ApprovalDecision`
- `RiskCategory`

PM guidance:

- Any new high-risk action should route through policy hooks.
- Enterprise-ready features should use the same hook kernel rather than separate ad hoc checks.
- Policy evals must cover allow, confirm, block, unsupported hook, bad category/risk, no-leak, read-only/no-mutation, and event query behavior.

### 5. Trace Graph

Turns events into inspectable execution structure.

Responsibilities:

- Link task, worker, model, tool, plugin, policy, review, test, handoff, and recovery activity.
- Represent spans rather than only flat logs.
- Support "why did this happen?" and "where can this resume?" queries.
- Feed the Agent OS dashboard and eval summaries.

Core objects:

- `Trace`
- `TraceSpan`
- `SpanLink`
- `ModelSpan`
- `ToolSpan`
- `PluginSpan`
- `PolicySpan`
- `ReviewSpan`
- `TestSpan`
- `RecoverySpan`

PM guidance:

- New runtime actions should emit traceable events with task/worker/session linkage when applicable.
- Do not store raw prompts, raw secrets, raw diffs, raw shell output, or sensitive payloads in trace metadata.
- Prefer safe metadata and artifact references.

### 6. Tool And Plugin Broker

Provides governed access to local tools, MCP tools, and industry plugins.

Responsibilities:

- Register local tools with permission metadata.
- Load plugin manifests without executing plugin code during inspection.
- Map plugin actions to permission categories and policy hooks.
- Bound and sanitize outputs.
- Record plugin calls in durable events/traces.

Plugin manifest must declare:

- `name`
- `version`
- `domain`
- `capabilities`
- `tools`
- `auth`
- `permissions`
- `data_sensitivity`
- `requires_confirmation`
- `event_logging`
- `output_bounding`

Core objects:

- `ToolDefinition`
- `PluginManifest`
- `PluginTool`
- `PluginAuth`
- `PluginPermission`
- `DataSensitivity`
- `PluginCall`

PM guidance:

- Build manifest inspection and routing before real API execution.
- Real connectors should start with read-only actions.
- High-risk industry plugins require confirmation and stronger event logging before write actions.
- Avoid broad plugin integrations before manifest, permission, trace, and eval foundations are stable.

### 7. Skill And Capability Router

Selects professional skills, plugins, risks, and deliverables for a user goal.

Responsibilities:

- Inspect and summarize skill manifests.
- Discover local skill manifests safely.
- Preview skill context without loading or executing skill content.
- Combine skill and plugin metadata into a capability plan.
- Feed scoped skill context into the context compiler.

Skill manifest should declare:

- `name`
- `version`
- `domain`
- `capabilities`
- `workflows`
- `deliverables`
- `required_plugins`
- `risk_boundaries`
- `evals`

Core objects:

- `SkillManifest`
- `SkillCatalog`
- `SkillContextPreview`
- `CapabilityRequest`
- `CapabilityPlan`
- `RiskBoundary`
- `DeliverableSpec`

PM guidance:

- Skill packs describe how domain work should be done; plugins perform governed external actions.
- Do not hard-code all industry knowledge into one system prompt.
- Skill context must be scoped, bounded, marked untrusted when user/project supplied, and deterministic.
- High-risk domains such as legal, healthcare, investment, tax, and regulated finance need source tracking, disclaimers, human confirmation, and policy gates.

### 8. Context Compiler

Builds task-specific context packs.

Responsibilities:

- Compile scoped context from repository files, symbols, diffs, tests, docs, previous traces, durable task state, worker state, skill previews, plugin capability metadata, project decisions, and memory records.
- Keep RAG auxiliary, not the main code understanding path.
- Make context packs inspectable and reproducible.
- Avoid dumping broad hidden memory.

Core objects:

- `ContextPack`
- `ContextSource`
- `ContextBudget`
- `KnowledgeExcerpt`
- `SymbolContext`
- `SkillContextSection`
- `PluginContextSection`

PM guidance:

- Context compiler changes must include safety/bounding tests.
- Prefer agentic search, AST/symbol indexing, import/call relationships, diffs, tests, and trace memory over vector-only code RAG.
- Context sections should be labeled and deterministic.

### 9. Model Router

Chooses models by task need and records why.

Responsibilities:

- Select models by task type, risk, cost, latency, context length, tool-calling quality, review quality, and reliability.
- Support separate policies for routing, implementation, review, long-context, and high-risk reasoning.
- Record model decisions and outcomes.

Core objects:

- `ModelPolicy`
- `ModelDecision`
- `ModelCapability`
- `ModelCostRecord`
- `ModelOutcome`

PM guidance:

- Start with a minimal router that explains decisions; do not overbuild provider orchestration.
- Every router decision should be traceable.
- Evals should compare outcomes before changing defaults.

### 10. Eval And Review System

Keeps the runtime honest.

Responsibilities:

- Provide deterministic offline evals for tools, manifests, policies, scheduling, context, workers, and traces.
- Add end-to-end workflow evals for durable task execution.
- Enforce PM/reviewer gates before integration.
- Track pass rate, tool count, time, model cost, token use, edit count, test count, review findings, recovery quality, and accidental mutation count.

Core objects:

- `EvalCase`
- `WorkflowEval`
- `ReviewGate`
- `ReviewFinding`
- `QualityMetric`

PM guidance:

- Each runtime feature should have a paired eval task unless the feature is doc-only.
- New automation must prove no mutation in dry-run.
- End-to-end evals should cover create task, dispatch worker, isolated workspace write, review gate, dry-run merge, apply, finalize, and injected failure recovery.

### 11. Agent OS Dashboard

Makes the runtime visible and operable.

Responsibilities:

- Show task queue and task state.
- Show worker pool, heartbeat, status, assignments, and workspace leases.
- Show scheduler decisions and blocked reasons.
- Show trace timeline/graph.
- Show approvals, review gates, diffs, patches, tests, checkpoints, recovery plans, plugin permissions, enabled skills, and model/cost status.

Core objects:

- `DashboardViewModel`
- `TaskPanel`
- `WorkerPanel`
- `TracePanel`
- `PolicyPanel`
- `PluginPanel`
- `SkillPanel`
- `ModelPanel`

PM guidance:

- UI tasks should expose runtime state, not just chat.
- Frontend views should be backed by deterministic, bounded API surfaces.
- The dashboard should answer: what is running, what is blocked, what changed, what was approved, what failed, and how to resume.

## Canonical Workflow

```text
User goal
  -> Capability Router
     -> selected skills
     -> selected plugins
     -> risk level
     -> deliverable spec
  -> Durable Task
  -> Context Compiler
  -> Scheduler
  -> Worker Runtime
  -> Policy Hooks around every risky action
  -> Tool/Plugin Broker
  -> Trace Graph records every significant span
  -> Review Gate
  -> Merge/Apply/Finalize
  -> Recovery/Handoff artifacts
  -> Dashboard visibility
```

## PM Task Generation Contract

When Codex PM generates a task, it must include:

- Architecture layer: one or more layers from this document.
- Objective: one concrete behavior or interface.
- Non-goals: what must not be implemented in this task.
- Safety boundaries: no-leak, no-mutation, path safety, policy hooks, or confirmation requirements.
- Durable evidence: what event, trace, artifact, or state should be written or queried.
- Verification: focused unittest, deterministic eval, `git diff --check`, and full suite when the blast radius is broad.
- References: relevant files and architecture sections.

Task wording should prefer narrow vertical slices:

```markdown
### TASK-XXX: [Layer] narrow behavior v1
- Architecture layer: Scheduler / Policy Hook Kernel / ...
- Goal: ...
- Non-goals: ...
- Safety: ...
- Durable evidence: ...
- Verification: ...
- References: docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md#[section], files...
```

## Continuous Framework Optimization

Nora's framework architecture is a living contract. It should be optimized continuously as implementation evidence, eval results, user feedback, and frontier agent platform signals arrive.

Optimization triggers:

- A completed task reveals a repeated pattern, missing abstraction, unclear module boundary, or unsafe workflow.
- Review findings recur across multiple tasks.
- Deterministic evals expose weak safety, recovery, traceability, routing, or context behavior.
- Daily radar finds a high-signal change in Codex, Claude Code, OpenAI Agents SDK, MCP, or relevant research.
- A user-facing workflow becomes hard to explain, inspect, recover, or test.
- A subsystem starts duplicating logic across registry tools, runtime modules, CLI, UI, or evals.

Optimization rules:

- Update this document when the framework shape, module boundary, core object, task contract, or review checklist changes.
- Update `docs/knowledge/DECISIONS.md` when the change is a durable architecture decision.
- Update `docs/knowledge/PROJECT_WAKEUP.md` when new windows or PM loops must inherit the change immediately.
- Update `agent_tasks/DAILY_AI_AGENT_RADAR.md` when the change came from external information gathering.
- Prefer small architecture amendments over broad rewrites.
- Do not use architecture optimization as a reason to interrupt active worker implementation unless the active work violates safety, durability, or scope boundaries.
- Convert architecture changes into PM candidate tasks only after identifying the architecture layer, non-goals, safety boundaries, durable evidence, and verification path.

Every architecture optimization should answer:

- What signal triggered the update?
- Which architecture layer is affected?
- What design rule or module boundary changes?
- What should PMs do differently when generating tasks?
- What should reviewers check differently?
- What eval or runtime evidence would prove the change works?

## Integration Rules

- Start read-only.
- Add deterministic evals.
- Add guarded write behavior only after read-only behavior passes review.
- Keep outputs bounded.
- Never leak secrets, raw prompts, raw diffs, raw shell output, hidden reasoning, raw plugin payloads, or private credentials.
- Do not mutate project root from worker tools except through approved merge/apply flows.
- Prefer explicit state and artifacts over hidden chat memory.
- Prefer stable structured JSON for internal surfaces and readable plain text for user-facing CLI.
- Avoid framework migrations unless there is a clear subsystem-level reason and an exit plan.

## Near-Term Architecture Roadmap

1. Finish current CLI UX work without disrupting runtime foundations.
2. Promote guarded scheduler tick into a policy-backed scheduler loop.
3. Add retry/backoff and blocked-reason explanations to scheduler decisions.
4. Consolidate policy hook APIs and apply them to shell, Git, edits, plugin calls, model calls, tests, handoffs, and commits.
5. Define `TraceSpan` and trace graph query surfaces over existing durable events.
6. Add end-to-end workflow evals across task -> worker -> workspace -> review -> merge -> finalize -> recovery.
7. Extend plugin manifest runtime from inspection/routing into safe read-only connector execution.
8. Extend skill manifests into installable local skill packs with versioning and eval metadata.
9. Add minimal model router with traceable model decisions.
10. Build Agent OS dashboard views over task, worker, scheduler, trace, policy, skill, plugin, review, and model state.

## Architecture Review Checklist

Reviewers should ask:

- Does this change fit a named architecture layer?
- Does it preserve local-first durable runtime ownership?
- Does it create durable evidence for important actions?
- Does it route risky behavior through permission or policy hooks?
- Does it keep worker changes isolated?
- Does it avoid leaking secrets, raw prompts, raw diffs, raw shell output, or raw plugin payloads?
- Is output bounded and deterministic where needed?
- Is there focused unittest coverage?
- Is there deterministic eval coverage for behavior and safety?
- Does the UI/CLI expose runtime state clearly if the change is user-facing?
- Does the task avoid premature broad refactors or framework migration?
