# Task Backlog

PM 从这里读取待分配的任务。每个任务格式：

## 待分配

### TASK-094: Deterministic eval coverage for scheduler blocker explanation v1
- 优先级: high
- 预计: 1-2 小时
- 依赖: TASK-093
- 目标: 为 scheduler blocker/explanation 工具增加 deterministic offline eval coverage，覆盖 pending/idle、not-ready closeout、missing lease、offline worker、already finalized、limit/bad params、安全不泄漏和 compatibility。
- 验证: `python3 evals/run_evals.py`；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent`；`git diff --check`。

## 进行中

### TASK-093: Worker lifecycle scheduler blocker explanation v1
- 分配给: Claude A
- 目标: 新增只读 scheduler explain/blocker 工具，复用现有 planner/closeout candidate state，输出 bounded reason labels，解释 pending tasks、idle workers、running workers、workspace leases、ready/not-ready closeouts 和 scheduler 下一步为什么会执行/跳过/阻塞。
- 状态: assigned

## 已完成

### TASK-092: Deterministic eval coverage for scheduler loop v1 ✅
- 完成者: Claude B；按 PM 初审反馈补强 weak assertions
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 323 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 651 tests OK；`python3 -m unittest discover -s tests` 2010 tests OK；`git diff --check` OK。
- 内容: 为 `run_worker_lifecycle_scheduler_loop` 增加 11 个 deterministic offline eval，覆盖 dry-run no mutation、max_ticks/limit bounds、stop_when_idle true/false、non-dry-run closeout-only 且不 dispatch pending task、dispatch/wait reason labels、record_event true/false、bad params、安全不泄漏和兼容性。

### TASK-091: Worker lifecycle scheduler loop v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests` 61 tests OK；`python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests` 28 tests OK；`python3 -m unittest tests.test_durable_workers` 484 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 651 tests OK；`python3 evals/run_evals.py` 312 passed；`python3 -m unittest discover -s tests` 2010 tests OK；`git diff --check` OK。
- 内容: 新增 guarded `run_worker_lifecycle_scheduler_loop(max_ticks=3, limit=5, dry_run=True, release_workspace=True, stop_when_idle=True, record_event=True)`；默认 dry-run；复用 scheduler tick 执行有限轮 tick；`max_ticks`/`limit` bounded，支持 idle early-stop；记录 bounded `scheduler_decision` loop event；输出和事件仅含 safe metadata。

### TASK-090: Deterministic eval coverage for worker lifecycle run-once ✅
- 完成者: Claude B partial；Codex PM 因 CCB provider_api_error 本地接手完成
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 312 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 623 tests OK；`python3 -m unittest discover -s tests` 1982 tests OK；`git diff --check` OK。
- 内容: 为 `run_worker_lifecycle_once(limit=5, dry_run=True, release_workspace=True)` 增加 deterministic offline eval coverage，覆盖 dry-run/no-mutation、safe closeout execution、wait/dispatch skipped、limit/release validation、安全不泄漏、failed finalize accounting 和 compatibility。

### TASK-089: Worker lifecycle scheduler tick v1 ✅
- 完成者: Claude A partial；Codex PM 因 CCB provider_api_error 本地接手完成
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests` 61 tests OK；`python3 -m unittest tests.test_durable_workers` 456 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 623 tests OK；`python3 evals/run_evals.py` 312 passed；`python3 -m unittest discover -s tests` 1982 tests OK；`git diff --check` OK。
- 内容: 新增 guarded `run_worker_lifecycle_scheduler_tick(limit=5, dry_run=True, release_workspace=True, record_event=True)`；默认 dry-run；复用 run-once 执行逻辑；记录 bounded `scheduler_decision` event；非 dry-run 只允许 ready closeout；dispatch 被 blocked，wait actions 被 skipped。

### TASK-088: Deterministic eval coverage for worker lifecycle planner ✅
- 完成者: Claude B；Codex PM 修复 eval API/fixture isolation 问题
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 304 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 604 tests OK；`python3 -m unittest discover -s tests` 1963 tests OK；`git diff --check` OK。
- 内容: 为 `plan_worker_lifecycle_actions(limit=20)` 增加 deterministic offline eval coverage，覆盖 empty/ready/not-ready/missing lease/dispatch recommendation/mixed/limit/100 raw-candidate 边界、安全不泄漏、no mutation 和 compatibility。

### TASK-087: Guarded worker lifecycle run-once v1 ✅
- 完成者: Claude A；Codex PM 补强 confirmation permission 和 failed-count accounting
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecyclePlannerTests` 42 tests OK；`python3 evals/run_evals.py` 304 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 604 tests OK；`python3 -m unittest discover -s tests` 1963 tests OK；`git diff --check` OK。
- 内容: 新增 `run_worker_lifecycle_once(limit=5, dry_run=True, release_workspace=True)`；默认只 dry-run，`dry_run=False` 时仅执行 ready closeout，不 dispatch、不执行 wait actions、不做 shell/git/project/workspace writes；注册为需要确认的 task/write。

### TASK-086: Deterministic eval coverage for batch workspace merge closeout ✅
- 完成者: Claude B；Codex PM 补强 release/idempotency/file-content eval assertions
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 298 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 580 tests OK；`python3 -m unittest discover -s tests` 1939 tests OK；`git diff --check` OK。
- 内容: 为 `finalize_ready_worker_workspace_merges(limit=10, release_workspace=True)` 增加 deterministic offline eval coverage，覆盖多 ready finalize、ready-limit semantics、100 raw-candidate 边界、release true/false、idempotency、bad args、安全不泄漏、expected-only mutation 和 compatibility。

