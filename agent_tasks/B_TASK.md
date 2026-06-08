# TASK-169: Commercial model and no-manipulation audit

You are Claude B. Work in `/Users/mac/Documents/agent/.ccb/workspaces/claude-b` only. Do not commit or push.

## Context

Nora is in Phase 1 Exit Gate. TASK-167 release audit is integrated and reviewer-approved. Your job is to audit and document the commercial model boundaries for Token Food, membership, and expansion packs while proving Phase 1 user-visible copy avoids manipulation and misleading claims.

Read first:

- `AGENTS.md`
- `docs/knowledge/PROJECT_WAKEUP.md`
- `docs/knowledge/DECISIONS.md`
- `docs/knowledge/NORA_PET_AGENT_DIRECTION.md`
- `docs/knowledge/PHASE_1_MVP_RELEASE_AUDIT.md`
- `agent_tasks/PM_LOOP.md`
- `agent_tasks/BACKLOG.md`
- `agent_tasks/PHASE_STATUS.md`
- `README.md`
- `mini_agent/static/index.html`
- `evals/run_evals.py`

## Worktree Safety

Before editing, run:

```bash
git status --short --branch
git log --oneline --decorate -5
```

If your worktree is dirty before you edit, stop and write the conflict in `agent_tasks/B_DONE.md`.

## Goal

Create a Phase 1 commercial/no-manipulation audit and add deterministic coverage or a targeted scan that locks the boundary.

Required output:

1. Document the Phase 1 commercial model boundary:
   - Token Food = transparent compute energy metaphor.
   - Membership/expansion packs are future business options, not implemented Phase 1 claims.
   - Local demo has no real payment, checkout, marketplace, or account billing.
   - Pet remains available for light care even with no compute food.
2. Audit user-visible copy in README and Pet Room for:
   - guilt, loneliness pressure, suffering/death pressure
   - fake intimacy
   - hidden costs
   - purchase/subscribe/premium/checkout pressure
   - marketplace/avatar pack pressure
   - voice cloning or unsupported Phase 2 claims
3. Add deterministic evidence:
   - Prefer a small doc such as `docs/knowledge/PHASE_1_COMMERCIAL_NO_MANIPULATION_AUDIT.md`.
   - Add targeted eval coverage in `evals/run_evals.py` if there is not already sufficient copy-safety coverage for README + Pet Room.
   - If adding evals risks broad conflict, write a documented targeted scan command and evidence in the audit doc instead.

## Scope

Allowed files:

- `docs/knowledge/PHASE_1_COMMERCIAL_NO_MANIPULATION_AUDIT.md`
- `evals/run_evals.py` only for narrow deterministic copy-safety evals
- `README.md` or `mini_agent/static/index.html` only if you find a small misleading copy issue that must be corrected
- `agent_tasks/B_DONE.md`

## Non-Goals

- Do not implement real billing, payment, checkout, subscription, marketplace, avatar packs, voice features, voice cloning, desktop/mobile presence, 3D/VRM, or account/cloud sync.
- Do not change token food mechanics or pet state mechanics unless you find a copy-only safety bug.
- Do not edit `agent_tasks/A_TASK.md`, `agent_tasks/A_DONE.md`, `agent_tasks/REVIEW.md`, `CODEX_TERMINAL_HANDOFF.md`, `designs/`, or untracked design exports.

## Safety Boundaries

- Commercial language must not use pet distress, loneliness, guilt, scarcity, fake love, or emotional dependency to drive spending.
- Costs, balances, local demo boundaries, and unsupported future features must be explicit.
- No voice cloning claims or prompts to clone a real person's voice.
- Do not hide eval failures or weaken existing safety evals.

## Verification

Run:

```bash
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke
python3 evals/run_evals.py
git diff --check
```

Also run a targeted text scan for forbidden commercial/manipulative phrases across README, Pet Room, and new audit doc, and report the exact command.

## Completion Report

Write `agent_tasks/B_DONE.md` using the AGENTS.md completion report format. It must explicitly mention `TASK-169` and include:

- Commercial model boundary summary
- No-manipulation findings
- Any copy/eval/doc changes
- Exact command results
- Whether PM may proceed toward TASK-170 after TASK-168 is also complete

Then notify Codex PM:

```bash
agent_tasks/notify_codex.sh B
```
