# Nora

Nora 是一个本地优先的个人 AI 助手，用来连接大模型、本地文件、项目代码、终端、浏览器、长期记忆和任务管理。

## 当前能力

- 本地工具：计算、当前时间、保存笔记、读取笔记、读取项目文件、列项目文件、生成任务计划、预览文件 diff、应用单文件或多文件 unified diff patch、写入项目文件、精确替换项目文件文本、安全终端命令执行、列出 Python 模块导入依赖
- 浏览器操作：打开页面、读取标题和正文、等待元素、提取链接/按钮/输入框、生成页面摘要、点击、输入、截图；真实浏览器 backend 使用可选 Playwright
- Toolkits 架构：工具实现拆在 `mini_agent/toolkits/`，`mini_agent/tools.py` 保留兼容导出
- Provider 架构：模型接入位于 `mini_agent/providers/`
- 模型接入：OpenAI-compatible、Anthropic Claude 原生 API、Google Gemini 原生 API
- 模型驱动工具调用：配置 API 后，模型可以自己决定是否调用本地工具
- 工具权限层：每个工具带权限分类；写文件、改文件、执行终端命令会在统一入口要求确认
- 短期会话记忆：当前进程内保留最近对话，退出后清空
- 长期记忆：本地 JSONL 保存可检索记忆
- 多步骤任务状态管理：创建任务、更新步骤、记录步骤总结、查看任务、完成任务，并在推进步骤时提示建议工具类型
- Git 本地工作流：查看 status/diff/log/current branch/local branches/staged diff，汇总变更、审查 staged diff、提交前检查，显式暂存/取消暂存路径，创建本地分支，提交已暂存改动；不提供 push/pull/fetch 等远程写操作
- 测试与诊断：运行白名单 unittest 命令，从失败输出中提取 traceback、断言和文件行号，并支持最多 3 轮的受控修复测试循环
- 受控自主执行：显式 `/auto` 入口，执行前生成计划和确认摘要，有限步数推进目标，每步记录 trace，高风险工具仍需确认
- Python 代码理解：用 AST 查找 class、function、method，生成文件 outline，查看符号签名/上下文，并查找 Name/Attribute 可能引用
- 上下文摘要：本地 JSONL 保存、搜索和列出短中期项目上下文，并拒绝敏感内容
- 上下文窗口管理：模型工具调用链路会自动压缩过长工具结果，只保留头尾和统计信息；完整结果可用 `result_id` 缓存在 `data/tool_results.jsonl` 后分段读取
- 轻量 RAG：按行 chunk 检索项目文本文件，返回 path、line range、score 和 snippet，不依赖向量数据库
- 联网搜索和网页读取：只读 HTTP/HTTPS 页面
- 工具调用日志：记录到 `logs/tool_calls.jsonl`，会脱敏工具参数和敏感结果预览，并可通过工具查看最近日志或生成安全审计摘要
- 后台进程管理：只允许内置 profile 启动本地后台进程，支持查看状态、读取输出、等待输出和停止进程

## 运行

一行安装（macOS / Linux）：

```bash
curl -fsSL https://raw.githubusercontent.com/Z-Jared/nora/main/install.sh | bash
```

一行安装（Windows PowerShell）：

```powershell
irm https://raw.githubusercontent.com/Z-Jared/nora/main/install.ps1 | iex
```

安装后启动 CLI：

```bash
nora
```

启动 HTTP 服务器（含 Web UI）：

```bash
nora-serve
```

浏览器访问 `http://127.0.0.1:8080` 即可使用 Web UI。

### 开发者安装

克隆仓库后本地安装：

```bash
python3 -m pip install --user .
```

或 editable 安装：

```bash
python3 -m pip install -e .
```

也可以直接运行：

```bash
python3 main.py
```

### PATH 配置

如果安装后提示 `nora: command not found`，通常是 Python user scripts 目录没有加入 `PATH`。macOS 系统 Python 常见路径是：

```bash
export PATH="$HOME/Library/Python/3.x/bin:$PATH"
```

