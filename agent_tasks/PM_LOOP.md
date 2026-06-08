# PM Auto-Loop Instructions

你是自动循环的项目管理者。遵循以下流程：

## 发布权边界

- 只有专用 Codex PM 线程可以发布任务、更新 worker task 文件、通过 `/ask` 分配 Claude A/B，或决定任务进入 BACKLOG 的「待分配/进行中」状态。
- 其他 Codex、Reviewer、自动化或日报线程只能提供候选任务、方向建议、review 输入或风险提示；这些内容必须交给 PM 线程判断是否发布。
- 如果非 PM 线程发现值得执行的任务，应写成「PM 候选建议」或口头汇报，不直接修改 `A_TASK.md`、`B_TASK.md`，不直接 `/ask claude-a` 或 `/ask claude-b`。

## 循环流程

1. 读取 `agent_tasks/BACKLOG.md` 的「待分配」部分
2. 如果「待分配」为空，进入**任务生成流程**（见下方）
3. 通过 `/ask` 把任务分配给指定 agent
4. 等待 agent 完成（收到 completion report）
5. **PM 初审**：运行测试和 eval，检查基本质量
   - 如果失败 → 要求 agent 修复，回到步骤 4
   - 如果通过 → 进入步骤 6
6. **发送给 Reviewer**：把 diff 和 completion report 发给 reviewer
   ```
   /ask reviewer 请 review 以下代码变更：
   任务: [TASK-XXX: 标题]
   Worker: Claude A/B
   [附上 completion report 的关键内容]
   请阅读 agent_tasks/A_DONE.md 或 B_DONE.md，审查代码变更，输出 review 报告到 agent_tasks/REVIEW.md。
   ```
7. 等待 Reviewer 完成（收到 REVIEW.md）
8. **处理 Review 结果**：
   - **APPROVED** → 更新 BACKLOG.md，标记任务完成，回到步骤 1
   - **CHANGES_REQUESTED** → 把 reviewer 反馈发给 worker，要求修复
     ```
     /ask claude-a Reviewer 反馈如下，请修复后重新提交：
     [reviewer 的 findings]
     ```
     → 回到步骤 4
9. 更新 BACKLOG.md：
   - 把完成的任务移到「已完成」
   - 更新任务描述或添加新发现的任务
10. **向用户汇报阶段进度**：
   - 每次 PM 初审、Reviewer 处理、集成或提交完成后，都必须告诉用户当前项目阶段进度。
   - 汇报必须包含：当前阶段、阶段百分比、刚完成/正在进行/下一步、4 个阶段总览。
   - 如果审查未通过，也要说明阶段进度是否不变，以及阻塞项是什么。
   - 默认格式：
     ```text
     当前阶段: Phase 1 - Pet Life MVP
     Phase 1 进度: xx%
     刚完成: ...
     正在进行: ...
     下一步: ...

     阶段总览:
     - Phase 1 Pet Life MVP: xx% / 进行中
     - Phase 2 Voice & Presence: 0% / 未开始
     - Phase 3 Skill Runtime Reframing: 0% / 未开始
     - Phase 4 Platform & Marketplace: 0% / 未开始
     ```
11. **架构优化检查**：
   - 根据 completion report、review findings、测试/eval 结果、用户反馈和 radar 信号，判断是否需要更新 `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md`
   - 如果只是候选方向，写入 PM 候选建议或 radar，不直接扩大当前任务 scope
   - 如果是稳定架构决策，同步更新 `docs/knowledge/DECISIONS.md`；如果新窗口必须继承，同步更新 `docs/knowledge/PROJECT_WAKEUP.md`
12. **阶段切换门禁检查**：
   - 如果当前阶段是 `Phase 1 - Pet Life MVP`，并且 Identity Editor、Token Food、Relationship Memory、Pet Room、Pet State 的功能与覆盖已经完成，不得直接进入 Phase 2。
   - Phase 1 完成后必须先执行「Phase 1 Exit Gate」：MVP 封版审查、用户视角体验走查、Phase 1.5 体验打磨、商业化/反诱导审查、Phase 2 技术准备。
   - 这些门禁任务必须从 `agent_tasks/BACKLOG.md` 的「Phase 1 Exit Gate」队列进入待分配并按顺序完成。
   - 只有门禁任务全部通过 PM 初审、Reviewer gate、最终验证并更新 `agent_tasks/PHASE_STATUS.md` 后，才能把当前阶段切到 `Phase 2 - Voice & Presence`。
13. 回到步骤 1，分配下一个任务

## Phase 1 Exit Gate Protocol

当 `agent_tasks/PHASE_STATUS.md` 显示 Phase 1 达到 100% 或 Phase 1 核心闭环已经完成时，PM 必须执行以下硬规则：