### TASK-085: Worker lifecycle action planner v1 ✅
- 完成者: Claude A；Codex PM 补强 ready-action priority / raw-candidate scan regression
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecyclePlannerTests` 18 tests OK；`python3 evals/run_evals.py` 298 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 580 tests OK；`python3 -m unittest discover -s tests` 1939 tests OK；`git diff --check` OK。
- 内容: 新增只读 `plan_worker_lifecycle_actions(limit=20)`，为 Codex PM 返回下一步 worker lifecycle 建议，包括 ready closeout、等待 merge apply/lease、pending task + idle worker 的 dispatch 推荐；只规划，不执行；扫描 worker/task pairs 并优先返回 ready closeout action。

### TASK-084: Deterministic eval coverage for worker workspace merge closeout candidates ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 293 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 561 tests OK；`python3 -m unittest discover -s tests` 1920 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval coverage，覆盖 `list_worker_workspace_merge_closeout_candidates` ready path、no apply、already finalized、offline/idle worker、task not running、no lease、stale apply、filters、limit bounds、bad limit、安全不泄漏、read-only/no mutation，以及 finalize/audit/registry/claim/dispatch compatibility。

### TASK-083: Guarded batch closeout for ready worker workspace merges ✅
- 完成者: Claude A；Codex PM 补强 ready-candidate limit semantics
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkspaceBatchFinalizeTests` 18 tests OK；`python3 evals/run_evals.py` 293 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 562 tests OK；`python3 -m unittest discover -s tests` 1921 tests OK；`git diff --check` OK。
- 内容: 新增 `finalize_ready_worker_workspace_merges(limit=10, release_workspace=True)`；批量处理 closeout candidates 中 `ready_to_finalize` 的 worker/task，逐个复用单任务 finalize 逻辑；`limit` 按 ready candidates 计数，扫描 worker/task pairs，不被 not-ready candidates 或前 100 个 raw candidates 截断；不写 project root、不删除 workspace、不执行 shell/git、不启动 worker。

### TASK-082: Deterministic eval coverage for worker workspace merge finalization ✅
- 完成者: Claude B；Codex PM 补强 stale apply event / unique file path eval fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 288 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 544 tests OK；`python3 -m unittest discover -s tests` 1903 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval coverage，覆盖 `finalize_worker_workspace_merge` successful finalize、no apply、missing lease、stale apply event predating active lease、invalid `release_workspace`、`release_workspace=False`、repeated finalization、non-running task、no-leak/no-mutation，以及 failed/successful finalization 后 compatibility。

### TASK-081: Worker workspace merge closeout candidate query v1 ✅
- 完成者: Claude A；Codex PM 撤回 out-of-scope lease id / apply no-op changes，并补强 active lease created_at stale-event gate
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkspaceApplyMergeTests tests.test_durable_workers.WorkspaceMergeFinalizeTests tests.test_durable_workers.WorkspaceMergeCloseoutCandidateTests` 76 tests OK；`python3 evals/run_evals.py` 288 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 544 tests OK；`python3 -m unittest discover -s tests` 1903 tests OK；`git diff --check` OK。
- 内容: 新增只读 `list_worker_workspace_merge_closeout_candidates(worker_id="", task_id="", limit=20)`；返回哪些 worker/task ready to finalize、哪些因 no apply / stale apply / no lease / worker mismatch / task status / already finalized 等原因不能 finalize；候选 ready 需要 running task、active worker/current_task、active lease、同 worker/task/lease 且不早于当前 lease 创建时间的 successful apply event；不 mutation、不释放 lease、不调用 finalize。

### TASK-080: Worker workspace merge finalization v1 ✅
- 完成者: Claude A；Codex PM 补强 active lease validation / lease_id-bound apply event / invalid release flag review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkspaceMergeFinalizeTests` 23 tests OK；`python3 evals/run_evals.py` 283 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 522 tests OK；`python3 -m unittest discover -s tests` 1881 tests OK；`git diff --check` OK。
- 内容: 新增 guarded `finalize_worker_workspace_merge(worker_id, task_id, release_workspace=True)`；未完成任务必须通过 active worker/task/workspace lease 校验；必须存在同 worker/task/active lease 的 successful `workspace_merge_apply` audit event；完成 task、将 worker 置 idle 并清空 current_task_id，默认释放 lease；支持 `release_workspace=False` 保留 lease；重复完成后返回 bounded `already_finalized`；输出和事件仅含 safe metadata；不删除 workspace、不执行 shell/git、不写 project root、不应用 patch。

### TASK-079: Deterministic eval coverage for worker workspace merge apply audit/history ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 283 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 522 tests OK；`python3 -m unittest discover -s tests` 1881 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval coverage，覆盖 `list_worker_workspace_merge_applies` empty/result basics、worker/task filters、limit bounds、bad limit error、filtering behavior、malformed payload safety、sensitive/traversal/absolute/long path filtering、no-leak/read-only behavior，以及 apply/dry-run/summary/patch export/review gate/lease/registry/claim/dispatch compatibility。

