# Task Backlog

PM 从这里读取待分配的任务。每个任务格式：

## 待分配

（空 — 当前无待分配任务）

## 进行中

（空 — 当前无进行中任务）

## 已完成

### TASK-014: Eval coverage for file-edit events ✅
- 完成者: Claude B 因 stale worktree 阻塞；Codex PM 接管并在主工作区完成
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 103 passed；`python3 -m unittest tests.test_durable_events tests.test_workspace tests.test_workspace_patch` 104 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 file-edit success、patch/multi-patch metadata、blocked/cancelled、OS error、event-store failure isolation；用 sentinel 和 forbidden payload key 断言确认 raw content、replacement text、patch/diff、reason、raw OS error 不进入 durable event payload 或 serialized records；无 runtime fallback/shim。

### TASK-013: Durable file-edit event logging ✅
- 完成者: Claude A；PM 整理并修复初审问题
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_workspace tests.test_workspace_patch` 104 tests OK；`python3 evals/run_evals.py` 98 passed；`python3 -m unittest discover -s tests` 1168 tests OK；`git diff --check` OK。
- 内容: `WorkspaceFiles` write/replace/apply patch/multi-patch 记录 file-edit started/finished/blocked/error durable events；payload 仅含 path(s)、operation、file_count、status、generic error label 和 byte metadata；不持久化 raw content、replacement text、patch/diff、reason、raw exception 或 secret；event-write failure isolation。

### TASK-012: Eval coverage for model-call events ✅
- 完成者: Claude B；PM 整理并修复 review 阻塞断言
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 98 passed；`python3 -m unittest tests.test_durable_events tests.test_mini_agent` 175 tests OK；`python3 -m unittest discover -s tests` 1155 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 model-call success、tool-call response、error、streaming、event-write failure isolation，并用 sentinel 断言确认 model events 不持久化 raw prompt、full messages、tool result content 或完整 tool schema。

### TASK-011: Durable model-call event logging ✅
- 完成者: Claude A；PM 已移植到 /Users/mac/Documents/agent
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_mini_agent` 175 tests OK；`python3 evals/run_evals.py` 93 passed；`git diff --check` OK
- 内容: MiniAgent LLM chat/stream/complete/autonomous paths 记录 model-call started/finished/error durable events；payload 仅包含安全元数据；event-write failure isolation；focused unittest 覆盖成功、tool-call、错误、streaming、broken/no event store、autonomous path。

### TASK-010: Eval coverage for tool-call events ✅
- 完成者: Claude B
- 验证: `python3 evals/run_evals.py` 93 passed；`python3 -m unittest tests.test_durable_events tests.test_mini_agent` 168 tests OK
- 工作树: .ccb/workspaces/claude-b；PM 已移植到 /Users/mac/Documents/agent
- 内容: 新增 4 个 deterministic offline eval，覆盖 tool-call success、error、permission blocked/cancelled、event write failure isolation。

### TASK-009: Durable tool-call event logging ✅
- 完成者: Claude A
- Reviewer: Claude B fallback review（reviewer pane 上游断流）
- 验证: `python3 -m unittest tests.test_durable_events tests.test_durable_tasks tests.test_traces tests.test_mini_agent` 341 tests OK；`python3 evals/run_evals.py` 89 passed；`python3 -m unittest discover -s tests` 1148 tests OK
- 工作树: .ccb/workspaces/claude-a (5 files, +730/-11)
- 内容: MiniAgent tool-call durable events；tool args/result preview 脱敏/截断；cancelled→blocked audit semantics；event-write failure isolation；trace/shadow regression fixes。

### TASK-003: Durable task CRUD API ✅
- 完成者: Claude A
- 验证: 1034 tests pass, CRUD tools 注册在 registry_builder.py, delete_task() 新增, wiring 完成
- 工作树: .ccb/workspaces/claude-a

### TASK-004: Task status dashboard CLI ✅
- 完成者: Claude B
- 验证: 1034 tests pass, 76 evals pass (+5 new), /dashboard 命令已添加
- 工作树: .ccb/workspaces/claude-b

### TASK-005: Task retry mechanism ✅
- 完成者: Claude A
- 验证: 1053 tests pass (+19), retry_count/max_retries 字段, retry_durable_task(), FAILED→PENDING 转换
- 工作树: .ccb/workspaces/claude-a (5 files, +727/-9)

### TASK-006: Eval coverage for CRUD tools ✅
- 完成者: Claude B
- 验证: 81 evals pass (+10 CRUD evals), 1014 tests pass
- 工作树: .ccb/workspaces/claude-b
- 注意: Claude B 也实现了部分 CRUD tools（与 Claude A 重复），合并时需要解决冲突

### TASK-007: Durable event log v1 ✅
- 完成者: Codex PM（从 Claude A stale worktree 候选实现中安全移植到当前 main）
- 验证: focused durable event/task/trace tests pass；89 evals pass
- 工作树: /Users/mac/Documents/agent
- 注意: Claude A/B CCB worktree 落后在 dc8f1cd 且有旧任务脏改动，未直接合并。

### TASK-008: Durable event log eval coverage ✅
- 完成者: Codex PM（Claude B 因等待 TASK-007 且 worktree stale 阻塞）
- 验证: `python3 evals/run_evals.py` 89 passed, 0 failed
- 工作树: /Users/mac/Documents/agent
