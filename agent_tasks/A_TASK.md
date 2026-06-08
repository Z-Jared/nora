# TASK-161: Token food economy estimate and transparent spend loop

You are Claude A. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-a` only. Do not commit or push.

## Context

Nora is now a customizable electronic pet agent. TASK-159/160 made the default example pet `Nora-01`, a robot electronic pet, and the Pet Room already shows Compute Food / Token Energy. The next product step is to make token food feel like a real transparent compute-energy loop rather than only a demo add/feed button.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `mini_agent/pets.py`
- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py`
- `tests/test_webui_smoke.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/A_DONE.md`.

## Goal

Build a deterministic Token Food Economy MVP around transparent cost estimate, balance, and insufficient-balance explanation.

Required behavior:

1. HTTP/API:
   - Add a read-only endpoint for pet food/compute status or estimate, for example `GET /pet/food-status?pet_id=...&action=chat|voice|work|feed`.
   - The response should include current balance, estimated cost, whether the action can run, short reason label, and safe user-facing copy.
   - Estimate must be deterministic and bounded. Suggested MVP costs: feed=100, chat=25, voice=80, work=150. Pick a small clear policy and document it in code/docs.
   - Balance insufficient responses must not mutate state.
   - Existing `/pet/feed` behavior should keep no-negative balance and clear insufficient-compute-food behavior.
   - Add concise docs entry to `/docs`.

2. Pet Room UI:
   - Show transparent balance and estimated costs for feed/chat/voice/work in the Pet Room.
   - Show a non-manipulative insufficient-balance explanation when feed/work cannot run.
   - Keep "Add Demo Tokens/Food" local-only framing; do not create a purchase flow.
   - Avoid pet suffering, threat, urgency, hidden-cost, or emotional blackmail language.

3. Runtime/product boundary:
   - This is not real billing. It is the local deterministic contract for future commercial food/token economy.
   - Model output must not control balance, estimates, or payment state.

## Non-Goals

- No real payment provider.
- No subscription/membership.
- No checkout/recharge page.
- No actual OpenAI/Anthropic/Gemini usage accounting.
- No LLM calls.
- No voice implementation.
- No marketplace.

## Safety Boundaries

- State mutations must continue to go through `PetStore`.
- New estimate/status endpoint must be read-only.
- Mutation endpoints must retain existing HTTP auth behavior when `NORA_API_TOKEN` is set.
- No secret-like text should be stored or rendered.
- Do not touch unrelated CLI/TUI code.

## Scope

Primary files:

- `mini_agent/http_server.py`
- `mini_agent/static/index.html`
- `tests/test_http_server.py` only for focused implementation-adjacent coverage
- `tests/test_webui_smoke.py` only for focused implementation-adjacent coverage
- `agent_tasks/A_DONE.md`

Do not edit:

- `agent_tasks/B_TASK.md`
- `agent_tasks/B_DONE.md`
- `CODEX_TERMINAL_HANDOFF.md`
- `designs/`
- `assets/`

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

If full evals fail because of pre-existing unrelated state, report the exact failure and still run the targeted API/UI tests.

## Completion Report

Write `agent_tasks/A_DONE.md` using the AGENTS.md completion report format. Include exact commands/results, known issues, and whether TASK-162 needs to adjust tests for your public contract.

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh A
```