其中 `3.x` 替换为你的 Python 版本号（如 `3.11`、`3.12`）。可写入 `~/.zshrc` 后重新加载：

```bash
echo 'export PATH="$HOME/Library/Python/3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

启动后可输入 `/doctor` 检查 workspace、LLM、Git、工具数量和 PATH；如果启动或安装异常，优先运行 `/doctor`。也可以输入 `/help` 查看 CLI 命令。

### 安装后快速验证

安装完成后，按以下步骤确认一切正常：

```bash
# 1. 启动 CLI（应看到 Nora 启动 banner，输入 exit 退出）
nora

# 2. 启动 HTTP 服务器（默认 8080，无需 token）
nora-serve

# 3. 另一个终端验证健康检查
curl http://127.0.0.1:8080/health

# 4. 如需验证 token 认证，先 Ctrl+C 停掉上面的 nora-serve，再用不同端口启动：
NORA_PORT=8081 NORA_API_TOKEN=my-secret nora-serve
curl -H "Authorization: Bearer my-secret" http://127.0.0.1:8081/chat -d '{"message": "hello"}'
```

如果 `nora` 提示 `command not found`，参考上方 PATH 配置。`/health` 无需认证，所有 POST 端点在设置了 `NORA_API_TOKEN` 时需要 `Authorization: Bearer <token>` 头。

可尝试输入：

```text
/doctor
/help
/status
/diff README.md
/staged
/test
/repair 2
/auto 3 总结 README 并说明项目能力
/logs 10
/context 10
/processes
<<<
请分析这段多行输入
并给出建议
>>>
计算 2 + 3 * 4
现在几点
保存笔记 今天学习 agent 架构
读取笔记
读取 README.md
列出项目文件
给“增加文件写入能力”做一个计划
```

## 接入大模型或中转站 API

复制配置模板：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=你的_api_key
LLM_MODEL=gpt-4.1-mini
```

如果使用中转站、OpenRouter、OneAPI、New API、LiteLLM 等兼容 OpenAI API 的服务，只需要替换：

```env
LLM_BASE_URL=https://你的服务地址/v1
LLM_API_KEY=你的中转站_key
LLM_MODEL=服务支持的模型名
```

使用 Anthropic Claude 原生 API：

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=你的_anthropic_key
ANTHROPIC_MODEL=claude-sonnet-4-5
```

Anthropic 和 Gemini 都支持通过 `ANTHROPIC_BASE_URL` / `GEMINI_BASE_URL` 覆盖 API 地址。

使用 Google Gemini 原生 API：

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=你的_gemini_key
GEMINI_MODEL=gemini-2.5-pro
```

OpenAI-compatible 模式也接受 `OPENAI_API_KEY` 作为 `LLM_API_KEY` 的回退。所有 provider 都支持 `LLM_TIMEOUT_SECONDS` 环境变量设置请求超时（默认 60 秒）。

没有配置 key 时，agent 会继续使用本地规则；配置 key 后，本地规则处理不了的问题会交给模型回答。

## agent.yaml 配置

`agent.yaml` 是可选配置文件；不存在时使用默认值。API key 仍放在 `.env`，不要写进 `agent.yaml`。

示例：

```yaml
llm:
  provider: openai-compatible
  base_url: https://api.deepseek.com
  model: deepseek-v4-flash
  timeout_seconds: 60

paths:
  notes: data/notes.txt
  long_term_memory: data/long_term_memory.jsonl
  task_state: data/current_task.json
  task_history: data/task_history.jsonl
  context_summaries: data/context_summaries.jsonl
  tool_logs: logs/tool_calls.jsonl

context_window:
  max_tool_result_chars: 8000
  head_chars: 3000
  tail_chars: 2000

budgets:
  max_tool_calls_per_turn: 8

rag:
  include_paths: []
  exclude_dirs: []
  max_file_bytes: 65536
  chunk_size: 80
  chunk_overlap: 20

safety:
  mode: normal
  allow_autonomous_write: true
  allow_shell_execute: true
  allow_git_write: true
  allow_browser_interact: true

tools:
  disabled: []

permissions:
  deny: []
  confirmation_overrides:
    fetch_url: false
    browser_click: true

processes:
  profiles:
    static_server_8000:
      command: ["python3", "-m", "http.server", "8000"]

system_prompt: 你是一个 Python 专家，帮助用户编写和调试代码。
```

