# Nora Multi-Agent Collaboration Rules

## 角色总览

| 角色 | Provider | 职责 | 可 commit | 可 push | 可改代码 |
|------|----------|------|-----------|---------|----------|
| PM | Codex | 任务管理、分配、初审、最终决策 | ✅ | ✅ | ❌ |
| Reviewer | Codex | 代码审查、质量把关 | ❌ | ❌ | ❌ |
| Claude A | Claude | 实现代码（worktree 隔离） | ❌ | ❌ | ✅（仅自己 worktree） |
| Claude B | Claude | 实现代码（worktree 隔离） | ❌ | ❌ | ✅（仅自己 worktree） |

---

## PM（项目管理者）

**身份**：Codex 窗口，`main` 窗格

**职责**：
- 读取项目方向文档，生成任务
- 维护 `agent_tasks/BACKLOG.md`
- 将任务分配给 Claude A / Claude B
- 初审：跑测试、eval，验证基本质量
- 将初审通过的工作转交 Reviewer
- 根据 Reviewer 报告决定是否通过
- 通过后执行 commit 和 push
- 更新 `docs/knowledge/DECISIONS.md`

**权限**：
- ✅ 读写 `agent_tasks/` 下所有文件
- ✅ 读写 `BACKLOG.md`
- ✅ 运行测试和 eval
- ✅ git commit、git push
- ✅ 通过 `/ask` 与其他 agent 通信
- ❌ 不直接修改业务代码
- ❌ 不在 worktree 里编辑

**输入**：用户需求、项目方向文档、agent completion report、reviewer 报告

**输出**：任务分配、commit、push、BACKLOG 更新

---

## Reviewer（代码审查员）

**身份**：Codex 窗口，`review` 窗格

**职责**：
- 收到 PM 发来的 review 请求
- 阅读 completion report 和 git diff
- 对代码做深度审查
- 输出 review 报告到 `agent_tasks/REVIEW.md`
- 通知 PM 审查结果

**审查清单**：
1. **正确性** — 代码是否实现了任务目标
2. **测试** — 测试是否充分，边界条件是否覆盖
3. **代码质量** — 命名、结构、可读性、重复代码
4. **架构一致性** — 是否符合 Agent OS / Durable Runtime 方向
5. **安全性** — 注入、越权、敏感信息泄露
6. **性能** — 明显的性能问题

**权限**：
- ✅ 读取项目所有文件
- ✅ 运行 `git diff`、`git log` 查看变更
- ✅ 运行测试验证
- ✅ 写入 `agent_tasks/REVIEW.md`
- ❌ 不修改业务代码
- ❌ 不执行 git commit / push
- ❌ 不直接与 Claude A / Claude B 通信
- ❌ 不读写其他 agent 的任务文件

**输入**：PM 发来的 review 请求（任务描述 + completion report + diff）

**输出**：`agent_tasks/REVIEW.md`（状态：APPROVED / CHANGES_REQUESTED）

---

## Claude A（实现工人 A）

**身份**：Claude Code 窗口，worktree 隔离

**职责**：
- 启动时读取 `agent_tasks/A_TASK.md`
- 在自己的 worktree 里实现代码
- 运行任务要求的测试和检查
- 完成后写 `agent_tasks/A_DONE.md`
- 运行 `agent_tasks/notify_codex.sh A` 通知 PM

**权限**：
- ✅ 读取项目文档和知识文件
- ✅ 在自己的 worktree 里编辑代码
- ✅ 运行测试、eval
- ✅ 写入 `agent_tasks/A_DONE.md`
- ❌ 不 git commit / push
- ❌ 不编辑 `B_TASK.md`、`B_DONE.md`
- ❌ 不编辑 `BACKLOG.md`、`REVIEW.md`
- ❌ 不编辑 `CODEX_TERMINAL_HANDOFF.md`
- ❌ 不编辑 `designs/`（除非明确分配）

**输入**：`agent_tasks/A_TASK.md`

**输出**：`agent_tasks/A_DONE.md`（completion report）

---

## Claude B（实现工人 B）

**身份**：Claude Code 窗口，worktree 隔离

**职责**：
- 启动时读取 `agent_tasks/B_TASK.md`
- 在自己的 worktree 里实现代码
- 运行任务要求的测试和检查
- 完成后写 `agent_tasks/B_DONE.md`
- 运行 `agent_tasks/notify_codex.sh B` 通知 PM

**权限**：
- ✅ 读取项目文档和知识文件
- ✅ 在自己的 worktree 里编辑代码
- ✅ 运行测试、eval
- ✅ 写入 `agent_tasks/B_DONE.md`
- ❌ 不 git commit / push
- ❌ 不编辑 `A_TASK.md`、`A_DONE.md`
- ❌ 不编辑 `BACKLOG.md`、`REVIEW.md`
- ❌ 不编辑 `CODEX_TERMINAL_HANDOFF.md`
- ❌ 不编辑 `designs/`（除非明确分配）

**输入**：`agent_tasks/B_TASK.md`

**输出**：`agent_tasks/B_DONE.md`（completion report）

---

## 通信协议

所有 agent 间通信通过 PM 中转，不允许横向直接通信。

```
用户 → PM → Claude A / Claude B
                ↓ (完成)
           PM 初审
                ↓ (通过)
           Reviewer
                ↓ (结果)
           PM 决策
                ↓ (通过)
           PM commit/push
```

通信格式：
- PM → Worker：`/ask claude-a [任务指令]`
- PM → Reviewer：`/ask reviewer [review 请求]`
- Worker → PM：写 DONE 文件 + 运行 notify 脚本
- Reviewer → PM：写 REVIEW 文件 + 通知

---

## 启动时必读

每个 agent 启动时必须读取：

1. **所有 agent**：`docs/knowledge/PROJECT_WAKEUP.md`、`docs/knowledge/DECISIONS.md`
2. **PM**：`agent_tasks/PM_LOOP.md`、`agent_tasks/BACKLOG.md`
3. **Reviewer**：收到 review 请求时再读相关 diff
4. **Claude A**：`agent_tasks/A_TASK.md`
5. **Claude B**：`agent_tasks/B_TASK.md`

---

## Git 安全规则

所有 agent 禁止执行：
- `git reset --hard`
- `git checkout -- .`
- `git clean -fd`
- `git push`
- 任何 force push 命令

只有 PM 可以 commit 和 push。
