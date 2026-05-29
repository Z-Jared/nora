# Task Backlog

PM 从这里读取待分配的任务。每个任务格式：

## 待分配

（空 — 当前任务已派发）

## 进行中

### TASK-011: Durable model-call event logging
- 优先级: high
- 预计: 1-2 小时
- 依赖: 无
- 目标: 在 MiniAgent 的 LLM chat/stream/complete 路径记录 durable model-call lifecycle events。
- 验证: `python3 -m unittest tests.test_durable_events tests.test_mini_agent` 和 `python3 evals/run_evals.py` 通过。
- 参考: `mini_agent/controller.py` LLM call sites；`mini_agent/durable_events.py` event constants；`docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` Priority 1。

### TASK-012: Eval coverage for model-call events
- 优先级: high
- 预计: 1 小时
- 依赖: 等待 TASK-011
- 目标: 为 durable model-call event logging 增加 deterministic offline eval，覆盖成功、tool-call 响应、错误、streaming 和 event write failure isolation。
- 验证: `python3 evals/run_evals.py` 通过且新增 eval case；必要时补 focused unittest。
- 参考: `evals/run_evals.py` durable event/tool-call event eval 区域；TASK-011 新增行为。

## 已完成

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