如果要关闭某些工具，把工具名放进 `tools.disabled`，例如 `disabled: ["fetch_url", "browser_click"]`。被禁用的工具不会注册，也不会暴露给模型。
`rag.include_paths` 可限制只检索指定文件或目录，`rag.exclude_dirs` 可额外跳过目录；`chunk_size` 和 `chunk_overlap` 控制按行切分粒度，检索结果会带来源路径、行号范围、分数和片段。
`budgets.max_tool_calls_per_turn` 控制一次普通对话最多允许模型调用多少个工具；超过后本轮会 blocked，并在运行报告里显示已用/上限/剩余。
`safety.mode: strict` 会默认禁用终端执行、测试/修复循环、后台进程、Git 写操作和浏览器点击/输入，并让 `/auto` 隐藏写入、执行、Git、浏览器交互和本地持久化工具；如果确实需要，可以把对应 `allow_*` 设置为 `true`。
如果要彻底禁止某些工具，把工具名放进 `permissions.deny`；如果要覆盖某个工具是否需要确认，可以在 `permissions.confirmation_overrides` 里按工具名设置 `true` 或 `false`。
`system_prompt` 设置自定义系统提示词，会作为每轮对话的第一条 system message 发送给模型；留空则不添加。可用于定义助手的角色、专业领域或回答风格。

启动时会校验 `agent.yaml`，对未知配置键和无效值打印警告（不会阻止启动）。

## 插件系统

在项目根目录创建 `plugins/` 目录，放入 `.py` 文件即可扩展工具。每个插件需导出 `register(registry)` 函数：

> **安全提示：** 插件是受信任的本地代码，启动时会直接执行 `plugins/*.py` 的顶层代码。请只加载你自己编写或审查过的插件，不要加载不受信任来源的插件。

```python
# plugins/my_tool.py
def register(registry):
    registry.register(
        "my_tool",
        "我的自定义工具",
        lambda text: f"结果: {text}",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )
```

以 `_` 开头的文件会被跳过。插件加载失败会打印警告，不影响启动。

CLI slash commands 会绕过 LLM，直接调用已注册工具；写入、测试、Git 写操作和后台进程控制仍会走统一确认。常用命令：

```text
/help                         查看命令帮助
/doctor                       检查运行环境状态
/tools                        查看工具列表
/permissions                  查看工具权限
/status                       查看 Git 状态
/diff [path]                  查看 Git diff
/staged                       查看 staged diff
/changes                      汇总当前 Git 变更
/review-staged                审查 staged diff
/check-commit                 提交前检查
/branch                       查看当前分支
/branches                     列出本地分支
/git-branch-create <name>     创建本地分支，需要确认
/log [n]                      查看最近提交
/symbols [query]              列出 Python 符号
/symbol <name>                查看 Python 符号详情
/refs <name>                  查找 Python 可能引用
/outline <path>               生成 Python 文件 outline
/test                         运行项目测试，需要确认
/repair [n]                   运行受控修复测试循环，需要确认
/auto [n] <goal>              受控自主执行，最多 n 步，高风险工具仍需确认
/task                         查看当前任务
/task-next                    推进当前任务一步
/task-history [n]             查看最近完成的任务历史
/task-search <query>          搜索已完成任务历史
/task-restore <task_id>       从历史恢复任务为当前任务
/logs [n]                     查看工具日志
/audit [n]                    生成工具调用安全审计摘要
/context [n]                  列出上下文摘要
/context-search <query>       搜索上下文摘要
/session-save [name]          保存当前会话
/session-load <name>          恢复已保存的会话
/session-list                 列出已保存的会话
/processes                    列出后台进程
/git-stage <path...>          暂存路径，需要确认
/git-unstage <path...>        取消暂存路径，需要确认
/git-commit <message>         提交 staged 改动，需要确认
/process-start <profile>      启动后台进程，需要确认
/process-stop <process_id>    停止后台进程，需要确认
```