### TASK-078: Worker workspace merge apply audit/history v1 ✅
- 完成者: Claude A；Codex PM 补强 operation-after-limit filtering / malformed sensitive path-id filtering review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkspaceMergeAuditTests` 17 tests OK；`python3 evals/run_evals.py` 278 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 499 tests OK；`python3 -m unittest discover -s tests` 1858 tests OK；`git diff --check` OK。
- 内容: 新增只读 `list_worker_workspace_merge_applies(worker_id="", task_id="", limit=20)`；查询 `workspace_merge` / `workspace_merge_apply` file edit events，支持 worker/task/limit 过滤，输出 event_id、created_at、worker/task/lease ids、applied/created/modified counts、safe paths；对 malformed payload 使用 safe defaults，过滤 sensitive/denied/traversal/absolute/redacted paths；不返回 raw content、patch、task goal/steps、reviewer summary、shell/env/request strings 或 secrets。

### TASK-077: Deterministic eval coverage for worker workspace reviewed merge apply ✅
- 完成者: Claude B；Codex PM 补强 symlink/project symlink/patch budget/safety/rollback eval coverage
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 278 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 499 tests OK；`python3 -m unittest discover -s tests` 1858 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval coverage，覆盖 `apply_reviewed_worker_workspace_merge` approved created/modified apply、post-apply dry-run no_changes、no gate/changes_requested/blocked/no changes rejection、sensitive/binary/oversized/workspace symlink escape/project symlink-to-sensitive/patch budget safety boundaries、validation errors、安全不泄漏 raw patch/file content/task goal/steps/reviewer summary/shell/request strings/secrets、rollback/no-mutation、workspace_merge event metadata，以及 audit/dry-run/review gate/registry/lease/claim/dispatch compatibility。

### TASK-076: Worker workspace reviewed merge apply v1 ✅
- 完成者: Claude A；Codex PM 补强 apply-time skipped/budget recheck、bounded failure errors、rollback metadata、safety/compatibility tests
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkspaceApplyMergeTests` 31 tests OK；`python3 -m unittest tests.test_durable_workers` 315 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 482 tests OK；`python3 evals/run_evals.py` 272 passed；`python3 -m unittest discover -s tests` 1841 tests OK；`git diff --check` OK。
- 内容: 新增 guarded project-root apply tool `apply_reviewed_worker_workspace_merge(worker_id, task_id, max_files=50)`；apply 时重跑 dry-run 且 ready 才允许写入；再次检查 summary skipped、patch skipped 和 patch budget；仅复制 safe created/modified text files 到 project root；拒绝 sensitive/binary/oversized/symlink escape/project symlink-to-sensitive-file/patch budget 情况；失败后 rollback modified/created writes；输出和 `workspace_merge` file-edit event 只含 bounded safe metadata；不做 git、不执行 shell、不删除文件。

### TASK-075: Deterministic eval coverage for worker workspace reviewed merge dry-run ✅
- 完成者: Claude B；Codex PM 补强 project symlink / patch budget / preview compatibility / safety assertions review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 272 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 451 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval coverage，覆盖 `dry_run_worker_workspace_merge` approved ready path、no gate / changes_requested / blocked / no changes not-ready states、sensitive worker path filtering、project symlink-to-sensitive-file、binary/oversized skipped entries、multi-file patch budget overflow、unknown worker/no lease/task mismatch/offline/idle/bad max_files validation、安全不泄漏 raw patch/file content/task goal/steps/reviewer summary/shell/request strings/secrets、dry-run no mutation，以及 worker/task registry、workspace lease、sandbox guard、read/list/preview/write、change summary/patch export、review gate、claim、dispatch compatibility。

### TASK-074: Worker workspace reviewed merge dry-run v1 ✅
- 优先级: high
- 预计: 1-2 小时
- 依赖: TASK-072/TASK-073
- 完成者: Claude A；Codex PM 补强 patch budget / project symlink / compatibility review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 284 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 451 tests OK；`python3 evals/run_evals.py` 265 passed；`python3 -m unittest discover -s tests` 1810 tests OK；`git diff --check` OK。
- 内容: 新增只读 worker workspace reviewed merge dry-run tool：`dry_run_worker_workspace_merge(worker_id, task_id, max_files=50)`；复用 active worker/task/workspace lease 校验、TASK-070 change summary/patch export safety、TASK-072 latest review gate lookup；返回 bounded metadata，包括 `ready`、safe reason labels、review gate state、created/modified/same/skipped counts、patch/skipped patch counts、patch bytes 和 worker/task/lease ids；只有 approved gate、存在安全变更、无 summary/patch skipped、patch bytes 未超预算时才 ready；不返回 raw patch、file content、summary body、task goal/steps、reviewer notes、shell/env/request strings 或 secrets；不写 project root、worker workspace 或 durable state。

### TASK-073: Deterministic eval coverage for worker workspace review gate artifacts ✅
- 完成者: Claude B；Codex PM 补强 no-lease/get validation / filesystem no-mutation / claim-dispatch compatibility review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 265 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 593 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 review gate approved/changes_requested/blocked 记录、no-gate/latest gate 查询、unknown decision/unknown worker/no lease/task mismatch/offline/idle validation、安全不泄漏 reviewer/summary/patch/diff/shell/env/task goal/steps、sensitive reviewer redaction、event payload safe metadata、event-store failure bounded error/no mutation、query failure bounded error，以及 worker/task registry、workspace lease、sandbox guard、file inspection、write tools、change summary/patch export、claim/dispatch compatibility。

