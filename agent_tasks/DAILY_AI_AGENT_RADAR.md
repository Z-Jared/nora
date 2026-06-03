# Daily AI Agent Radar

Owner: Codex PM
Cadence: daily when the user asks for the radar, or automatically once a scheduler is added.

## Purpose

Keep Nora's development direction aligned with the current frontier of AI coding agents, especially Codex, Claude Code, MCP tooling, agent runtime design, and new research papers.

This is not a generic news digest. Every entry must answer: "What should Nora build, avoid, copy, or measure differently?"

## Primary Sources

- OpenAI Codex changelog and official Codex documentation.
- `openai/codex` GitHub releases and notable pull requests.
- Claude Code official changelog, release notes, docs, hooks, subagents, MCP, memory, plugins, and sandbox documentation.
- Anthropic news and engineering posts relevant to Claude Code or agentic coding.
- OpenAI Agents SDK documentation, tracing, handoffs, guardrails, tools, and model updates.
- MCP specification and ecosystem changes.
- Research papers from arXiv, OpenReview, and major AI labs on software engineering agents, tool use, long-horizon planning, evals, context engineering, memory, and multi-agent systems.
- Practical field reports from reputable engineering blogs when they include reproducible details or clear product signals.

## Daily Output Format

```markdown
# AI Agent Radar - YYYY-MM-DD

## Executive Signal

- Direction change: yes/no
- Highest-impact item:
- Nora priority affected:

## Codex

- What changed:
- Why it matters:
- Nora action:

## Claude Code

- What changed:
- Why it matters:
- Nora action:

## Research

- Paper/title:
- Claim:
- Evidence strength:
- Nora action:

## Product/Architecture Implications

- Build now:
- Watch:
- Avoid:

## Task Proposals

- Claude A:
- Claude B:
- Codex PM/reviewer:
```

## Decision Rules

- Treat official docs, release notes, and source releases as high signal.
- Treat papers as directional until reproduced or backed by strong benchmarks.
- Treat social posts as weak signal unless they point to official artifacts, code, or measurable behavior.
- Do not chase every feature. Convert findings only into Nora priorities when they improve reliability, autonomy, safety, context quality, or multi-agent throughput.
- Downgrade old-style vector RAG for code understanding unless evidence shows it beats agentic search and context compilation on real coding tasks.
- Prefer agentic search, structured project memory, trace logs, review gates, worker isolation, and evals as the core coding-agent direction.

## Nora Strategic Bias

Nora should aim to beat Claude Code and Codex in focused areas before attempting broad parity:

- Local-first project memory and trace continuity.
- PM-worker-reviewer multi-agent workflow.
- Safer Git and filesystem boundaries.
- Better task handoff, DONE report validation, and review gates.
- Transparent context compiler instead of opaque retrieval.
- Reproducible evals on this repository and real user tasks.

## Next Implementation Themes

1. Agent runtime trace: every model call, tool call, file edit, test, failure, retry, and review finding should be inspectable.
2. Context compiler: build task-specific context packs from files, diffs, tests, symbols, docs, and prior traces.
3. Worker isolation: run Claude A/B-style tasks in separate worktrees or patch queues before PM merge.
4. Hooks: lifecycle events for pre-tool, post-tool, pre-edit, post-edit, pre-test, post-test, stop, compact, and handoff.
5. Eval harness: fixed coding tasks with pass/fail, time, token, edit count, test count, and review findings.
6. MCP/plugin layer: external tool integrations without hard-coding every tool into Nora core.

## 2026-06-03 Radar Update

Executive signal:

- Direction change: no; this reinforces the Agent OS / Durable Runtime direction.
- Highest-impact item: serious agent platforms are converging on traceability, hooks/guardrails, pluggable tools, isolated workers, and explicit context.
- Nora priority affected: turn durable worker primitives into a scheduler, add a policy hook kernel, make traces graph-shaped and UI-inspectable, and establish skill/plugin manifests before broad industry integrations.

Source signals:

- OpenAI Agents SDK emphasizes trace/spans, handoffs, guardrails, tools, sessions, and model/provider abstraction.
- Claude Code emphasizes hooks, subagents, tool permissions, plugins, MCP, memory files, and sandboxed execution behavior.
- MCP continues to formalize external tool/resource/prompt integration boundaries.
- Codex-style workflows reinforce multi-agent task execution, diff review, and controlled integration rather than chat-only interaction.

Nora actions:

- Build now: finish guarded worker lifecycle run-once, then promote it into a scheduler loop with dry-run defaults, safe execution, retry/backoff, durable decision events, and blocked-reason explanations.
- Build now: add a hook/policy kernel for pre/post tool, edit, shell, git, plugin call, test, handoff, compact, commit, and recovery lifecycle points.
- Build now: upgrade durable events into trace graphs/spans for task, worker, model, tool, plugin, approval, review, test, handoff, and recovery activity.
- Build now: add plugin manifest/runtime v1 before connecting many real industry APIs. Cover auth, tool schemas, permissions, data sensitivity, confirmation rules, output bounding, and event-log behavior.
- Build now: add skill manifest/runtime v1 and connect it to the context compiler so skills contribute scoped terminology, workflows, templates, deliverable formats, and safety rules.
- Build now: add capability routing that chooses skills, plugins, model policy, risk level, and expected deliverables from the user's goal.
- Build now: add end-to-end durable-runtime evals that exercise task creation, dispatch, isolated workspace writes, review gate, dry-run merge, apply, finalize, and injected failure recovery.
- Watch: compare LangChain, LangGraph, and OpenAI Agents SDK as references now that orchestration complexity is rising, but do not migrate by default.
- Avoid: broad industry plugin integrations before manifests, permission mapping, trace logging, and high-risk confirmation semantics are stable.

Task proposals:

- Claude A: scheduler loop v1 on top of worker lifecycle planner/run-once, default dry-run, durable decision events, and blocked reason labels.
- Claude B: deterministic evals for scheduler loop decisions, no mutation in dry-run, safe closeout-only execution, retry/backoff, blocked explanations, and compatibility with worker lifecycle tools.
- Codex PM/reviewer: design HookPolicyKernel v1 task pair after scheduler lands; verify all new automation remains bounded, explainable, and reversible.

## 2026-05-28 Radar Update

Executive signal:

- Direction change: no, but priority is sharper.
- Highest-impact item: tracing and explicit context management are now table stakes for serious coding agents.
- Nora priority affected: build trace spine and context compiler before adding more UI features.

Source signals:

- OpenAI Agents SDK documents built-in traces/spans for agent runs, LLM generations, tool calls, handoffs, guardrails, and custom events.
- OpenAI Agents SDK positions agents around tools, handoffs, guardrails, sessions, and traceability.
- Claude Code docs emphasize project/user subagents with isolated context windows and configurable tool access.
- Claude Code hooks cover PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, PreCompact, SessionStart, and SessionEnd.
- Claude Code memory docs continue to rely on project memory files such as `CLAUDE.md`, not opaque vector-only recall.

Nora actions:

- Claude A: implement first run trace vertical slice.
- Claude B: implement first context compiler vertical slice.
- Codex PM: review both for privacy, deterministic output, and testability before any merge.
