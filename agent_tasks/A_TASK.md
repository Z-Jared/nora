# TASK-137: Minimal model routing inspection scaffold v1

You are Codex A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora has OpenAI-compatible, Anthropic, and Gemini provider adapters, but no model router yet. The architecture contract says model routing should start as a minimal explainable layer before real provider orchestration.

Architecture layer:
- `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md` section 9, Model Router.
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 11, model routing.

Read first:
- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md`
- `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md`
- `docs/knowledge/CHAT_INDEX.md`
- `agent_tasks/BACKLOG.md`
- `mini_agent/settings.py`
- `mini_agent/providers/factory.py`
- `mini_agent/registry.py`
- `mini_agent/toolkits/registry_builder.py`
- relevant provider/tests files before editing

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Add a read-only, deterministic model routing inspection scaffold. This is the first small slice of a future model router. It must explain what model Nora would use and why, without changing actual model execution behavior.

Required behavior:

1. Core router module
   - Add a focused module, likely `mini_agent/model_router.py`.
   - Provide a pure function that accepts current `LLMSettings` plus optional routing hints such as:
     - `task_type`
     - `risk_level`
     - `context_tokens`
     - `requires_tools`
     - `requires_review`
   - Return safe structured metadata:
     - selected provider/model from current settings
     - route type/policy version
     - normalized task type and risk level
     - reason labels, not raw user prompts
     - capability hints for the selected provider/model
     - fallback availability as safe booleans/names only
     - warnings/errors for disabled or unsupported provider
   - Do not include API keys, raw prompts, raw task goals, environment values, hidden reasoning, or file contents.

2. Registry tool
   - Register a read-only tool such as `inspect_model_routing`.
   - Permission must be `ToolPermission(category="local", risk="read")`.
   - The tool must not call the network or create an LLM client.
   - The tool must not mutate durable tasks, workers, events, memory, files, or traces.
   - Output may be JSON, but it must be bounded and safe.

3. Provider compatibility
   - Keep `build_llm_client(...)` behavior unchanged.
   - Support current providers: `openai-compatible`, `anthropic`, `gemini`.
   - Unknown provider should return a safe unsupported-provider routing result instead of leaking config.
   - Disabled/missing API key should be represented as disabled/not ready, not as an exception.

4. Unit tests
   - Add focused unit tests for the router and registry tool.
   - Cover default configured route, missing API key, unsupported provider, task/risk/context hints, no secret leak, registry permission, and no mutation.

## Scope

Primary files:
- `mini_agent/model_router.py`
- `mini_agent/toolkits/registry_builder.py`
- `tests/test_model_router.py` or the most appropriate existing test file
- `agent_tasks/A_DONE.md`

Only touch provider files if needed for a tiny compatibility helper. Do not change live model call semantics.

Do not edit:
- `evals/run_evals.py` — Codex B owns TASK-138 eval coverage after TASK-137 is integrated.
- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Non-Goals

- No real automatic provider switching.
- No cost API, latency measurement, benchmarking, retry policy, or network calls.
- No trace/event recording yet.
- No UI changes.
- No prompt classification or hidden reasoning.
- No broad provider refactor.

## Safety Boundaries

- Never print API keys, tokens, `.env` values, private file contents, hidden reasoning, raw prompts, raw task goals, raw tool payloads, or raw shell output.
- Keep all output deterministic and bounded.
- Read-only tool means no durable event/task/worker/memory/file mutation.

## Durable Evidence

- Unit tests for router behavior and registry permission.
- Completion report in `agent_tasks/A_DONE.md`.
- No durable runtime event changes in this task.

## Required Verification

Run:

```bash
python3 -m unittest tests.test_model_router tests.test_config tests.test_mini_agent
python3 evals/run_evals.py
git diff --check
```

If you choose not to create `tests/test_model_router.py`, replace that command with the exact focused test module you used and explain why in `A_DONE.md`.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