### TASK-072: Worker workspace review gate artifact v1 ✅
- 完成者: Claude A；Codex PM 补强 reviewer sanitization / event failure / query failure review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 261 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 593 tests OK；`python3 evals/run_evals.py` 260 passed；`python3 -m unittest discover -s tests` 1787 tests OK；`git diff --check` OK。
- 内容: 新增 worker workspace review gate artifact tools：`record_worker_workspace_review_gate(worker_id, task_id, decision, reviewer="codex_pm", summary="", checks_passed=True, patch_exported=True)` 和 `get_worker_workspace_review_gate(worker_id, task_id)`；复用 active worker/task/workspace lease 校验；支持 `approved`、`changes_requested`、`blocked` 决策；以 `REVIEW_GATE_FINISHED` durable event 记录安全元数据，包括 worker/task/lease、decision、safe reviewer label、summary_present/summary_length、checks_passed、patch_exported；查询最新 gate 或返回 bounded no-gate；不记录 raw summary、patch/diff、task goal/steps、shell/env/request strings 或 secrets；event/query failure 返回 bounded JSON error；不做 project-root merge、不应用 patch、不改 project root 或 worker workspace。

### TASK-071: Deterministic eval coverage for worker workspace change export tools ✅
- 完成者: Claude B；Codex PM 补强 validation / project symlink / patch budget review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 260 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 401 tests OK；`git diff --check` OK。
- 内容: 新增 15 个 deterministic offline eval，覆盖 worker workspace change summary created/modified/same classification、metadata-only output、max_files bounds、sensitive path filtering、workspace symlink escape、safety no-leak、no mutation；patch export created/modified/same/single-file behavior、context/max_files bounds、binary/oversized skips、traversal/absolute escape/sensitive path rejection、workspace symlink rejection、安全不泄漏、no mutation；两工具共同覆盖 unknown worker/no lease/task mismatch/offline/idle rejection、project-root symlink-to-sensitive-file 安全跳过/拒绝、单文件和多文件 patch budget，以及 worker/task registry、workspace lease、sandbox guard、file inspection、write tools、claim/dispatch compatibility。

### TASK-070: Worker workspace change summary / patch export tools v1 ✅
- 完成者: Claude A；Codex PM 补强 sensitive path / symlink / patch budget review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 234 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 401 tests OK；`python3 evals/run_evals.py` 245 passed；`python3 -m unittest discover -s tests` 1760 tests OK；`git diff --check` OK。
- 内容: 新增只读 worker workspace change export tools：`summarize_worker_workspace_changes(worker_id, task_id, max_files=50)` 和 `export_worker_workspace_patch(worker_id, task_id, path="", max_files=50, context_lines=3)`；复用 active worker/task/workspace lease 校验；对比 worker workspace 与 project root，输出 created/modified/same/skipped 安全元数据或 bounded unified diff；拒绝/跳过 traversal、absolute escape、offline/idle、missing/no lease、task mismatch、敏感文件/目录与中间路径组件、symlink escape、project-root symlink-to-sensitive-file、binary/non-UTF8/oversized 文件；单文件和多文件 patch 输出受 64KB 预算限制；不写 project root、不修改 worker workspace 或 durable 状态。

### TASK-069: Deterministic eval coverage for worker workspace write tools ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 245 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 353 tests OK；`git diff --check` OK。
- 内容: 新增 9 个 deterministic offline eval，覆盖 worker workspace write/replace/patch valid scoped writes、relative/absolute path escape、empty path/old_text/patch、unknown worker/no lease/task mismatch、offline/idle rejection、敏感文件/目录与 symlink escape/symlink-to-denied-dir、安全不泄漏 outputs/events、oversized content/result/patch、binary/non-UTF8 existing files、error no-mutation，以及 write tools 与 worker/task registry、workspace lease、sandbox guard、file inspection、claim/dispatch 的 compatibility。

### TASK-068: Worker workspace write tools v1 ✅
- 完成者: Claude A；Codex PM 补强 sensitive path / event / rollback review fixes
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 186 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 353 tests OK；`python3 evals/run_evals.py` 236 passed；`python3 -m unittest discover -s tests` 1712 tests OK；`git diff --check` OK。
- 内容: 新增 worker-scoped write tools：`write_worker_workspace_file(worker_id, task_id, path, content, reason="")`、`replace_worker_workspace_file(worker_id, task_id, path, old_text, new_text, reason="")`、`apply_worker_workspace_patch(worker_id, task_id, patch, reason="")`；全部复用 active worker/task/workspace lease 校验；路径限定在 worker 当前 lease workspace 内；拒绝 traversal、absolute escape、offline/idle worker、missing/no lease、task mismatch、`.env`/`.env.local`/`.env.production` 任意路径层级、`.git`/`logs`/`data`/cache dirs、symlink escape 与 symlink-to-denied-dir；输出 bounded JSON metadata；记录 safe file-edit events；patch 使用 workspace unified diff helpers 并在 partial write failure 时回滚。

