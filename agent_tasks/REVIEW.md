# TASK-139/TASK-140 Review: CLI UI v2

Status: APPROVED

## Summary

TASK-139 and TASK-140 are approved as an integrated CLI UI v2 slice.

TASK-139 makes the default terminal surface lighter: the input prompt is now exactly `> `, the startup banner is compact, and the default status line shows only model, local-first, and command hint information. It avoids fullscreen TUI behavior, dashboard panels, and default intelligence/speed/routing controls.

TASK-140 updates deterministic eval coverage for the new surface. Claude B could not apply the eval patch because its CCB worktree did not include the PM-integrated TASK-139 runtime changes, so Codex PM completed the eval-only patch directly on main.

## Findings

No blocking issues found.

## Verification

```text
python3 evals/run_evals.py
560 passed, 0 failed

python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent
Ran 226 tests ... OK

git diff --check
clean
```

## Coverage

- Minimal prompt is exactly `> ` and does not repeat branch, workspace, provider, or model.
- Startup banner preserves `Nora 已启动`, `Workspace:`, `LLM:`, `API key`, `Tools:`, `/wake`, `/setup`, `/model`, and `/workers`.
- Disabled/no-settings banner uses `API key: not used`.
- Input status line contains `model:`, the selected model or disabled state, `local-first`, and `/ for commands`.
- Default status line does not expose intelligence, speed, routing, secrets, hidden reasoning, or raw payloads.
- Slash commands, blank input, and exit do not emit lifecycle noise.
- `/`, `/setup`, `/model`, `/workers`, `/wake`, and `/help` remain plain text/Markdown rather than raw JSON.

## Verdict

APPROVED. TASK-139 and TASK-140 are ready to commit together.
