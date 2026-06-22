# Nora Code TUI Frontend Contract

Last updated: 2026-06-20

## Scope

This contract defines the Nora Code terminal frontend line. It intentionally does not add backend capabilities. Backend threads may implement the data sources behind these surfaces later.

The reference set is:

- Claude Code-like restraint: minimal prompt, useful status, no noisy dashboard.
- MiMo Code-like wake surface: terminal-native entry, bottom input, mode/status hinting, slash command wake, optional right status rail.
- Nora-specific runtime: Goal Judge, Checkpoint, Review Gate, Workers, MCP, Model, Git, and Context surfaces.

Nora Code is the professional terminal product. It should not become the Pet Room UI, and it should not expose a heavy Agent OS dashboard by default.

## Product Positioning

Nora terminal has three layers:

```text
Nora Code
  = terminal-first coding agent UX
  + bottom input and slash wake
  + compact status
  + optional right rail

Nora Core
  = durable runtime behind the terminal
  + goal judge, checkpoint, model routing, tools, policy, workers, traces

Nora Agentic Pet
  = relationship/memory destination
  + task outcomes may become pet diary or relationship memory later
```

Rules:

- Terminal default is `Nora Code`, not Pet Room.
- Pet-related copy is allowed only when explicitly bridging task outcomes into relationship memory.
- The terminal must feel serious enough for engineering work.
- The UI must stay usable in `80x24`.

## Wake Contract

Primary commands:

```bash
nora
nora code
```

Both should enter the same Nora Code terminal workbench when stdout is a TTY.

Initial empty wake surface:

```text
                         NORA CODE

      输入任务...（输入 / 唤起命令）

      Code · Nora Auto
      tab 切换模式   ctrl+p 设置   @ 添加文件   / 命令   $ 子智能体
```

Rules:

- First paint is a terminal-native workbench, not a plain log transcript.
- The logo/brand area may be centered on an empty screen, but it must collapse after conversation starts.
- The input stays docked at the bottom.
- The wake surface must not print secret/model debug information.
- The default mode is `Code · Nora Auto`.
- If provider is not configured, the mode line should say `Code · local mode` without blocking local commands.

## Layout Contract

Nora Code TUI uses a stable vertical layout:

```text
header
body, scrollable, consumes all remaining height
right rail, optional and collapsible
overlay panel, optional: slash menu, approval, file picker, subagent picker, activity
bottom input, fixed
status hint, fixed
```

Rules:

- The bottom input must remain visually docked at the bottom during startup, typing, slash navigation, approvals, thinking/tool activity, and long output.
- The body is the only flexible region. Empty body space stays empty rather than pulling the input upward.
- Overlay panels render above the input and compress the body. They do not move below or replace the input.
- The status hint stays below the input and remains short.
- The right rail is visible only when width allows it, or when explicitly toggled.
- In `80x24`, the right rail is hidden by default and available through `/status` or `ctrl+p`.

## Startup Contract

Startup is an empty-state surface, not a restored-history transcript.

Rules:

- Nora identity, mode, model/provider state, and workspace summary stay visible on first paint.
- Restored session state appears as a compact notice only.
- Restored previous messages must not replace the startup surface.
- Full previous messages are loaded only after an explicit session-load flow.
- The wake surface may show "New session", context usage, workspace path, MCP, and LSP readiness in the right rail when width allows it.

## Bottom Input Contract

The bottom input is the primary interaction surface.

Required behaviors:

- Free text submits a coding/task request.
- `/` wakes command palette.
- `@` wakes file/context picker.
- `$` wakes subagent/worker picker.
- `tab` switches mode.
- `ctrl+p` opens settings/status.
- `esc` interrupts current run or closes the active panel.

Input placeholder:

```text
输入任务...（输入 / 唤起命令）
```

Mode line:

```text
Code · Nora Auto
```

Allowed modes for the first implementation:

- `Code · Nora Auto`
- `Plan · Nora Core`
- `Review · Nora Code`

Do not add a visible `Pet` mode to Nora Code until the Pet bridge has a concrete terminal workflow.

## Right Rail Contract

The right rail is a status surface, not a dashboard.

Suggested sections:

```text
Session
Context
Workspace
Model
Git
MCP
LSP
Workers
Goal
Checkpoint
```

Rules:

- The rail is read-only.
- It must not expose raw prompts, raw diffs, API keys, secrets, hidden reasoning, raw shell output, or raw tool payloads.
- It must degrade to `/status` text output on narrow terminals.
- It must stay compact: no nested cards, no tables, no scroll-heavy dashboard.
- MCP/LSP status may show pending/active/error, but not raw config secrets.

## Slash Panel Contract