### TASK-067: Deterministic eval coverage for worker workspace file inspection ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 236 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 314 tests OK；`git diff --check` OK。
- 内容: 新增 8 个 deterministic offline eval，覆盖 worker workspace file inspection valid list/read/preview、relative/absolute/deep path escape、empty path、unknown/no-lease/task mismatch、offline/idle stale lease rejection、goal/step/secret sentinel 不泄漏、oversized/binary read bounded error、direct `.env`/`.git` rejection、symlink escape、symlink to denied dirs (`gitlink -> .git/config`, `loglink -> logs/app.log`)、no-mutation，以及 file inspection 后 worker/task/lease/sandbox guard/claim/dispatch compatibility。

### TASK-066: Worker workspace file inspection tools v1 ✅
- 完成者: Claude A
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 314 tests OK；`python3 evals/run_evals.py` 228 passed；`git diff --check` OK。
- 内容: 新增 worker-scoped read-only file inspection tools：`list_worker_workspace_files(worker_id, task_id, max_files=50)`、`read_worker_workspace_file(worker_id, task_id, path)`、`preview_worker_workspace_write(worker_id, task_id, path, content, context_lines=3)`；复用 active worker/task/workspace lease 校验；relative path 在 lease root 下解析，absolute path 仅允许 resolved target 留在 workspace 内；拒绝 traversal、absolute escape、offline/idle worker、missing/no lease、task mismatch、敏感 `.env`/denied dirs；preview 只返回 diff 不写文件；list 跳过 symlink escape、symlink to denied dirs、bad numeric inputs 返回 bounded JSON error。

### TASK-065: Deterministic eval coverage for worker workspace sandbox guard ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 228 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 585 tests OK；`python3 -m unittest discover -s tests` 1641 tests OK；`git diff --check` OK。
- 内容: 新增 7 个 deterministic offline eval，覆盖 sandbox guard valid workspace paths、path traversal rejection、absolute path escape rejection、unknown/no-lease/task-mismatch/empty-path errors、offline/idle worker with stale lease rejection、安全不泄漏 goal/steps/secrets、sandbox error 后 worker/task list/get 与 claim compatibility，以及 post-claim absolute workspace path strict `valid is True`。

### TASK-064: Worker workspace sandbox guard v1 ✅
- 完成者: Claude A
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 228 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 585 tests OK；`python3 -m unittest discover -s tests` 1641 tests OK；`git diff --check` OK。
- 内容: 新增只读 sandbox guard tools：`get_worker_workspace(worker_id, task_id)` 和 `validate_worker_workspace_path(worker_id, task_id, path)`；共享 `_resolve_and_validate_lease()` 校验 worker 存在、非 offline/idle、current task 匹配、task owner 匹配、workspace lease 存在且 task 匹配；path validation 使用 `Path.resolve()` 与 resolved workspace root containment 拒绝 traversal/absolute escape；输出 bounded metadata，不创建文件，不执行命令。

### TASK-063: Deterministic eval coverage for worker workspace integration ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 221 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 565 tests OK；`python3 -m unittest discover -s tests` 1621 tests OK；`git diff --check` OK。
- 内容: 新增 10 个 deterministic offline eval，覆盖 claim/dispatch 自动准备 workspace、same-worker same-task lease reuse、多 worker dispatch unique leases、offline/idle/mismatch 不产生非法 workspace、workspace prepare failure 不阻断 claim/dispatch、错误后 list/get compatibility、workspace sub-dict 不泄漏 raw goal/steps/secrets、`WORKSPACE_PREPARED` event safe metadata，以及 no-task dispatch 无 workspace activity。

### TASK-062: Worker workspace preparation integration ✅
- 完成者: Claude A
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 221 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 565 tests OK；`python3 -m unittest discover -s tests` 1621 tests OK；`git diff --check` OK。
- 内容: 将 workspace lease preparation 接入 `claim_durable_task` 和 `dispatch_durable_tasks`；成功 claim/dispatch 后 best-effort prepare workspace，并在返回值中附带 bounded `workspace` metadata 或 `workspace.error`；workspace failure 不阻断任务分配；same worker + same task prepare 变为 idempotent `reused: true`；different-worker same-task uniqueness 继续返回 `existing_lease_id` error。

### TASK-061: Deterministic eval coverage for worker workspace lease ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 211 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 553 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 `prepare_worker_workspace` / `release_worker_workspace` happy path、validation errors、worker/task lease uniqueness、release/no-lease/re-prepare 行为、bounded output/event safety、mkdir failure no lease、broken event-store failure isolation，以及 worker/task registry compatibility。复审后补强了真实 task-level duplicate lease registry 分支：同一 task 已有 lease 后重新 assign 给第二个 active worker，调用 prepare 返回 `existing_lease_id`。

### TASK-060: Worker workspace lease / isolation v1 ✅
- 完成者: Claude A
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 211 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 553 tests OK；`git diff --check` OK。
- 内容: 新增 durable worker workspace lease 基础能力：`WorkspaceLeaseStore`、`DurableWorkspaceLease`、`WORKSPACE_PREPARED` / `WORKSPACE_RELEASED` events，以及 registry tools `prepare_worker_workspace(worker_id, task_id)` / `release_worker_workspace(worker_id)`；prepare 要求 worker 非 idle/offline、`current_task_id` 匹配且 task owner 匹配，防止同 worker 或同 task 重复 lease；mkdir 失败返回 bounded error 且不落 lease；release 只删除 lease 不删除目录；event-store failure 不阻断 lease 操作。

