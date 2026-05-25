# Mini Agent

一个从零搭建的小型本地 agent，用来演示 agent 的基本结构：入口、controller、工具注册、工具调用和测试。

## 当前能力

- 本地工具：计算、当前时间、保存笔记、读取笔记、读取项目文件、列项目文件、生成任务计划、写入项目文件、精确替换项目文件文本、安全终端命令执行
- 浏览器操作：打开页面、读取标题和正文、点击、输入、截图；真实浏览器 backend 使用可选 Playwright
- Toolkits 架构：工具实现拆在 `mini_agent/toolkits/`，`mini_agent/tools.py` 保留兼容导出
- Provider 架构：模型接入位于 `mini_agent/providers/`
- 模型接入：OpenAI-compatible、Anthropic Claude 原生 API、Google Gemini 原生 API
- 模型驱动工具调用：配置 API 后，模型可以自己决定是否调用本地工具
- 工具权限层：每个工具带权限分类；写文件、改文件、执行终端命令会在统一入口要求确认
- 短期会话记忆：当前进程内保留最近对话，退出后清空
- 长期记忆：本地 JSONL 保存可检索记忆
- 多步骤任务状态管理：创建任务、更新步骤、查看任务、完成任务
- 轻量 RAG：基于项目文本文件做关键词检索，不依赖向量数据库
- 联网搜索和网页读取：只读 HTTP/HTTPS 页面
- 工具调用日志：记录到 `logs/tool_calls.jsonl`

## 运行

```bash
python3 main.py
```

可尝试输入：

```text
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

使用 Google Gemini 原生 API：

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=你的_gemini_key
GEMINI_MODEL=gemini-2.5-pro
```

没有配置 key 时，agent 会继续使用本地规则；配置 key 后，本地规则处理不了的问题会交给模型回答。

配置 key 后，模型也可以调用本地工具。例如：

```text
帮我算一下 2 + 3 * 4
记一下：今天开始做 agent 工具调用
我之前保存了什么笔记？
读取 README.md 并总结
列出项目文件，然后告诉我核心代码在哪
为下一步添加安全命令执行能力做计划
创建 docs/idea.md，内容是“下一步做安全命令执行”
把 README.md 里的某句话替换成另一句话
运行测试看看是否通过
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
把任务第 2 步标记为 done，备注是测试已写好
查看当前任务
完成当前任务，总结是实现完成并通过测试
执行当前任务下一步
查看工具权限
用浏览器打开 https://example.com 并读取页面文本
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
写文件和改文件工具会在统一工具入口要求确认，只有输入 `y` 或 `yes` 才会执行；默认拒绝 `.env`、`data/`、`.git/` 等敏感路径。
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
任务状态保存在 `data/current_task.json`。`run_task_once` 每次只选择一个待执行步骤并标记为 `in_progress`，不会自动无限执行工具；完成步骤后需要调用 `update_task_step` 更新状态。
轻量 RAG 只索引 `.py`、`.md`、`.txt`、`.json`、`.toml`、`.yaml`、`.yml` 等文本文件，并跳过 `.env`、`data/`、`.git/`、`logs/`。
联网工具只执行 GET 请求，不提交表单，不执行网页脚本，并限制返回文本长度。
浏览器工具只允许打开 HTTP/HTTPS URL；点击和输入会走统一确认；截图只能保存到项目目录内的非敏感路径。
如果要使用真实浏览器操作，需要安装可选依赖：

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## 项目结构

```text
main.py                         # CLI 入口
mini_agent/controller.py        # agent 主循环和工具调用流程
mini_agent/registry.py          # 工具注册、权限元数据、统一确认和日志入口
mini_agent/providers/           # OpenAI-compatible、Claude、Gemini 等模型接入
mini_agent/toolkits/            # 本地工具实现
mini_agent/toolkits/basic.py    # 计算、时间、计划
mini_agent/toolkits/browser.py  # 浏览器操作工具和可选 Playwright backend
mini_agent/toolkits/workspace.py # 项目文件读取、写入、替换、列目录
mini_agent/toolkits/notes.py    # 本地笔记工具
mini_agent/toolkits/registry_builder.py # 默认工具注册
mini_agent/tools.py             # 兼容导出层，旧 import 仍可用
mini_agent/rag.py               # 项目上下文检索
mini_agent/memory.py            # 短期会话记忆和长期记忆
mini_agent/task_runner.py       # 多步骤任务状态管理
mini_agent/shell.py             # 安全终端命令执行
mini_agent/web_tools.py         # 联网搜索和网页读取
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

eval 不调用真实模型，覆盖核心工具、安全边界、权限确认、浏览器工具、RAG、长期记忆、任务执行和 provider factory。

真实模型 eval：

```bash
EVAL_USE_LLM=1 python3 evals/run_evals.py
```

真实模型 eval 使用当前 `.env` 的 provider，额外验证模型是否能正确调用计算、文件读取和项目上下文检索工具。
