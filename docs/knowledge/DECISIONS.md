# Nora Development Decisions

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