### TASK-059: Deterministic eval coverage for durable task timeline ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 206 passed；`python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 470 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 `get_durable_task_timeline` 的 chronological ordering、task/checkpoint/recovery event presence、bounded summaries、event/checkpoint/recovery linkage、`payload_keys` key names only、limit bounds、unknown task/bad limit errors、安全不泄漏 goal/step/note/summary/checkpoint description/state_snapshot/secret-like sentinels、allowed-fields-only 输出、timeline no-mutation，以及 error/no-op 后 existing registry tool compatibility。

### TASK-058: Durable task timeline inspection tool v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 470 tests OK；`python3 evals/run_evals.py` 202 passed；`git diff --check` OK。
- 内容: 新增只读 `get_durable_task_timeline(task_id, limit=50)` registry tool，按 chronological oldest-first 返回 durable task 的 bounded safe timeline；task summary 仅包含 status/count/presence metadata，event summaries 仅包含 safe metadata 和 sorted `payload_keys` key names；limit bounded 到 1..200，bad limit/unknown task/event-store failure 返回 JSON error；event-store failure 不回显原始异常文本；不泄漏 goal、step、notes、summary、checkpoint description、state_snapshot、payload values 或 secret-like 内容，且不 mutate task/event state。

### TASK-057: Deterministic eval coverage for recovery-plan events ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 202 passed；`python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 458 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 `RECOVERY_PLANNED` event metadata、source/severity、top-level `checkpoint_id` linkage、explicit/step/no-checkpoint/terminal selection events、payload allowed-fields-only、直接注入 step note/summary 与 checkpoint description/state_snapshot sentinel 的 serialized event 泄漏检查、broken event-store failure isolation、planning no-mutation，以及 recovery planning 后 existing registry tool compatibility。

### TASK-056: Durable recovery plan event logging v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 458 tests OK；`python3 evals/run_evals.py` 198 passed；`git diff --check` OK。
- 内容: 新增 `RECOVERY_PLANNED = "recovery_planned"` durable event type；`plan_durable_recovery` 成功生成计划后记录 safe bounded event，包含 `operation=plan_recovery`、`can_resume`、`resume_policy`、`reason`、checkpoint/step/count/worker presence metadata；选中 checkpoint 时写入 top-level `checkpoint_id` 便于查询；错误路径跳过 event logging；event-store failure 不阻断 plan 返回；保持 recovery planning 只读且不泄漏 raw goal、step、notes、summaries、checkpoint description 或 state_snapshot。

### TASK-055: Deterministic eval coverage for durable recovery plans ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 198 passed；`python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 452 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 recovery plan basics、explicit/step/latest/no-checkpoint selection、missing checkpoint fallback、unknown task/checkpoint/bad step errors、terminal status、`resume_policy=from_checkpoint`、严格 `next_step_id==2` 回归断言、allowed-fields-only bounded output、直接注入 step note/summary 与 checkpoint description/state_snapshot sentinel 的泄漏检查、planning no-mutation，以及 error/no-op 后 existing registry tool compatibility。

### TASK-054: Durable recovery plan tool v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 452 tests OK；`python3 evals/run_evals.py` 194 passed；`git diff --check` OK。
- 内容: 新增只读 `plan_durable_recovery(task_id, checkpoint_id="", step_id="")` registry tool；按 explicit checkpoint、step checkpoint、latest checkpoint、no-checkpoint fallback 生成恢复计划；输出 `can_resume`、`resume_policy`、`next_step_id`、safe reason labels 和 bounded counts；选中 checkpoint 时返回 `from_checkpoint`，terminal statuses 不可恢复；不 mutate task，不执行恢复，不启动 worker，不泄漏 goal、step、notes、summaries、checkpoint description 或 raw state_snapshot。

### TASK-053: Deterministic eval coverage for durable checkpoint controls ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 194 passed；`python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 433 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 explicit checkpoint basics、checkpoint count increments、bounded JSON output、unknown task error、step `checkpoint_ref` linking、trace refs preservation、bad/large `step_id` handling、`CHECKPOINT_ADDED` safe event metadata、sentinel leakage safety、broken event-store failure isolation，以及 existing durable task registry compatibility。

### TASK-052: Durable checkpoint control tools v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 433 tests OK；`python3 evals/run_evals.py` 190 passed；`python3 -m unittest discover -s tests` 1554 tests OK；`git diff --check` OK。
- 内容: 新增 `add_durable_checkpoint(task_id, step_id=0, description="", state_summary="")` registry tool；复用 `DurableTaskStore.add_checkpoint()`；非整数 `step_id` 返回 JSON error，负数 clamp 到 0；checkpoint snapshot 只保存 safe metadata；匹配 step 时写入 `checkpoint_ref`；输出 bounded JSON；记录 `CHECKPOINT_ADDED` event 且仅包含安全元数据；event failure 不阻断 checkpoint 创建。

### TASK-051: Deterministic eval coverage for durable lifecycle controls ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 190 passed；`python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_durable_workers tests.test_mini_agent` 487 tests OK；`git diff --check` OK。
- 内容: 新增 4 个 deterministic offline eval，覆盖 `pause_durable_task` / `resume_durable_task` / `cancel_durable_task` lifecycle basics、invalid transitions、unknown task、retry compatibility、worker pause/resume/cancel consistency、offline/unrelated worker preservation、safe bounded outputs、event payload safety、broken event-store failure isolation，以及 existing registry tool compatibility。