输入 `<<<` 后可进入多行输入，单独一行 `>>>` 结束。

## HTTP API

Nora 也可以作为 HTTP 服务器运行，提供 JSON API 供外部集成：

```bash
nora-serve
# 或指定端口、token 和速率限制
NORA_PORT=9090 NORA_API_TOKEN=my-secret nora-serve
```

端点：

```text
GET  /health              健康检查 + 指标（无需认证）
POST /chat                发送消息 {"message": "..."}
POST /chat/stream         SSE 流式响应（返回 text/event-stream）
POST /chat/clear          清空当前对话记忆（需与其他 POST 一致的 Authorization）
GET  /tools               列出可用工具
GET  /docs                OpenAPI 3.0 API 文档
POST /session/save        保存会话 {"name": "..."}
POST /session/load        恢复会话 {"name": "..."}
GET  /session/list        列出已保存会话
```

设置 `NORA_API_TOKEN` 后，所有 POST 端点需要 `Authorization: Bearer <token>` 头。内置令牌桶速率限制（默认 10 req/s，突发 20）。所有响应带 CORS 头（默认 `*`），支持浏览器直接调用。

示例：

```bash
curl http://localhost:8080/chat -d '{"message": "计算 2 + 3"}'
curl -H "Authorization: Bearer my-secret" http://localhost:8080/chat -d '{"message": "hello"}'
curl http://localhost:8080/chat/stream -d '{"message": "hello"}'  # SSE 流式
```

## Docker 部署

```bash
docker compose up -d
# 或单独构建
docker build -t nora .
docker run -p 8080:8080 --env-file .env -v ./data:/app/data nora
```

`docker-compose.yml` 会自动挂载 `data/`、`logs/`、`plugins/`、`agent.yaml` 和 `.env`。环境变量优先于 `.env` 文件。

配置 key 后，模型也可以调用本地工具。例如：

```text
帮我算一下 2 + 3 * 4
记一下：今天开始做 agent 工具调用
我之前保存了什么笔记？
读取 README.md 并总结
列出项目文件，然后告诉我核心代码在哪
为下一步添加安全命令执行能力做计划
预览创建 docs/idea.md，内容是“下一步做安全命令执行”的 diff
创建 docs/idea.md，内容是“下一步做安全命令执行”
预览把 README.md 里的某句话替换成另一句话
把 README.md 里的某句话替换成另一句话
查看 git 状态
查看当前分支
查看最近 5 个提交
查看 README.md 的 git diff
查看 staged diff
汇总当前 Git 变更
审查 staged diff
提交前检查
查看 ToolRegistry 符号详情
查找 ToolRegistry 的可能引用
生成 mini_agent/registry.py 的 outline
把 README.md 加入暂存区
提交已暂存改动，message 是 update readme
运行测试看看是否通过
运行项目测试并诊断失败
运行最多 2 轮修复测试循环
/auto 3 总结 README 并说明项目能力
查找 Python 符号 ToolRegistry
保存当前上下文摘要：主题是第一阶段，摘要是已加入 Git、测试诊断和符号索引
搜索上下文摘要：第一阶段
用 rg 搜索 write_project_file
读取 README.md 并总结
刚才这个文件主要讲了什么？
搜索项目上下文：tool calling 是在哪里实现的？
搜索 LangGraph 是什么，并给我一个接入建议
读取 https://api-docs.deepseek.com 并总结
记住：我偏好先写测试再实现
搜索长期记忆里的测试偏好
列出长期记忆
删除长期记忆 mem_1
创建一个任务：给 agent 增加一个新工具，步骤是读代码、写测试、实现、运行测试
把任务第 2 步标记为 done，备注是测试已写好，总结是新增测试已通过
查看当前任务
查看最近 10 条工具调用日志
生成最近 50 条工具调用安全审计摘要
列出工具结果缓存
读取工具结果 tr_1
搜索工具结果里的 ToolRegistry
完成当前任务，总结是实现完成并通过测试
执行当前任务下一步
查看工具权限
启动 static_server_8000 后台进程
查看后台进程输出 proc_1
停止后台进程 proc_1
用浏览器打开 https://example.com 并读取页面文本
等待页面里的 #submit 出现
提取当前页面的链接、按钮和输入框
总结当前浏览器页面状态
点击页面里的 button[type=submit]
给 input[name=q] 输入 agent framework
保存当前浏览器截图到 screenshots/page.png
```

