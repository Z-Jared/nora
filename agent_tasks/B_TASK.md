# TASK-138: Minimal model routing deterministic eval coverage

You are Codex B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Codex A owns TASK-137: a read-only minimal model routing inspection scaffold. You own deterministic offline eval coverage after TASK-137 is integrated by Codex PM.

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
- `agent_tasks/A_TASK.md`
- `mini_agent/model_router.py` if present
- `mini_agent/settings.py`
- `mini_agent/providers/factory.py`
- `mini_agent/toolkits/registry_builder.py`
- `evals/run_evals.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Add deterministic offline eval coverage for the minimal model routing scaffold.

Coverage requirements:

1. Default route
   - Configured OpenAI-compatible settings select the configured provider/model.
   - Output includes stable policy/version and reason labels.
   - Output does not leak the fake API key.

2. Provider support
   - Anthropic and Gemini settings produce safe selected provider/model metadata.
   - Unknown provider produces a bounded unsupported-provider result.
   - Missing API key produces a disabled/not-ready route rather than a crash.

3. Routing hints
   - Task type, risk level, context token, tool requirement, and review requirement hints are normalized or safely bounded.
   - High-risk/review/long-context hints add deterministic reason labels.
   - No raw prompt/task goal content is echoed.

4. Registry tool
   - `inspect_model_routing` is registered with `local/read` permission.
   - Calling it does not mutate durable tasks, workers, events, memory, files, or traces.
   - It does not call the network or build a live LLM client.

5. Compatibility
   - Existing provider factory behavior remains intact for `openai-compatible`, `anthropic`, and `gemini`.
   - Existing CLI/provider/config evals continue to pass.

## Scope

Primary files:
- `evals/run_evals.py`
- `agent_tasks/B_DONE.md`

Only touch tests/runtime files if a tiny import/helper fix is necessary after TASK-137 integration. If TASK-137 surface is not yet present in your worktree, do not implement it yourself. Instead write `agent_tasks/B_DONE.md` with `Status: blocked/waiting for TASK-137 integration` and list the exact missing surface.

Do not edit:
- `mini_agent/model_router.py` unless PM explicitly asks after TASK-137 integration.
- `mini_agent/toolkits/registry_builder.py` unless PM explicitly asks after TASK-137 integration.
- `agent_tasks/A_TASK.md`
- `agent_tasks/A_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`

## Coverage Quality Requirements

- No `or True`, tautological assertions, or broad substring-only pass conditions.
- Use tempdir-isolated roots and explicit env/settings objects where needed so local `.env` cannot affect evals.
- Assert exact or meaningfully specific substrings/fields.
- Assert secrets/API keys are not leaked.
- Do not call network, LLMs, external services, or CCB commands from evals.

## Required Verification

Run:

```bash
python3 evals/run_evals.py
python3 -m unittest tests.test_model_router tests.test_config tests.test_mini_agent
git diff --check
```

If TASK-137 is not integrated yet and required checks cannot pass without runtime implementation, stop and report that dependency clearly in `agent_tasks/B_DONE.md` rather than broadening your scope.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. Include exact commands/results and known issues.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
