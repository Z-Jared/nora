# Task Backlog

PM 从这里读取待分配的任务。每个任务格式：

## 待分配

（空）

## 进行中

（空）

## 已完成

### TASK-033: Eval coverage for durable worker registry tools ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 147 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_durable_tasks tests.test_mini_agent` 427 tests OK；`python3 -m unittest discover -s tests` 1309 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 worker registry register/get/list/upsert、status/current_task_id 更新、未知 worker 和非法 status 错误、安全隔离，以及 broken event store 下 registry 工具行为不变。

### TASK-032: Durable worker heartbeat and offline lifecycle v1 ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 441 tests OK；`python3 evals/run_evals.py` 147 passed；`python3 -m unittest discover -s tests` 1309 tests OK；`git diff --check` OK。
- 内容: `DurableWorkerStore` 新增 stale worker 标记 offline 能力；registry 新增 `touch_worker` 和 `mark_stale_workers_offline`；offline 标记保留 `last_seen_at` 和 `current_task_id`，不改变 durable task ownership；新增 SQLite/JSONL 和 registry focused tests。

### TASK-031: Eval coverage for durable task worker assignment ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 143 passed；`python3 -m unittest tests.test_durable_events tests.test_durable_tasks tests.test_mini_agent` 402 tests OK；`python3 -m unittest discover -s tests` 1295 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 durable task worker assignment 的 create/assign/clear/list 基础行为、worker-linked task action events、`list_durable_events(worker_id=...)` 查询、sentinel goal/secret 不泄漏，以及 broken event store 下 assign/clear failure isolation。

### TASK-030: Durable worker registry v1 ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 427 tests OK；`python3 evals/run_evals.py` 143 passed；`python3 -m unittest discover -s tests` 1295 tests OK；`git diff --check` OK。
- 内容: 新增 `mini_agent.durable_workers`，提供 SQLite/JSONL durable worker store、`DurableWorker` 数据结构和 `idle/assigned/running/paused/offline` 状态；registry 新增 `register_worker`、`list_workers`、`get_worker`、`update_worker_status` 工具；空 worker id、未知 worker、非法 status 返回 JSON error；状态更新不会修改 durable task 本身。

### TASK-029: Eval coverage for durable task action events ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 139 passed；`python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 402 tests OK；`python3 -m unittest discover -s tests` 1270 tests OK；`git diff --check` OK。
- 内容: 新增 7 个 deterministic offline eval，覆盖 durable task action events 的 create/update/retry/delete、previous_status、registry query by task_id/event_type、source/severity 输出、payload 不暴露、sentinel goal/step/failure_reason/secret 不泄漏，以及 broken event store 下 create/update/retry/delete 行为不变。

### TASK-028: Durable task worker assignment metadata ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 402 tests OK；`python3 evals/run_evals.py` 139 passed；`python3 -m unittest discover -s tests` 1270 tests OK；`git diff --check` OK。
- 内容: `create_durable_task` 支持可选 `worker_id` 并规范化空白值；新增 `assign_durable_task` 工具用于设置/清除 worker ownership 且不改变任务状态；`list_durable_tasks` 摘要包含 `worker_id`；task action events 在任务有 owner 时写入 top-level `worker_id` 和安全 `worker_id_present` 元数据。

### TASK-027: Eval coverage for durable event query filters ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 132 passed；`python3 -m unittest tests.test_durable_events tests.test_mini_agent` 275 tests OK；`python3 -m unittest discover -s tests` 1255 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 SQLite/JSONL filter parity、registry wiring、source/severity 输出、payload 不输出、filter-before-limit、newest-first、task_id 组合过滤、空白过滤参数和 sentinel payload/secret 不泄漏。

### TASK-026: Durable task registry action events ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 387 tests OK；`python3 evals/run_evals.py` 132 passed；`python3 -m unittest discover -s tests` 1255 tests OK；`git diff --check` OK。
- 内容: `create_durable_task` 记录 `TASK_CREATED`，`update_durable_task` 记录带 `previous_status` 的 `TASK_STATUS_CHANGED`，`retry_durable_task` 记录 `TASK_RETRIED`，`delete_durable_task` 记录带 `operation="delete"` 的安全状态变更事件；payload 只含 operation/status/previous_status/step_count/retry_count/max_retries/failure_reason_present/deleted 等元数据，事件写入失败不影响工具行为。

### TASK-025: Durable event query filters ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_mini_agent` 262 tests OK；`python3 -m unittest tests.test_durable_events tests.test_task_runner tests.test_durable_tasks tests.test_mini_agent` 395 tests OK；`python3 evals/run_evals.py` 127 passed；`python3 -m unittest discover -s tests` 1242 tests OK；`git diff --check` OK。
- 内容: `DurableEventStore.list_events` 支持 event_type、source、severity、worker_id、trace_id、checkpoint_id 过滤，SQLite 和 JSONL 后端一致；过滤与 task_id/max_results 组合，结果保持 newest-first 且上限 500；`list_durable_events` 工具暴露新过滤参数并在摘要中返回 source/severity，同时仍不暴露 payload。

### TASK-024: Eval coverage for handoff events ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 127 passed；`python3 -m unittest tests.test_durable_events tests.test_task_runner tests.test_durable_tasks tests.test_mini_agent` 395 tests OK；`python3 -m unittest discover -s tests` 1242 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 handoff_created、handoff_accepted、serialized safety、broken/no event store failure isolation 和 registry wiring；用 goal、summary、step、note、secret sentinel 与 forbidden payload keys 断言 handoff events 不泄漏原始任务内容。