Slash commands are a frontend command graph:

```text
SlashCommandNode:
  id
  label
  meta
  children
  args
  backend_action
  enabled
```

Current implementation may map this graph onto existing command metadata. Backend-backed children can be added later without changing the layout contract.

Rules:

- `/` opens a panel above the input.
- Selecting a group updates the same panel; it never prints menu rows into chat history.
- Argument steps update the same panel and place the cursor at the editable placeholder.
- Truncated second-level panels keep navigation hints such as `Enter choose, Esc back`.
- `/` is the command wake path, not a normal chat message.

## File Picker Contract

`@` opens a file/context picker above the input.

Rules:

- It may list files from the current workspace.
- It must respect existing sensitive path exclusions.
- It inserts bounded references, not raw file dumps.
- It must not read large files until explicitly selected.
- It must not include `.env`, secrets, private keys, credentials, or ignored sensitive paths.

## Subagent Picker Contract

`$` opens a subagent/worker picker above the input.

Initial choices:

```text
$ plan
$ implement
$ review
$ test
```

Rules:

- `$` does not directly spawn uncontrolled workers in the first implementation.
- It creates an explicit intent routed through Nora Core policy/review boundaries.
- When CCB workers are available, the picker may show worker status, but no dispatch happens without a confirmed command.

## Approval Panel Contract

Tool approvals render as a selectable panel above the input.

```text
ApprovalRequest:
  tool
  permission
  action
  reason
  choices
  default_choice
```

Rules:

- Up/Down changes selection.
- Enter confirms.
- Esc/Ctrl-C denies.
- Session allow is scoped to the exact action, not the whole tool.
- The approval panel must fit in `80x24`.
- If content is too long, truncate safely and provide a detail command such as `/approval`.

## Activity Contract

Thinking and tool status are lightweight activity rows near the bottom, above the input when active.

```text
ActivityEvent:
  kind: thinking | tool_start | tool_done | error | done
  label
  detail
```

Rules:

- Model name, speed, API key, and debug fields are not printed per turn.
- Activity rows do not become persistent chat history unless they are meaningful final results.
- `esc interrupt` should be visible while a run is active.
- Tool activity should show safe labels such as `reading files`, `running tests`, `editing`, `reviewing`.
- Do not stream raw shell output into the status strip.

## Goal And Checkpoint Contract

Nora Code should expose MiMo-inspired long-task support through Nora Core primitives.

Visible concepts:

- `Goal`: what the agent is trying to complete.
- `Checkpoint`: compact durable progress memory.
- `Review`: whether the output is ready to trust.

Rules:

- Goal Judge is not part of the visual shell until the backend exists, but the UI must leave a right-rail slot for it.
- Checkpoint status may be `none`, `writing`, `saved`, or `stale`.
- Checkpoints must be summaries only, never raw prompts, raw diffs, or raw shell output.
- A completed coding task may later offer "save to pet memory" as an explicit bridge, not automatic emotional copy.

## Visual Style

The style should be dark, quiet, and terminal-native.

Allowed:

- ASCII/bitmap-like `NORA CODE` wake title.
- Thin vertical input rail.
- Muted gray status text.
- Sparse separators.
- Monospace typography.

Avoid:

- Full-screen dashboard cards.
- Neon cyberpunk styling.
- Pet Room art inside the terminal default screen.
- Large decorative gradients.
- Persistent huge logo after first user message.
- Dense tables in the main terminal.

## Frontend Acceptance Matrix

Run real TTY checks for:

- 80x24 empty startup: input is framed and bottom docked.
- 80x24 restored startup: Nora startup remains visible; restored state is one compact notice.
- 80x24 typing: input row does not move.
- 80x24 `/`: slash panel appears above input; input remains docked.
- 80x24 `@`: file picker appears above input; input remains docked; sensitive files excluded.
- 80x24 `$`: subagent picker appears above input; input remains docked; no auto-dispatch.
- 80x24 second-level slash: Up/Down/Enter continue selecting.
- 80x24 approval: selectable approval appears above input; input remains docked.
- 80x24 long output: body scrolls; input remains docked.
- 80x24 active run: `esc interrupt` visible and works.
- 100x32 right rail: session/context/workspace/MCP/LSP visible without overlapping body/input.
- 100x32 rail toggle: rail can hide and restore without losing input focus.
- Repeat critical checks at 100x32.

## Implementation Sequence

1. Wake screen and bottom input contract.
2. Mode/status strip and active-run interrupt hint.
3. Slash command palette polish.
4. `@` file picker.
5. `$` subagent picker.
6. Right rail.
7. Goal/checkpoint slots.
8. Pet memory bridge after task completion.