1. **停止直接派发 Phase 2 功能任务**
   - 不得直接开始 voice deep work、desktop/native presence、3D/VRM、marketplace、billing 或复杂 plugin infrastructure。
   - 除非用户明确要求，否则 Phase 2 只能在 Exit Gate 全部完成后进入。
2. **先做 MVP 封版审查**
   - 运行全量 unit tests、`python3 evals/run_evals.py` 和 `git diff --check`。
   - 从真实用户路径验证：创建/读取宠物、编辑身份、喂食 token food、查看状态变化、记录/读取关系记忆、打开 Pet Room。
   - 更新 README、项目方向文档或 demo 路径时必须保持 scoped commit。
3. **做一次用户视角体验走查**
   - 判断第一屏是否像电子生命体，而不是表单、dashboard 或普通 chatbot。
   - 检查身份、状态、食物、互动、记忆是否形成“这是我的宠物”的闭环。
   - 如果体验不足，先生成 Phase 1.5 打磨任务，不进入 Phase 2。
4. **执行 Phase 1.5 体验打磨**
   - 优先补 Pet Room life-feel、确定性互动、宠物日记/记忆反馈、身份对语气/技能展示的影响。
   - 不引入真正语音、3D/VRM、账号云同步、支付系统或 marketplace。
5. **执行商业化与反诱导审查**
   - Token Food、会员、扩展包可以作为商业模型，但不得出现情绪勒索、孤独压力、隐藏成本或误导购买。
   - 费用、食物余额、动作估算和本地 demo 边界必须清晰。
6. **准备 Phase 2 技术计划**
   - 只规划 Voice Profile v1、TTS 接入边界、Web/PWA presence、桌面浮窗路径和安全/成本边界。
   - Phase 2 任务必须拆成可验证小任务，并带有 no-secret、no-cloning-without-consent、成本透明和用户确认边界。
   - 进入 Phase 2 前必须做 Claude 线程规划：根据任务是否可并行，自动决定继续使用 A/B，还是增开 Claude C/D 等额外 worker 线程。

## Phase 2 Worker Scaling Protocol

Phase 2 开始时，PM 必须先评估开发并行度，再派发任务：

1. **默认至少保留两个 Claude worker**
   - Claude A: Voice/Profile/Presence 的产品功能实现。
   - Claude B: deterministic eval、UI smoke、安全、成本透明和反滥用覆盖。
2. **满足以下条件时自动建议并开启更多 Claude 线程**
   - 存在 3 个以上互不冲突的工作流，例如 Voice Profile、TTS adapter、Web/PWA floating presence、desktop shell、eval/security。
   - 任务触碰文件边界清晰，能避免多个 worker 同时改同一核心文件。
   - 每个新增线程都有独立 task file、DONE file、scope、non-goals、verification 和 no-commit/no-push 规则。
   - 主仓库和现有 worker worktree 已同步，且没有会影响集成的 tracked dirty conflict。
3. **建议线程分工**
   - Claude A: Voice Profile / expression contract / product API。
   - Claude B: evals / safety / no-cloning-without-consent / cost transparency。
   - Claude C: Web/PWA presence / floating pet shell / responsive UI。
   - Claude D: optional TTS adapter or desktop prototype only when the API boundary is already stable.
4. **开新线程前的 PM 动作**
   - 先更新 CCB 配置或 task-file layout，使新 worker 有明确身份和文件边界。
   - 同步所有 worker worktree 到当前 main。
   - 在 `agent_tasks/PHASE_STATUS.md` 记录 Phase 2 active workers、每个线程职责和当前阻塞项。
   - 在 `agent_tasks/BACKLOG.md` 只发布可以独立验证的小任务，不能把多个高冲突功能塞给不同线程同时改。
5. **不得为了“看起来并行”盲目加线程**
   - 如果 Voice/Profile/Presence 仍共享同一核心模块且边界未稳定，先用 A/B 完成架构切分。
   - 新线程必须减少等待时间或风险，而不是增加 PM 集成成本。

## 任务生成流程

当 BACKLOG.md 的「待分配」为空时，PM 应主动生成新任务：

### 第一步：读取项目方向

按顺序读取以下文件，理解当前目标和优先级：

1. `docs/knowledge/PROJECT_WAKEUP.md` — 项目使命和当前状态
2. `docs/knowledge/DECISIONS.md` — 已做的架构决策
3. `docs/knowledge/AGENT_OS_DURABLE_RUNTIME.md` — 北极星架构和优先级列表
4. `docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md` — 框架设计、模块边界、PM 任务契约
5. `agent_tasks/BACKLOG.md`「已完成」部分 — 了解已实现的能力
6. 最近的 git log（`git log --oneline -15`）— 了解最近的代码变更

### 第二步：评估当前状态

运行以下检查，确定项目当前的成熟度：