### TASK-050: Durable task lifecycle control tools v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_tasks tests.test_durable_events tests.test_durable_workers tests.test_mini_agent` 487 tests OK；`python3 evals/run_evals.py` 190 passed；`git diff --check` OK。
- 内容: 新增 `pause_durable_task`、`resume_durable_task`、`cancel_durable_task` registry tools；复用 `DurableTaskStore.update_status()` 状态机；`resume` 只允许 paused/blocked -> running；pause/cancel reason 只记录 presence metadata；输出 bounded JSON，不返回 goal/steps/raw reason；同步匹配 worker 的 paused/running/idle 状态并保留 offline/unrelated workers；`TASK_STATUS_CHANGED` events 仅写安全元数据，event/worker store failure 不阻断 task transition。

### TASK-049: Deterministic eval coverage for durable worker auto-dispatch ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 186 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 468 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 `dispatch_durable_tasks` oldest-task dispatch、`max_assignments` normal/0/oversized bounds、running/assigned/paused/offline worker exclusion、no-idle/no-pending no-op、task `worker_id` 与 worker `assigned/current_task_id` 一致性、task status 保持 pending、安全输出、event-store failure isolation，以及 dispatch 后 worker/task registry tool compatibility。

### TASK-048: Durable worker auto-dispatch v1 ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 468 tests OK；`python3 evals/run_evals.py` 186 passed；`git diff --check` OK。
- 内容: 新增 `dispatch_durable_tasks` registry tool，将 pending/unassigned durable tasks 自动派发给 idle/online worker；派发前复用 stale worker lifecycle 将过期 worker 标记 offline；按 `created_at` 选择最早 pending tasks，按 worker id 稳定配对，`max_assignments` bounded 到 1..50；更新 task `worker_id` 和 worker `assigned/current_task_id`，保持 task status 不变；输出 bounded assignment summary，事件写入失败不阻断派发。

### TASK-047: Deterministic eval coverage for Context compiler structured memory recall ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 182 passed；`python3 -m unittest tests.test_context_compiler tests.test_context_memory tests.test_memory_records tests.test_mini_agent` 251 tests OK；`python3 -m unittest discover -s tests` 1509 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 `compile_context_pack` structured memory recall basics、默认/显式 memory query、关闭 memory recall、安全过滤 unsafe title/content/tags/source/task_id、oversized content bounding、budget stability，以及 Git Status、Changed Files、file outline、RAG snippets、structured memory 的 strict compatibility assertions。

### TASK-046: Context compiler v2 — structured memory recall ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_context_compiler tests.test_context_memory tests.test_memory_records tests.test_mini_agent` 251 tests OK；`python3 evals/run_evals.py` 182 passed；`python3 -m unittest discover -s tests` 1509 tests OK；`git diff --check` OK。
- 内容: `ContextCompiler` 新增 structured `MemoryRecordStore` recall，`compile_context_pack` 支持 `include_memory_records`、`memory_query`、`memory_max_results`；registry builder 注入 DB-backed memory record store；输出新增 bounded `结构化记忆` section，并复用 auto-context structured memory safety/formatting。

### TASK-045: Deterministic eval coverage for structured memory recall ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 178 passed；`python3 -m unittest tests.test_context_memory tests.test_context_compiler tests.test_memory_records tests.test_mini_agent` 240 tests OK；`python3 -m unittest discover -s tests` 1498 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 structured memory recall basics、ranking/filtering、max result bounding、oversized content truncation、secret/prompt/diff/shell/env/unsafe metadata safety，以及 context summary、long-term memory、project/RAG snippet、structured memory 的 strict sentinel compatibility。

### TASK-044: Structured memory recall in Nora auto-context v1 ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_context_memory tests.test_context_compiler tests.test_memory_records tests.test_mini_agent` 240 tests OK；`python3 evals/run_evals.py` 178 passed；`python3 -m unittest discover -s tests` 1498 tests OK；`git diff --check` OK。
- 内容: `ContextSystem` 新增 structured `MemoryRecordStore` recall，自动上下文增加 `结构化记忆` section；app wiring 注入 DB-backed memory record store；召回输出按记录数与内容长度 bounded；过滤所有会输出字段中的 secret-like 内容、prompt transcript、diff、shell output、env-var assignments；保留安全 tags/source/task metadata。

### TASK-043: Deterministic eval coverage for review memory capture ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 174 passed；`python3 -m unittest tests.test_review_memory tests.test_memory_records tests.test_mini_agent tests.test_tool_cache` 226 tests OK；`python3 -m unittest discover -s tests` 1475 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 review memory capture approved/non-approved、secret/diff/shell/prompt/env-var safety、oversized content bounding、dedupe、failure isolation、searchability，以及 search/list/tool output 不泄漏 full content 或 safety sentinel。

### TASK-042: Review memory capture v1 ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_review_memory tests.test_memory_records tests.test_mini_agent tests.test_tool_cache` 226 tests OK；`python3 evals/run_evals.py` 174 passed；`python3 -m unittest discover -s tests` 1475 tests OK；`git diff --check` OK。
- 内容: 新增 `mini_agent.review_memory` 显式 capture 层和 `capture_review_memory` registry tool，将 bounded review/task summary 写入 structured `MemoryRecordStore`；approved 可写 task_learning/decision/risk，changes_requested/blocked 仅允许显式 risk；拒绝 secrets、diff、shell output、prompt transcript/chat template、env-var assignment、raw artifacts；返回 bounded JSON 并支持 deterministic dedupe、`related_task_id`、`source` 和 review/task/status tags。