### TASK-023: Durable handoff event logging ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_task_runner tests.test_durable_tasks tests.test_mini_agent` 376 tests OK；`python3 evals/run_evals.py` 122 passed；`git diff --check` OK。
- 内容: `finish_task` 记录 handoff_created，`restore_task` 记录 handoff_accepted；payload 仅含 artifact_type、history_id、status、step_count、done_step_count、blocked_step_count、summary_present/restored_from_present 等安全元数据；不持久化 raw goal、summary、step、note、history JSON 或 secret-like values；focused tests 覆盖 finish、restore、serialized safety、broken/no event store、registry wiring 和返回文案兼容。

### TASK-022: Eval coverage for review-gate events ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 122 passed；`python3 -m unittest tests.test_durable_events tests.test_git_tools tests.test_cli` 170 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 review-gate no_diff、present diff、sensitive path blocked、Git error、event-store failure isolation；present diff eval 将 sentinel 写入 staged README 并断言不进入 serialized review-gate events；sensitive path 和 raw Git error sentinel 也覆盖不泄露；eval-only。

### TASK-021: Durable review-gate event logging ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_git_tools tests.test_cli` 160 tests OK；`python3 evals/run_evals.py` 117 passed；`python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent` 247 tests OK；`git diff --check` OK。
- 内容: `git_review_staged_diff` 记录 review-gate started/finished/blocked/error durable events；payload 仅含 gate_name、status、has_staged_diff、file_count、sensitive_path_count、max_chars、generic error_label 等安全元数据；不持久化 raw diff、file paths、Git command/stdout/stderr、sensitive path warning 或 raw error text；default registry wiring 完成；focused tests 覆盖 no diff、present diff、sensitive path blocked、broken/no event store、registry wiring、error branch 和 serialized safety。

### TASK-020: Eval coverage for approval events ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 117 passed；`python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent` 247 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 approval approved、denied、non-permissioned、failure isolation；approved/failure-isolation 路径使用真实 permissioned `git_commit_staged` 并初始化 staged Git repo 证明工具成功；secret-like sentinel 注入 raw message 并断言不进入 serialized approval events；eval-only。

### TASK-019: Durable approval event logging ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent` 237 tests OK；`python3 evals/run_evals.py` 113 passed；`git diff --check` OK。
- 内容: `ToolRegistry.call` 对 permissioned tool confirmation 记录 approval requested/decided durable events；payload 仅含 tool_name、permission category/risk、requires_confirmation、argument_count、argument_keys、reason_present、decision status 等安全元数据；不持久化 raw arguments、reason text、confirmation prompt 或 secrets；event-write failure isolation；default registry wiring 完成；focused tests 覆盖 approved、denied、non-permissioned、broken/no event store、serialized safety。

### TASK-018: Eval coverage for test-run events ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 113 passed；`python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent` 237 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 test-run success、failure、blocked、timeout/OSError、event-write failure isolation；用 sentinel 和 forbidden payload key 断言确认 raw stdout/stderr、traceback/failure body、command args、reason、raw exception、secret-like values 不进入 payload/summary/serialized durable events；eval-only。

### TASK-017: Durable test-run event logging ✅
- 完成者: Claude A incomplete 后 Codex PM 接管整理
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_diagnostics tests.test_mini_agent` 227 tests OK；`python3 evals/run_evals.py` 108 passed；`python3 -m unittest discover -s tests` 1193 tests OK；`git diff --check` OK。
- 内容: `Diagnostics.run_tests` 记录 test-run started/finished/blocked/error durable events；registry wiring 注入 durable event store；payload 仅含 command_kind、status、exit_code、timeout、stdout/stderr byte counts、max_output_chars 和 generic error labels；sentinel/forbidden key tests 确认 raw stdout/stderr、traceback/failure body、command/args、reason、raw exception、secrets 不进入 serialized events；event-write failure isolation。

### TASK-016: Eval coverage for shell-command events ✅
- 完成者: Claude B；Codex PM 加固 forbidden payload-key 和 sentinel 断言
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 108 passed；`python3 -m unittest tests.test_durable_events tests.test_mini_agent` 203 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 shell-command success、blocked/disallowed、cancelled、timeout/OSError、event-store failure isolation；用 4 个 sentinel 和 10 个 forbidden payload key 断言确认 raw command args、stdout/stderr、raw exception、reason/secrets 不进入 serialized durable events；eval-only，无 runtime shim/fallback。

### TASK-015: Durable shell-command event logging ✅
- 完成者: Claude A；Codex PM 移植到主工作区并加固 raw command handling
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_events tests.test_mini_agent` 203 tests OK；`python3 evals/run_evals.py` 103 passed；`python3 -m unittest discover -s tests` 1183 tests OK；`git diff --check` OK。
- 内容: `ShellRunner.run` 记录 shell-command started/finished/blocked/error durable events；registry wiring 注入 durable event store；payload 仅含 executable、argv_count、status、exit_code、timeout、stdout/stderr byte counts 和 generic error labels；sentinel tests 确认 raw command、raw args、stdout/stderr、raw exception、reason/secrets 不进入 summary/payload/serialized events；event-write failure isolation。

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