执行流程是：

```text
用户输入 -> 模型判断是否需要工具 -> 程序执行工具 -> 工具结果交回模型 -> 模型生成最终回答
```

文件读取工具只允许读取当前项目目录内的 UTF-8 文本文件，并拒绝读取 `.env` 等敏感文件。
文件列表工具不会列出 `.env`、`data/`、`.git/`、`logs/` 等敏感或内部文件。
工具注册表会记录每个工具的权限分类。可以让模型调用 `list_tool_permissions` 查看所有工具权限。
预览文件 diff、预览多文件 patch、Git status/diff/log/current branch/staged diff/变更审查、Python 符号索引和引用查找、测试失败诊断和查看工具日志是只读工具，不会修改项目文件；真正写文件、改文件、应用 patch、Git 本地写操作、运行测试循环、启动/停止后台进程会在统一工具入口要求确认，只有输入 `y` 或 `yes` 才会执行；默认拒绝 `.env`、`data/`、`.git/`、`logs/` 等敏感路径。
Git 工具支持本地 stage/unstage/commit/create branch 和只读提交前审查，但不提供 push、pull、fetch、reset、clean、rebase、stash、删除分支等高风险或远程操作；stage 只能使用显式项目内路径，拒绝 `.env`、`data/`、`logs/`、`.git/` 等敏感路径；如果敏感路径已被外部强制 staged，commit 工具会硬拒绝提交。
多文件 patch 不支持创建、删除或 rename 文件；应用前会全量解析、校验路径和上下文，并在写入失败时尽力回滚已写入文件，但不承诺断电级跨文件原子性。
默认工具注册表中的高风险工具由 `ToolRegistry` 统一确认；`WorkspaceFiles` 和 `ShellRunner` 直接单独使用时仍会自行确认。
终端命令工具同样在统一工具入口需要确认，只允许安全白名单命令：

```text
pwd
ls
find
rg
python3 -m unittest discover -s tests
python3 -m py_compile ...
python3 main.py
```

