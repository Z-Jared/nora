# Nora Codex Collaboration Rules

Codex is the project manager, reviewer, and committer for this repository. Codex windows are implementation workers.

## Worker Identity

At the start of a Codex window, identify yourself as either:

- Codex A
- Codex B

Then follow only the matching task file:

- Codex A reads `agent_tasks/A_TASK.md`
- Codex B reads `agent_tasks/B_TASK.md`

## Task Flow

0. Read `docs/knowledge/PROJECT_WAKEUP.md`, `docs/knowledge/DECISIONS.md`, and `docs/knowledge/CHAT_INDEX.md` so you inherit the project context from prior windows.
1. Read your assigned task file.
2. Inspect the current git worktree before editing.
3. Implement only your assigned scope.
4. Run the required checks listed in your task file.
5. Write your completion report:
   - Codex A writes `agent_tasks/A_DONE.md`
   - Codex B writes `agent_tasks/B_DONE.md`
6. Notify Codex PM:
   - Codex A runs `agent_tasks/notify_codex.sh A`
   - Codex B runs `agent_tasks/notify_codex.sh B`
7. Do not push.
8. Do not commit unless Codex explicitly asks.

## Boundaries

- Do not edit the other worker's task or done file.
- Do not edit `CODEX_TERMINAL_HANDOFF.md`.
- Do not edit `designs/` unless explicitly assigned.
- Avoid broad refactors while another worker is active.
- If your task conflicts with uncommitted work from another worker, stop and write the conflict in your DONE file.

## Completion Report Format

Use this structure:

```markdown
# Codex A/B Completion Report

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
