# Nora Agent OS / Durable Runtime North Star

Last updated: 2026-06-01

## Positioning

Nora is not just a chatbot, RAG app, or coding assistant UI. Nora should become a local-first Agent OS / Durable Runtime: an execution environment where AI agents can run real work with persistent state, explicit permissions, replayable traces, worker isolation, review gates, and recovery from interruption.

Claude Code and Codex are the benchmark for coding execution quality. Nora's way to surpass them is to become a broader durable runtime that can host coding agents, research agents, browser agents, file agents, voice agents, and workflow agents under one auditable local operating layer.

Nora should also become a professional agent platform for personal and enterprise users across industries. The long-term shape is:

```text
Nora = Agent OS Core + Skill Packs + Plugin Runtime + Capability Router
```

- Agent OS Core provides durable tasks, event logs, permissions, workers, context compilation, model routing, review gates, and replay.
- Skill Packs provide industry and professional knowledge: terminology, workflows, templates, risk boundaries, and quality checks.
- Plugin Runtime provides governed access to external systems and APIs used by each industry.
- Capability Router selects the right skills and plugins for a user goal, then runs them through the durable runtime with trace and permission controls.

## Core Architecture

The durable runtime should be organized around these kernel services:

- Task scheduler: creates, queues, pauses, resumes, cancels, and retries agent tasks.
- Event log: records every user request, model call, tool call, file edit, command, approval, test, review, error, and handoff.
- State store: persists task state, step state, worker state, artifacts, checkpoints, and summaries.
- Permission manager: applies policy before high-risk tools, filesystem writes, shell commands, network calls, browser actions, and Git actions.
- Tool broker: exposes local tools, MCP tools, browser tools, filesystem tools, shell tools, and future plugins through one governed interface.
- Context compiler: builds task-specific context packs from files, symbols, tests, diffs, traces, decisions, and user memory.
- Model router: selects models by task type, cost, latency, context length, reliability, and tool-calling quality.
- Skill registry: installs, enables, disables, versions, and evaluates professional skill packs.
- Plugin runtime: loads external connectors with manifests, auth, permission mapping, data sensitivity labels, and event logging.
- Capability router: maps user goals to skill packs, plugins, tools, risk levels, and expected deliverables.
- Worker runtime: runs planner, implementer, reviewer, tester, researcher, and UI agents in isolated workspaces.
- Review gate: blocks merge, commit, push, destructive commands, or high-risk actions until tests and review criteria pass.
- Replay and recovery engine: reconstructs what happened and resumes from checkpoints after crashes, window loss, or model failure.

## Skill Packs And Plugins

Industry support should be embedded in Nora as a system capability, but specific industry knowledge should stay modular. Do not hard-code every industry into one large prompt. Build a skill and plugin ecosystem that can be installed, inspected, tested, upgraded, and governed.

Skill Packs answer "how should this work be done?"

- Industry terminology and domain language.
- Standard workflows and task decomposition.
- Templates for reports, emails, plans, forms, spreadsheets, and review checklists.
- Risk boundaries and "must ask the user" rules.
- Evaluation cases that prove the skill behaves reliably.

Plugins answer "what external system can Nora operate?"

- Developer tools: GitHub, GitLab, Sentry, Linear, Jira, Vercel, Netlify, Figma.
- Productivity tools: Google Drive, Gmail, Calendar, Notion, Slack, Sheets.
- Industry tools: Shopify, Stripe, QuickBooks, Xero, Salesforce, HubSpot, CMS systems, inventory systems, contract databases, learning platforms, market data providers, and other vertical systems.

Every plugin manifest should declare:

- Tool names and descriptions.
- Auth method such as OAuth, API key, local token, or enterprise connector.
- Permission category for each action: read, write, destructive, financial, external-send, or high-risk.
- Data sensitivity such as customer PII, payment data, health data, legal data, source code, or secrets.
- Confirmation requirements for high-risk actions such as refunds, bulk updates, production changes, external messages, Git pushes, or legal/financial submissions.
- Event-log behavior and output bounding so raw sensitive payloads are not persisted unnecessarily.

Personal use and enterprise use should share the same core, but emphasize different product surfaces:

- Personal Nora: local-first professional workbench for developers, founders, researchers, creators, operators, and consultants. Optimize for low setup friction, strong memory, private local data, resumable tasks, personal workflows, and useful deliverables.
- Enterprise Nora: governed agent runtime platform for teams. Optimize for RBAC, SSO, audit logs, policy controls, isolated worker pools, internal connectors, approval workflows, cost metrics, task reliability, and compliance.

The first skill packs should stay close to Nora's current strengths:

1. Software engineering.
2. Product and project management.
3. Research and consulting.
4. Spreadsheet, finance, and operations analysis.
5. Content creation and publishing.

Higher-risk skills such as legal, healthcare, investment, tax, and regulated finance require stronger source tracking, disclaimers, human confirmation, and policy gates before any external or irreversible action.

## Durable Task Lifecycle

Every serious task should move through an explicit lifecycle:

1. Intake: capture user goal, constraints, repository state, and acceptance criteria.
2. Plan: generate a task plan with risk level, required tools, and expected artifacts.
3. Context pack: compile scoped context instead of relying on broad hidden chat history.
4. Execute: run model/tool/edit/test loops with event logging.
5. Checkpoint: persist state after meaningful steps.
6. Review: run automated checks and agent review gates.
7. Handoff: write durable artifacts for another window or worker.
8. Complete: store final result, tests, changed files, decisions, and next tasks.
9. Replay: allow a future agent to inspect or resume the task from trace and checkpoints.

## What To Build Next

Priority 1: Durable trace schema

- Define model_call, tool_call, file_edit, shell_command, test_run, approval, review, checkpoint, and handoff event types.
- Store events in a queryable local database.
- Link events to task_id, session_id, worker_id, repo state, and artifact paths.

Priority 2: Durable task state

- Replace ad hoc session memory with resumable task records.
- Add pause/resume/cancel semantics.
- Store task checkpoints and current step state.

Priority 3: Context compiler

- Build context packs from repository files, symbol search, diffs, tests, docs, previous traces, and knowledge files.
- Make context packs inspectable and reproducible.
- Keep RAG as one optional input, not the main brain.

Priority 4: Worker isolation

- Run workers in separate worktrees or patch queues.
- Require DONE reports and trace links.
- Add review gates before integration.

Priority 5: Eval harness

- Measure real tasks: fix bug, add API, update UI, run tests, recover from interruption, coordinate two workers.
- Track pass rate, tool count, time, cost, number of corrections, and recovery quality.

Priority 6: Skill pack runtime

- Add a skill manifest format with name, domain, capabilities, required tools, risk boundaries, templates, and evals.
- Add a skill registry that can install, list, enable, disable, version, and inspect skill packs.
- Extend the context compiler so skills contribute scoped terminology, workflows, templates, and safety rules without dumping full skill contents.
- Add deterministic evals for skill routing, skill context inclusion, safety boundaries, and deliverable shape.

Priority 7: Plugin runtime and capability routing

- Add plugin manifests with auth, permissions, tool schemas, data sensitivity, confirmation rules, and event-log metadata.
- Map plugin actions into the existing permission manager and durable event log.
- Build a capability router that selects skill packs and plugins based on user goals, available integrations, risk level, and expected output.
- Start with developer and productivity plugins before high-risk industry plugins.

## Design Rules

- Hidden chat memory is not durable memory.
- Tool output is not useful unless it becomes an event, artifact, or decision.
- A task is not complete until it can be explained, replayed, and handed off.
- Context should be compiled for the task, not dumped wholesale.
- RAG is auxiliary. Trace, state, code structure, tests, and review artifacts are primary.
- Industry support belongs in skill packs and plugins, not in one monolithic system prompt.
- Skills describe domain work; plugins perform governed external actions.
- High-risk industry actions must be permissioned, auditable, and easy to stop.
- Safety is a runtime property, not just a prompt instruction.
- UI should show task state, trace, approvals, diffs, tests, and recovery points, not just messages.

## Benchmark

Nora should be compared against Claude Code and Codex on:

- Correctness on real repository tasks.
- Recovery after a lost window or interrupted run.
- Multi-agent coordination quality.
- Trace clarity and auditability.
- Permission safety.
- Context relevance.
- Test and review discipline.
- Speed and cost.
- Ability to integrate non-code tools through MCP/plugins without losing control.