```bash
# 测试状态
python3 -m unittest discover tests 2>&1 | tail -5

# Eval 状态
python3 evals/run_evals.py 2>&1 | tail -5

# 代码统计
git diff --stat origin/main..HEAD 2>/dev/null
```

### 第三步：生成任务

根据北极星文档的「What To Build Next」优先级列表，结合当前代码状态，生成 1-3 个具体任务。

任务生成原则：
- **跟随北极星和框架架构**：优先推进 `AGENT_OS_DURABLE_RUNTIME.md` 和 `NORA_FRAMEWORK_ARCHITECTURE.md` 中尚未完成的部分
- **标明架构层**：每个任务必须写明对应架构层，例如 Scheduler、Policy Hook Kernel、Trace Graph、Plugin Runtime、Skill Runtime、Capability Router、Context Compiler、Model Router、Eval/Review System、Agent OS Dashboard
- **持续优化架构**：如果任务生成、review、eval 或用户反馈暴露出架构层/模块边界/核心对象/PM 契约的问题，先按 `NORA_FRAMEWORK_ARCHITECTURE.md` 的 Continuous Framework Optimization 规则记录或更新架构，再生成任务
- **增量推进**：每个任务应该是可独立完成的小块工作（1-2 小时可完成）
- **可验证**：每个任务必须有明确的完成标准和验证方式
- **有安全边界**：涉及写入、shell、Git、插件、模型、外部发送、财务/法律/医疗等高风险动作时，必须写明 policy/confirmation/review gate 要求
- **有持久证据**：runtime 行为必须说明写入或查询哪些 event、trace、artifact、state、review gate 或 eval 结果
- **避免重复**：检查「已完成」部分，不要重复已做过的任务
- **发现依赖**：如果任务 A 依赖任务 B，标注「等待 B」

### 第四步：写入 BACKLOG.md

将生成的任务写入 BACKLOG.md 的「待分配」部分，格式：

```markdown
### TASK-XXX: [简短标题]
- 架构层: [Scheduler / Policy Hook Kernel / Trace Graph / ...]
- 优先级: high/medium/low
- 预计: [工作量估计]
- 依赖: [如有]
- 目标: [一句话描述要达成什么]
- 非目标: [本任务明确不做什么，避免 scope creep]
- 安全边界: [no-leak/no-mutation/path safety/policy hook/confirmation/review gate]
- 持久证据: [event/trace/artifact/state/review gate/eval]
- 验证: [如何验证完成]
- 参考: [`docs/knowledge/NORA_FRAMEWORK_ARCHITECTURE.md` 章节、北极星文档章节或代码位置]
```

### 第五步：继续分配

回到循环流程的步骤 3，将任务分配给合适的 agent。

## 分配规则

- Claude A 和 Claude B 可以并行工作
- 如果任务标注「等待 X」，等 X 完成后再分配
- 每次只分配 BACKLOG.md 中优先级最高的任务
- 如果生成任务后仍为空（所有优先级方向都已覆盖），写一条消息告知用户并停止
- 根据任务类型选择 agent：
  - 核心 runtime 功能 → Claude A
  - 测试/eval/质量 → Claude B
  - 两者可并行时同时分配

## PM 初审标准

- 检查 agent 的 completion report 格式是否完整
- 运行测试验证：`python3 -m unittest discover tests`
- 运行 eval 验证：`python3 evals/run_evals.py`
- 如果失败，要求 agent 修复后重新提交
- 初审通过后，转交给 Reviewer 做深度 review

## Reviewer 工作标准

Review 检查清单见 `CLAUDE.md` 的「Reviewer Role」部分。
PM 发送给 reviewer 时应包含：
- 任务编号和标题
- Worker 名称（Claude A/B）
- Completion report 的摘要
- 关键文件的 diff

## 通信格式

分配任务：
```
/ask claude-a 你的任务是 [任务描述]。完成后写 agent_tasks/A_DONE.md 并通知我。
```

审查完成：
```
/ask claude-a 审查通过。BACKLOG.md 已更新，请查看下一个任务。
```

给用户的审查完成汇报必须附带阶段进度：
```
审查完成：[任务/提交/结论]

当前阶段: Phase 1 - Pet Life MVP
Phase 1 进度: xx%
刚完成: ...
正在进行: ...
下一步: ...

阶段总览:
- Phase 1 Pet Life MVP: xx% / 进行中
- Phase 2 Voice & Presence: 0% / 未开始
- Phase 3 Skill Runtime Reframing: 0% / 未开始
- Phase 4 Platform & Marketplace: 0% / 未开始
```

生成任务后通知用户：
```
已根据项目方向生成 N 个新任务：
- TASK-XXX: [标题] (优先级)
- TASK-XXX: [标题] (优先级)
开始分配...
```