它会拒绝 `rm`、`sudo`、`chmod`、`git`、`curl`、`wget`、`bash -c`、`sh -c`、管道和重定向等高风险命令。
短期会话记忆只保存在当前进程内，程序退出后清空；包含 API key、`.env` 等敏感标记的内容不会写入记忆。
长期记忆保存在 `data/long_term_memory.jsonl`，支持保存、搜索、列出和按 id 删除；包含 API key、`.env`、`sk-` 等敏感标记的内容会被拒绝保存。
上下文摘要默认保存在 `data/context_summaries.jsonl`，适合记录读过的文件、阶段性判断、测试失败摘要和设计决策；包含 API key、`.env`、`sk-` 等敏感标记的内容会被拒绝保存。
安全审计报告基于已脱敏的 `logs/tool_calls.jsonl` 生成，只统计工具名、状态、高风险类别、敏感路径提示和最近高风险操作摘要，不输出 patch/content/text/API key/secret/token 原文。
模型工具调用链路会压缩过长工具结果，默认保留结果头尾和字符/行数统计，避免大 diff、网页正文、测试输出直接占满模型上下文；如果完整结果不含敏感标记，会缓存到 `data/tool_results.jsonl` 并在压缩内容里返回 `result_id`，模型可用 `list_tool_results`、`read_tool_result`、`search_tool_results` 分段回看；CLI slash commands 仍会直接显示工具返回。
任务状态保存在 `data/current_task.json`。`run_task_once` 每次只选择一个待执行步骤并标记为 `in_progress`，返回当前步骤和建议工具类型，但不会自动执行工具或无限循环；完成步骤后需要调用 `update_task_step` 更新状态，`done` 会建议填写 summary，`blocked` 必须填写 note 或 summary 说明阻塞原因，`list_task` 会突出显示当前 in_progress 步骤；`finish_task` 会把完成后的任务追加到 `data/task_history.jsonl`，可用 `/task-history` 和 `/task-search` 回看，也可用 `/task-restore task_1` 恢复为当前 active 任务继续推进。
受控自主执行只能通过显式 `/auto` 进入，有最大步数硬上限；执行前会生成本地计划和确认摘要，列出最大步数、可用工具数、隐藏工具和仍需确认的高风险工具；每步最多执行一个工具调用，所有工具仍经过 `ToolRegistry` 权限确认和日志记录，取消、拒绝或失败会停止为 blocked，不会绕过 `run_task_once` 的一步一推进语义。
每次普通对话和 `/auto` 结束后，CLI 会附加运行报告，包含状态、步骤数、工具预算、本轮工具调用、失败位置和下一步建议；报告不写入模型记忆，避免污染后续上下文。模型调用高风险工具时必须提供 `reason`，否则会在确认前直接拒绝。
安全模式默认是 `normal`，保持现有行为；`strict` 适合真实项目或不想让模型触碰高风险动作的场景。`allow_autonomous_write: false` 只影响 `/auto` 暴露给模型的工具，不会移除 CLI 手动命令。
受控修复测试循环最多运行 3 轮白名单 unittest 命令，只返回测试摘要、失败诊断和下一步建议；它不会自动生成 patch、不会自动应用 patch、不会自动提交。
后台进程管理只支持内置 profile，例如 `static_server_8000`；不支持任意 shell、不持久化 pid，输出读取和等待都有上限，启动/停止需要确认；后台进程 stdin 会关闭，避免交互式进程抢占当前终端输入。
轻量 RAG 只索引 `.py`、`.md`、`.txt`、`.json`、`.toml`、`.yaml`、`.yml` 等文本文件，并跳过 `.env`、`data/`、`.git/`、`logs/`、`evals/.tmp/`；它按行 chunk 返回 path、line range、score、snippet，排序会综合考虑命中词覆盖、短语、路径和频次，`answer_with_project_context` 会要求模型只基于来源片段回答。
配置中的日志、记忆、任务状态和上下文摘要路径必须位于项目目录内，避免把运行数据写到 workspace 外。
联网工具只执行 GET 请求，不提交表单，不执行网页脚本，并限制返回文本长度；网页读取和浏览器打开只允许公开 HTTP/HTTPS URL，拒绝 localhost、私网、link-local 和解析到内部地址的域名。
浏览器工具的等待元素、读取页面摘要和提取链接/按钮/输入框是只读操作；点击、输入和截图会走统一确认；截图只能保存到项目目录内的非敏感路径。
Playwright 是包的硬依赖（`pip install .` 会自动安装），但 Chromium 浏览器二进制需要单独安装才能使用真实浏览器操作：

```bash
python3 -m playwright install chromium
```

## 项目结构

