# Nora Agent OS / Durable Runtime North Star

Last updated: 2026-05-29

## Positioning

Nora is not just a chatbot, RAG app, or coding assistant UI. Nora should become a local-first Agent OS / Durable Runtime: an execution environment where AI agents can run real work with persistent state, explicit permissions, replayable traces, worker isolation, review gates, and recovery from interruption.

Claude Code and Codex are the benchmark for coding execution quality. Nora's way to surpass them is to become a broader durable runtime that can host coding agents, research agents, browser agents, file agents, voice agents, and workflow agents under one auditable local operating layer.

## Core Architecture

The durable runtime should be organized around these kernel services:

- Task scheduler: creates, queues, pauses, resumes, cancels, and retries agent tasks.
- Event log: records every user request, model call, tool call, file edit, command, approval, test, review, error, and handoff.
- State store: persists task state, step state, worker state, artifacts, checkpoints, and summaries.
- Permission manager: applies policy before high-risk tools, filesystem writes, shell commands, network calls, browser actions, and Git actions.
- Tool broker: exposes local tools, MCP tools, browser tools, filesystem tools, shell tools, and future plugins through one governed interface.
- Context compiler: builds task-specific context packs from files, symbols, tests, diffs, traces, decisions, and user memory.
- Model router: selects models by task type, cost, latency, context length, reliability, and tool-calling quality.
- Worker runtime: runs planner, implementer, reviewer, tester, researcher, and UI agents in isolated workspaces.
- Review gate: blocks merge, commit, push, destructive commands, or high-risk actions until tests and review criteria pass.
- Replay and recovery engine: reconstructs what happened and resumes from checkpoints after crashes, window loss, or model failure.

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

## Design Rules

- Hidden chat memory is not durable memory.
- Tool output is not useful unless it becomes an event, artifact, or decision.
- A task is not complete until it can be explained, replayed, and handed off.
- Context should be compiled for the task, not dumped wholesale.
- RAG is auxiliary. Trace, state, code structure, tests, and review artifacts are primary.
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
