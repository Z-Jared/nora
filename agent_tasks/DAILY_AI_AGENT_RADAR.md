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