### TASK-041: Deterministic eval coverage for Nora MCP server adapter ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 168 passed；`python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache` 159 tests OK；`python3 -m unittest discover -s tests` 1433 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 MCP optional dependency、metadata export、safe allowlist、bounded adapter output、memory/structured-memory compatibility、unknown/malformed/handler-error failure isolation，以及 handler exception secret sentinel 不泄漏。

### TASK-040: Optional MCP server adapter for Nora ToolRegistry ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache` 159 tests OK；`python3 evals/run_evals.py` 168 passed；`python3 -m unittest discover -s tests` 1433 tests OK；`git diff --check` OK。
- 内容: 新增 optional MCP server adapter `mini_agent/mcp_server.py`，支持 `nora-mcp` stdio entrypoint、optional `mcp` extra、safe default allowlist、OpenAI tool metadata 到 MCP tool metadata 转换、纯 Python `call_mcp_tool` adapter dispatch、bounded output、generic handler error；新增 `tests/test_mcp_server.py` 和 `docs/knowledge/MCP_INTEGRATION.md`。

### TASK-039: Eval coverage for native memory record store ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 163 passed；`python3 -m unittest tests.test_memory_records tests.test_mini_agent tests.test_tool_cache` 184 tests OK；`python3 -m unittest discover -s tests` 1408 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 structured memory record basics、query/scope/tags search、bounded list/search summaries、get/delete、安全拒绝 secret-like 内容、大内容不泄漏、legacy `save_memory`/`search_memory` compatibility、Supermemory no-key deterministic safety，以及 invalid input failure isolation。

### TASK-038: Nora native memory record store v1 ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_memory_records tests.test_mini_agent tests.test_tool_cache` 184 tests OK；`python3 evals/run_evals.py` 163 passed；`python3 -m unittest discover -s tests` 1408 tests OK；`git diff --check` OK。
- 内容: 新增 Nora local-first structured memory record store，支持 SQLite/JSONL backend、`decision/preference/fact/task_learning/risk/note` 类型、`project/user/global` scope 校验、CRUD/list/search/delete、scope/tags filters、bounded registry summaries、secret-like 内容拒绝；registry 新增 `save_memory_record`、`search_memory_records`、`list_memory_records`、`get_memory_record`、`delete_memory_record`；新增 `docs/knowledge/MEMORY_KERNEL.md`。

### TASK-037: Eval coverage for optional Supermemory memory toolkit ✅
- 完成者: Claude B；Codex PM 补强 deterministic env/containerTag/metadata assertions
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 159 passed；`python3 -m unittest tests.test_supermemory tests.test_mini_agent tests.test_tool_cache` 171 tests OK；`python3 -m unittest discover -s tests` 1358 tests OK；`git diff --check` OK。
- 内容: 新增 deterministic offline eval，覆盖 no-key optional config、save 仅保存显式内容与 metadata、search/profile bounded output、metadata bounding/filtering、`SUPERMEMORY_CONTAINER_TAG` 配置、API/network failure isolation，以及现有本地 memory tools 不受 Supermemory 配置影响。

### TASK-036: Supermemory optional memory toolkit v1 ✅
- 完成者: Claude A；Codex PM 补强 metadata secret filtering 与 containerTag 配置
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_supermemory tests.test_mini_agent tests.test_tool_cache` 171 tests OK；`python3 evals/run_evals.py` 159 passed；`python3 -m unittest discover -s tests` 1358 tests OK；`git diff --check` OK。
- 内容: 新增 optional Supermemory client/toolkit 与 registry tools：`supermemory_save`、`supermemory_search`、`supermemory_profile`；支持 `SUPERMEMORY_API_KEY`、`SUPERMEMORY_BASE_URL`、`SUPERMEMORY_CONTAINER_TAG`；未配置 key 时返回 JSON error；search/profile 输出 bounded，metadata 仅保留安全标量并过滤 secret-like key/value；不新增依赖，网络/API 失败返回 JSON error。

### TASK-035: Eval coverage for durable worker heartbeat/offline lifecycle ✅
- 完成者: Claude B
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 152 passed；`python3 -m unittest tests.test_durable_workers tests.test_durable_events tests.test_durable_tasks tests.test_mini_agent` 441 tests OK；`python3 -m unittest discover -s tests` 1321 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic offline eval，覆盖 `touch_worker` heartbeat、未知/空白 worker 错误、stale→offline、fresh/already-offline 行为、保留 `current_task_id`、task ownership/status isolation、安全不泄漏，以及 broken event store 下 heartbeat/offline 行为不变。

### TASK-034: Durable worker task claim v1 ✅
- 完成者: Claude A
- Reviewer: Codex review (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers tests.test_durable_tasks tests.test_durable_events tests.test_mini_agent` 453 tests OK；`python3 evals/run_evals.py` 152 passed；`python3 -m unittest discover -s tests` 1321 tests OK；`git diff --check` OK。
- 内容: registry 新增 `claim_durable_task(worker_id)`；在线已注册 worker 可 claim 最老 pending/unassigned durable task；claim 同步 task `worker_id` 与 worker `assigned/current_task_id`，不改变 task status；已分配 worker 返回既有 assignment；无任务返回 `claimed: false`；成功 claim 记录安全 task action event，事件写入失败不影响 claim。

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
