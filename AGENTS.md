# Nora Multi-Agent Collaboration Rules

Codex is the project manager, reviewer, and committer for this repository. Claude Code windows are implementation workers.

## Roles

- Codex PM: plans, assigns, reviews, runs checks, commits, and pushes after approval.
- Codex Reviewer: performs read-only code review and writes `agent_tasks/REVIEW.md`.
- Claude A: implementation worker for `agent_tasks/A_TASK.md`.
- Claude B: implementation worker for `agent_tasks/B_TASK.md`.

Codex PM/Reviewer windows do not identify as A/B workers. Claude Code worker windows must identify as either:

- Claude A
- Claude B

Then follow only the matching task file:

- Claude A reads `agent_tasks/A_TASK.md`
- Claude B reads `agent_tasks/B_TASK.md`

## Task Flow

0. Read `docs/knowledge/PROJECT_WAKEUP.md`, `docs/knowledge/DECISIONS.md`, and `docs/knowledge/CHAT_INDEX.md` so you inherit the project context from prior windows.
1. Codex PM reads `agent_tasks/PM_LOOP.md` and `agent_tasks/BACKLOG.md`.
2. Claude workers read their assigned task file.
3. Inspect the current git worktree before editing.
4. Implement only the assigned scope.
5. Run the required checks listed in the task file.
6. Write a completion report:
   - Claude A writes `agent_tasks/A_DONE.md`
   - Claude B writes `agent_tasks/B_DONE.md`
7. Notify Codex PM:
   - Claude A runs `agent_tasks/notify_codex.sh A`
   - Claude B runs `agent_tasks/notify_codex.sh B`
8. Codex PM runs initial checks, sends approved candidates to Codex Reviewer, then decides integration.
9. Workers do not push or commit unless Codex explicitly asks.

## Boundaries

- Do not edit the other worker's task or done file.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/` unless explicitly assigned.
- Avoid broad refactors while another worker is active.
- If your task conflicts with uncommitted work from another worker, stop and write the conflict in your DONE file.

## Completion Report Format

Use this structure:

```markdown
# Claude A/B Completion Report

Status: ready for Codex review

## Summary

...

## Diff

```text
<git diff --stat output>
```

## Tests

```text
<exact commands and pass/fail results>
```

## Notes

- No push performed.
- Known issues: ...
```

## Git Safety

Never run destructive git commands such as:

- `git reset --hard`
- `git checkout -- .`
- `git clean -fd`
- `git push`
- force push commands

Codex owns final review, commit, and push decisions.
