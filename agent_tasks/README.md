# Nora Agent Task Board

Codex is the reviewer and project manager. Task publication is owned by the dedicated Codex PM thread. Claude A and Claude B should read their own task files, implement only the assigned scope, then write a completion report to the matching `DONE` file.

Rules:
- Do not push.
- Do not commit unless Codex explicitly asks.
- Only the dedicated Codex PM thread may publish tasks, edit worker task files, or assign Claude A/B. Other Codex or automation threads may only propose candidate tasks or review inputs for PM to decide.
- Keep changes scoped to the assigned files and feature.
- Do not edit `CODEX_TERMINAL_HANDOFF.md` or `designs/`.
- Before reporting done, include `git diff --stat`, tests run, and any files intentionally left uncommitted.

Workflow:
1. Claude A reads `A_TASK.md`.
2. Claude B reads `B_TASK.md`.
3. When done, Claude A writes `A_DONE.md`.
4. When done, Claude B writes `B_DONE.md`.
5. Notify Codex PM:
   - Claude A runs `agent_tasks/notify_codex.sh A`
   - Claude B runs `agent_tasks/notify_codex.sh B`
6. Codex reviews the repo, `PM_INBOX.md`, and the matching `DONE` file directly.