```text
main.py                         # 兼容 CLI 入口
mini_agent/app.py               # Nora console script 入口
mini_agent/cli.py               # CLI 交互、slash commands 和多行输入
mini_agent/http_server.py       # HTTP JSON API 服务器
mini_agent/controller.py        # agent 主循环和工具调用流程
mini_agent/config.py            # agent.yaml 配置读取
mini_agent/settings.py          # .env 加载和 LLMSettings
mini_agent/registry.py          # 工具注册、权限元数据、统一确认和日志入口
mini_agent/providers/           # OpenAI-compatible、Claude、Gemini 等模型接入
mini_agent/providers/base.py    # LLMClient 协议和 ToolCall 定义
mini_agent/providers/factory.py # Provider 工厂
mini_agent/providers/http.py    # HTTP 工具调用和错误脱敏
mini_agent/providers/openai_compatible.py # OpenAI-compatible 实现
mini_agent/providers/anthropic.py # Anthropic Claude 实现
mini_agent/providers/gemini.py  # Google Gemini 实现
mini_agent/toolkits/            # 本地工具实现
mini_agent/toolkits/basic.py    # 计算、时间、计划
mini_agent/toolkits/browser.py  # 浏览器操作工具和 Playwright backend
mini_agent/toolkits/workspace.py # 项目文件读取、写入、替换、列目录
mini_agent/toolkits/notes.py    # 本地笔记工具
mini_agent/toolkits/registry_builder.py # 默认工具注册
mini_agent/toolkits/register_core.py # 核心工具注册
mini_agent/toolkits/register_developer.py # 开发工具注册
mini_agent/toolkits/register_external.py # 外部/RAG/浏览器工具注册
mini_agent/toolkits/register_git.py # Git 工具注册
mini_agent/toolkits/register_state.py # 状态/任务/记忆工具注册
mini_agent/tools.py             # 兼容导出层，旧 import 仍可用
mini_agent/tools_common.py      # 确认提示和 JSONL 读取公共函数
mini_agent/rag.py               # 项目上下文检索
mini_agent/memory.py            # 短期会话记忆和长期记忆
mini_agent/session.py           # 会话保存/恢复（JSONL 持久化）
mini_agent/plugins.py           # 插件系统：从 plugins/ 动态加载工具
mini_agent/metrics.py           # HTTP 请求指标收集
mini_agent/rate_limit.py        # 令牌桶速率限制
mini_agent/tool_cache.py        # 只读工具结果 LRU 缓存
mini_agent/context_system.py    # 自动上下文注入和不可信参考资料边界
mini_agent/context_summary.py   # 上下文摘要存储和检索
mini_agent/context_window.py    # 工具结果压缩和上下文窗口控制
mini_agent/tool_results.py      # 工具结果缓存和分段读取
mini_agent/task_runner.py       # 多步骤任务状态管理
mini_agent/git_tools.py         # Git 本地 status/diff/log/stage/commit
mini_agent/diagnostics.py       # 测试运行和失败诊断
mini_agent/repair_loop.py       # 受控修复测试循环
mini_agent/process_manager.py   # 后台进程 profile 管理
mini_agent/symbols.py           # Python AST 符号索引
mini_agent/shell.py             # 安全终端命令执行
mini_agent/logs.py              # 工具调用日志和安全审计
mini_agent/web_tools.py         # 联网搜索和网页读取
mini_agent/url_safety.py        # 公开 URL 校验和 SSRF 防护
mini_agent/llm.py               # Provider 兼容导出层
tests/                          # 单元测试
evals/                          # 离线和真实模型 eval
```

## 测试

```bash
python3 -m unittest discover -s tests
```

离线 eval：

```bash
python3 evals/run_evals.py
```

eval 不调用真实模型，覆盖 CLI 命令解析、多行输入、核心工具、安全边界、权限确认、浏览器工具、diff 预览、patch 应用、Git 本地工作流、测试诊断、修复测试循环、后台进程管理、Python 符号索引、上下文摘要、上下文窗口压缩、工具日志查看、RAG 排序、长期记忆、任务执行和 provider factory。

真实模型 eval：

```bash
EVAL_USE_LLM=1 python3 evals/run_evals.py
```

真实模型 eval 使用当前 `.env` 的 provider，额外验证模型是否能正确调用计算、文件读取、diff 预览、工具日志、Git 状态和 staged diff、Python 符号查找、项目测试、修复测试循环、后台进程状态、任务总结和项目上下文检索工具。
