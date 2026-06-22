# Task Backlog

PM 从这里读取待分配的任务。每个任务格式：

## 待分配

### TASK-190A: Nora Code MiMo-inspired terminal wake surface
- 架构层: Nora Code TUI / Terminal UX / Context Compiler / Safety/Policy
- 优先级: high
- 预计: 1 hour
- Worker: Claude A
- 依赖: TASK-189A/B 已完成并集成；`docs/knowledge/NORA_TUI_FRONTEND_CONTRACT.md` 已更新。
- 目标: 参考 MiMo Code 的终端唤醒方式，把 Nora Code TTY 空启动页改成 terminal-native wake surface：居中 `NORA CODE` 标识、底部 docked 输入区、`Code · Nora Auto` 模式行、`tab`/`ctrl+p`/`@`/`/`/`$` 快捷提示，并保持 Claude Code-like 克制。
- 非目标: 不实现真实 subagent dispatch、Goal Judge、Checkpoint 后端、右侧 rail 后端、Pet Room UI、Web UI、provider 配置变更、MCP/LSP 新集成；不改模型调用逻辑；不引入 curses/Textual/Rich 新依赖；不做 dashboard/card-heavy TUI。
- 安全边界: TTY 首屏不得泄漏 API key、raw prompt、hidden reasoning、raw tool payload、raw shell output、环境变量或敏感路径；`@`/`$` 提示只作为 UI 文案，不得触发读取文件或派发 worker；保持 80x24 可用。
- 持久证据: `mini_agent/interactive_cli.py` 的空启动渲染满足 Nora Code wake contract；底部输入仍固定；启动页在用户提交第一条消息后折叠；保留现有 slash/approval/typing 行为。
- 验证: `python3 -m unittest tests.test_cli tests.test_tty_* 2>/dev/null || python3 -m unittest tests.test_cli`; `PYTHONPYCACHEPREFIX=/private/tmp/nora-pycache python3 evals/run_evals.py`; `git diff --check`; targeted TTY replay for 80x24 empty startup, typing, `/` panel, approval panel。
- 参考: `docs/knowledge/NORA_TUI_FRONTEND_CONTRACT.md`; `mini_agent/interactive_cli.py`; MiMo Code screenshots from 2026-06-20 user request。

### TASK-190B: Nora Code TUI deterministic coverage for wake/input shortcuts
- 架构层: Eval/Review System / Nora Code TUI / Safety/Policy
- 优先级: high
- 预计: 1 hour
- Worker: Claude B
- 依赖: TASK-190A；可先并行准备 eval skeleton，但不得改实现文件。
- 目标: 为 TASK-190A 增加 deterministic TTY/eval 覆盖，锁住 MiMo-inspired wake surface、bottom-docked input、mode/status line、shortcut hints、no leak、安全退化和 80x24 可用性。
- 非目标: 不实现 TUI；不修改 `mini_agent/interactive_cli.py`；不新增真实 file picker/subagent dispatch/right rail 后端；不引入外部截图/Playwright/Node/Rich/Textual/curses 依赖。
- 安全边界: 覆盖必须证明 `@`/`$` 只是 UI 唤醒提示而非读取文件/派发 worker；不得要求真实 provider/API key/MCP/LSP；不得记录 raw prompt、API key、hidden reasoning、raw shell output。
- 持久证据: 新增 eval 名称包含 `nora_code_wake` 或 `tui_wake`；覆盖 `NORA CODE`、`Code · Nora Auto`、`/ 命令`、`@ 添加文件`、`$ 子智能体`、`tab 切换模式`、`ctrl+p 设置`、`esc interrupt` active-run hint、80x24 bottom input invariant、no dashboard/card-heavy regression。
- 验证: `PYTHONPYCACHEPREFIX=/private/tmp/nora-pycache python3 evals/run_evals.py`; targeted `python3 -m unittest` for TTY/CLI tests; `git diff --check`。
- 参考: `docs/knowledge/NORA_TUI_FRONTEND_CONTRACT.md`; existing `tty_real_screen_*` evals; current failing/fragile TTY approval fit baseline should be treated carefully and not weakened。

## Phase 1 Exit Gate

这些任务是 Phase 1 完成后的硬门禁。`TASK-167`、`TASK-168`、`TASK-169`、`TASK-170A`、`TASK-170B` 已完成。Phase 1 Exit Gate 已通过；Phase 2 可以从 Voice Profile / Presence 的小任务开始，但必须遵守 `agent_tasks/PM_LOOP.md` 的 Phase 2 Worker Scaling Protocol。

## 进行中

## 已完成
### TASK-189A: Pet Room first-screen pet-first experience ✅
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 438 tests OK；`python3 evals/run_evals.py` 768 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: Web UI 默认视口改为 Pet Room 首屏；`currentView` 默认为 `'pet'`；Pet Room CSS 默认 `display:block`；聊天视图默认隐藏；启动时自动调用 `loadPet()`；新增 3 个 smoke test 锁定首屏标记、CSS 默认值和启动加载行为；修复 `test_add_food_endpoint_normalizes_to_food_added` mock 缺少 pet shape 的预存脆弱性。

### TASK-189B: First-screen pet experience deterministic coverage ✅
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 768 passed, 0 failed, 0 skipped（含 6 个新增 pet_first_screen eval）；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 438 tests OK；`git diff --check` OK。
- 内容: 新增 6 个 deterministic offline eval（`pet_first_screen_markers_present`、`pet_first_screen_local_hero_image`、`pet_first_screen_not_hidden`、`pet_first_screen_modules_wired`、`pet_first_screen_no_scope_drift`、`pet_first_screen_startup_loads_pet`）；锁住首屏标记、本地 hero 图片、非隐藏状态、模块接入、无构建系统/产品范围蔓延、启动路径自动加载 pet。


### TASK-188A: Extract Pet Room Memory Diary native module ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 435 tests OK；`python3 evals/run_evals.py` 762 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 native ES module `mini_agent/static/components/memory-diary.js`，把 Pet Room Today diary rendering、relationship memory list rendering 和 shared moment button wiring 从 `index.html` 拆出；`index.html` 本地导入 `loadTodayDiary()`、`loadRelationshipMemories()`、`wireMemoryDiary()` 并通过注入 `PetAPI` / `handleAuthError` / `showRoomNotice` / `applyReaction` 保留 API/auth/notice/reaction delegation；保留 `pet-today-*`、`today-*`、`pet-memory-*`、`kind`、`mem-summary`、`mem-meta` markers，Today diary empty/activity/memory rendering、relationship memory empty/list rendering、shared moment prompt/request/refresh/notice/reaction/auth failure 行为不变；module 不直接 `fetch`、不包含 `/pet/activity` 或 `/pet/relationship-memory` endpoint literal、不新增 endpoint、外部 URL、build step、真实 audio/recording/provider activation、payment/marketplace、PWA/native 或 3D/VRM/Live2D。

### TASK-188B: Memory Diary module deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 762 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 435 tests OK；`git diff --check` OK。
- 内容: 新增 6 个 `memory_diary_module_*` eval，覆盖 component file existence/native export、本地 module wiring、required Today diary / relationship memory markers、delegated API boundary、safe rendering、shared moment request/refresh contract、无 direct fetch/endpoint literal、无 external URL/build-system/audio/recording/payment/native/PWA/3D scope drift；补强 smoke tests 锁住 module exports、no direct fetch/PetAPI/URL、Today diary activity/memory/empty rendering、relationship memory list/empty rendering、shared moment request body、refresh/notice/reaction callbacks 和 no-pet/empty-summary guards。

### TASK-187A: Extract Pet Room Voice Preview native module ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 421 tests OK；`python3 evals/run_evals.py` 756 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 native ES module `mini_agent/static/components/voice-preview.js`，把 Pet Room text-only voice preview 的 consent check、input validation、button wiring、preview result rendering 和 meta tag rendering 从 `index.html` 拆出；`index.html` 本地导入 `wireVoicePreview()` 并通过注入的 `PetAPI.previewVoice` / `handleAuthError` 保留 API/auth delegation；保留 `speech-bubble-*`、`voice-consent-*`、`speech-preview-*` markers，unchecked consent、empty/over-500 validation、auth failure、preview failure、text-only fallback metadata 行为不变；module 不直接 `fetch`、不包含 `/pet/voice-preview` endpoint literal、不新增 endpoint、外部 URL、build step、真实 audio/recording/provider activation、food debit、payment/marketplace、PWA/native 或 3D/VRM。

### TASK-187B: Voice Preview module deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 756 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 421 tests OK；`git diff --check` OK。
- 内容: 新增 6 个 `voice_preview_module_*` eval，覆盖 component file existence/native export、本地 module wiring、required voice/speech markers、delegated API boundary、consent-before-call、empty/overlong validation、text/meta escaping、no audio/recording/payment/provider/PWA/native/3D scope drift；同步修复 speech bubble 与 voice consent 旧 eval，使其通过 `_read_voice_preview_surface()` 扫描 `index.html` + `voice-preview.js` combined surface，确保抽取后旧契约仍 active/pass。

### TASK-186A: Extract Pet Room Skill Shelf native module ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 411 tests OK；`python3 evals/run_evals.py` 750 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 native ES module `mini_agent/static/components/skill-shelf.js`，把 Pet Room deterministic skill ability shelf 的 `skillCardsFromIdentity()` 和 `renderSkillShelf()` 从 `index.html` 拆出；`index.html` 本地导入 `skillCardsFromIdentity` / `renderSkillShelf` 并保持 `renderPet()` 调用不变；保留 icon mapping、unknown default icon、secret-like filtering、empty/malformed stale cleanup、`pet-skill-shelf`、`pet-skill-list`、`pet-skill-empty`、`pet-skill-card`、`skill-icon`、`skill-name`、`data-skill-count` markers；module 不直接 `fetch`、不引用 `PetAPI` / `petAction`、不调用 `/pet/` endpoint、tool/plugin/runtime，不新增 endpoint、外部 URL、build step、billing/marketplace、真实 voice/audio、PWA/native 或 3D/VRM。

### TASK-186B: Skill Shelf module deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审要求修复旧 TASK-179 eval 扫描范围后通过，reviewer gate 通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 750 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 411 tests OK；`git diff --check` OK。
- 内容: 新增 6 个 `skill_shelf_module_*` eval，覆盖 component file existence/native export、本地 module wiring、required skill markers、read-only/no-tool boundary、secret-like filtering、empty/malformed stale cleanup、no external URL/build-system/payment/marketplace/voice/PWA/native/3D scope drift；同步修复 4 个旧 TASK-179 skill shelf eval，使其通过 `_read_skill_shelf_surface()` 扫描 `index.html` + `skill-shelf.js` combined surface，确保抽取后旧契约仍 active/pass。

### TASK-185A: Extract Pet Room Food Panel native module ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 411 tests OK；`python3 evals/run_evals.py` 744 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 native ES module `mini_agent/static/components/food-panel.js`，把 Pet Room Compute Food/Token Energy panel 的 food stat、balance、cost estimate rendering 和 feed/add-food button wiring 从 `index.html` 拆出；`index.html` 本地导入 `updateFoodPanel()`、`loadCostEstimates()`、`wireFoodButtons()`，在 `renderPet()` 中通过 `loadCostEstimates(pet.pet_id, PetAPI)` 保留 PetAPI delegated boundary；module 不直接 `fetch`、不引用 `PetAPI` literal、不新增 endpoint、外部 URL、build step、billing/marketplace、真实 voice/audio、PWA/native、plugin execution 或 3D/VRM。

### TASK-185B: Food Panel module deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 744 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 411 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 `food_panel_*` eval，覆盖 `food-panel.js` 文件存在和 native export、本地 module wiring、required food markers、delegated `api.getPetFoodStatus` / `petActionFn` boundary、cost action set feed/chat/voice/work、无 direct fetch、无 external URL/build-system/payment/marketplace/manipulative copy 或 product scope drift；补强 smoke tests 锁住 module exports、no fetch/PetAPI/URL、required markers、index import、`renderPet()` delegation、food stat/balance rendering 和 cost estimate API action set。

### TASK-184A: Extract Pet Room Status Chips native module ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 400 tests OK；`python3 evals/run_evals.py` 739 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy/build-system scan 仅命中既有 `index.html` PetAPI/非 pet fetch、测试 mock、eval 负面断言和既有 LLM/example URL。
- 内容: 新增 native ES module `mini_agent/static/components/status-chips.js`，把 Mood/Presence/Energy/Bond chip 文本更新从 `pet-room-canvas.js` 拆成独立 visual/read-only module；`updateStatusChips(state, expr, pres)` 只拥有 `chip-mood-value`、`chip-presence-value`、`chip-energy-value`、`chip-bond-value` 四个 marker，使用 `textContent`，不调用 `fetch`、`PetAPI`、`/pet/` endpoint、voice、food、memory、identity、skill/plugin/runtime；`pet-room-canvas.js` 保留 room name/role 边界并委托 chip 更新；不新增 endpoint、外部 URL、build step、React/Vite/TypeScript/npm、真实 voice/audio、PWA/native、billing/marketplace、plugin execution 或 3D/VRM。

### TASK-184B: Status Chips module deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 739 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 400 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 `status_chips` eval，覆盖 `status-chips.js` 文件存在和 native export、本地 module wiring、`pet-room-status-chip` 与四个 chip value markers 保留、status module read-only/no-fetch/no-PetAPI/no-`/pet/` endpoint/no mutation behavior、无 external URL/build-system/product scope drift；补强 smoke tests 锁住 module exports、no fetch/PetAPI/URL、`textContent`、chip IDs、canvas delegation，以及 `renderPet()` 经 delegation 更新 chip values。

### TASK-183A: Extract Pet Room Canvas native module ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 393 tests OK；`python3 evals/run_evals.py` 734 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy/build-system scan 仅命中既有 `index.html` PetAPI/非 pet fetch、测试 mock、eval 负面断言和既有 LLM 示例 URL。
- 内容: 新增 native ES module `mini_agent/static/components/pet-room-canvas.js`，把 Pet Room 第一屏视觉 canvas 边界拆出为 `updateCanvas()` / `updateChips()`；`index.html` 使用本地 `/static/components/pet-room-canvas.js` import，并在 `renderPet()` 中把 room name、relationship role、Mood/Presence/Energy/Bond chip 更新交给该模块；保留 `pet-room-design-shell`、`pet-room-canvas`、`pet-room-hero-image`、`pet-room-status-chip`、`pet-room-name`、`pet-room-role`、chip markers、本地 `/static/nora-01-hero.jpg` 和 PetAPI API boundary；不新增 endpoint、外部 URL、build step、React/Vite/TypeScript/npm、真实 voice/audio、PWA/native、billing/marketplace、plugin execution 或 3D/VRM。

### TASK-183B: Pet Room Canvas module deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 734 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 393 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 `pet_room_canvas` / `canvas_module` eval，覆盖 component 文件存在和 native export、index 本地 module wiring、required design markers 与 local hero asset path、canvas module read-only/no-fetch/no-PetAPI/no-`/pet/` endpoint/no mutation behavior、无 external URL/build-system/product scope drift；补强 smoke tests 锁住 module exports、index import、no fetch/PetAPI/URL，以及 `renderPet()` 经 canvas module 更新 name/role/chip markers。

### TASK-182A: Extract Pet Room API boundary into native api.js ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 387 tests OK；`python3 evals/run_evals.py` 729 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy/build-system scan 仅命中既有负面断言、既有 LLM/API 示例 URL 和 eval/test 中的安全扫描词。
- 内容: 新增 native ES module `mini_agent/static/api.js`，集中 Pet Room same-origin API wrapper 和 `PET_ENDPOINTS` catalog；`index.html` 使用 `<script type="module">` 从 `/static/api.js` 导入 `PetAPI`，并将 `/pet/current`、`/pet/create`、`/pet/add-food`、`/pet/feed`、`/pet/care`、`/pet/activity`、`/pet/food-status`、`/pet/update-identity`、`/pet/relationship-memory`、`/pet/voice-preview` 调用迁移到 wrapper；保留 auth bearer header、JSON/error handling、DOM markers、CSS links 和现有 UI 行为；不新增 endpoint、外部 URL、build step、React/Vite/TypeScript/npm、真实 voice/audio、PWA/native、billing/marketplace、plugin execution 或 3D/VRM。

### TASK-182B: API boundary deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 729 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 387 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 `api_boundary` / `pet_room_api` eval，覆盖 `api.js` 文件存在、native export/no-build/no-window-global、10 个 Pet Room endpoint path 保留、Authorization bearer header 保留、index 本地 module import wiring、无 external URL/build-system/product scope drift；同步修复 speech bubble 与 voice consent 旧 eval，使 `/pet/voice-preview` endpoint 从 HTML 迁移到 `api.js` 后仍检查 `PetAPI.previewVoice`、`pet_id`、`text` 和 consent-before-call contract；补强 smoke tests 锁住 module import、API exports、endpoint catalog 和 Pet Room fetch calls 使用 `PetAPI` wrapper。

### TASK-181A: Extract Pet Room design tokens and CSS modules ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 381 tests OK；`python3 evals/run_evals.py` 724 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy/build-system scan 仅命中既有负面断言、既有 LLM/API 示例 URL 和 `reaction` 命名中的 `react` 子串。
- 内容: 新增 `mini_agent/static/styles/tokens.css` 和 `mini_agent/static/styles/pet-room.css`，把 Pencil/Pet Room 设计常量和 Pet Room CSS 从 `mini_agent/static/index.html` 的内联 style 中抽出；`index.html` 改为本地 `/static/styles/...` stylesheet links；保留 `pet-room-design-shell`、`pet-room-canvas`、`pet-room-hero-image`、`pet-room-status-chip`、name/role/chip marker 和 `renderPet()` 行为；不新增 build step、React/Vite/TypeScript/npm、endpoint、外部 asset、真实 voice/TTS、PWA/native、billing/marketplace、插件执行或 3D/VRM。

### TASK-181B: Design token and CSS module deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 724 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 381 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 `design_tokens` / `pet_room_css` eval，覆盖 `tokens.css` / `pet-room.css` 存在、Pencil colors 与 radius/action tokens、本地 stylesheet links、Pet Room selector ownership、无 build-system 和产品 scope drift；更新 TASK-180 `pet_room_design_tokens_match_pencil` eval，使 Pencil token 检查在 CSS extraction 后继续扫描 HTML + CSS；新增/补强 smoke tests 锁住 stylesheet links、CSS token usage 和 Pencil 色值定义。

### TASK-180A: Pencil Pet Room design restoration contract and first-pass UI implementation ✅
- 完成者: Claude A；Codex PM 修正静态资产扩展名后集成；reviewer gate 通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 378 tests OK；`python3 evals/run_evals.py` 719 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval/测试断言和既有 LLM setup URL。
- 内容: 新增 `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`，把 `designs/nora_pet_web_ui.pen` 的 `Room canvas` 设为 Pet Room 前端还原源；记录 880 x 850 画布、Pencil 色值、主图资产、字体、status chip、响应式允许偏差和 restore checklist；Web UI 新增 `pet-room-design-shell`、`pet-room-canvas`、`pet-room-hero-image`、`pet-room-status-chip`、`pet-room-name`、`pet-room-role` 等 markers；接入本地 `mini_agent/static/nora-01-hero.jpg` 陶瓷 Nora-01 主视觉，保留 CSS fallback；`renderPet()` 继续保留现有功能并同步更新名字、角色、mood/presence/energy/bond chips；不新增 endpoint、不引入外部图片、真实音频、PWA/native、billing/marketplace、插件执行或 3D/VRM。

### TASK-180B: Pencil design restoration deterministic smoke and safety coverage ✅
- 完成者: Claude B；Codex PM 合并后补强本地 `.jpg` asset existence/reference 断言；reviewer gate 通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 719 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 378 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 `pencil_design` / `pet_room_design` eval，覆盖合同文档存在且引用 Pencil source、Room canvas 尺寸、核心色值、源/静态 asset 路径、required markers；覆盖 Web UI design markers、Pencil tokens、本地 hero asset 存在且无外部图片 URL、无 marketplace/plugin/premium/voice-cloning/recording/microphone/camera/screen/location/PWA/native/3D/VRM scope drift；新增 Pet Room design smoke tests，锁住 design shell、canvas、hero image、status chips、name/role marker、local asset path、CSS fallback 和 `renderPet()` 对设计 marker 的更新。

### TASK-179A: Pet Room deterministic skill ability shelf ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 372 tests OK；`python3 evals/run_evals.py` 714 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: Pet Room 新增 read-only deterministic skill ability shelf，从 bounded `identity.skills` 派生可见能力卡片；新增 `pet-skill-shelf`、`pet-skill-list`、`pet-skill-empty`、`pet-skill-card` 和 `data-skill-count` markers；`skillCardsFromIdentity()` 过滤非字符串、空值、超长、特殊字符和 secret-like skill labels；`renderSkillShelf()` 修复空/ malformed 渲染后 stale card 残留问题；动态 skill label/icon 通过 escaping 后渲染，不执行工具、不新增 endpoint、不写 food/activity/relationship memory。

### TASK-179B: Skill ability shelf deterministic eval and safety coverage ✅
- 完成者: Claude B；Codex PM 初审确认实际 diff 注册 6 个 eval，B_DONE 文本“4 evals”不作为阻塞。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 714 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 372 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: 新增 `pet_skill_shelf_markers_present`、`skill_shelf_mapping_rules`、`skill_shelf_read_only_no_tool_execution`、`skill_shelf_no_marketplace_native_pwa_or_surveillance_copy`、`skill_shelf_no_stale_content_on_empty`、`skill_shelf_rejects_secret_like_skills`；覆盖 skill shelf DOM markers、bounded skill rendering、empty/malformed fallback、stale cleanup、secret-like filtering、read-only/no-tool/no-fetch/no-mutation，以及 no marketplace/plugin/native/PWA/voice/3D scope drift；保留 TASK-178 interaction reaction eval 覆盖。

### TASK-178A: Pet Room deterministic interaction reaction surface ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 356 tests OK；`python3 evals/run_evals.py` 708 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: Pet Room 新增 deterministic interaction reaction surface，在 feed/care/add demo food/shared moment 成功后显示 text-only 即时反应；新增 `pet-room-reaction`、`pet-room-reaction-text`、`pet-room-reaction-meta` 和 `data-reaction` marker；`reactionFromInteraction()` 复用 `clampState()` 从 bounded action/state/result 派生 text/meta，`applyReaction()` 使用 `textContent`；`petAction('/pet/add-food', ...)` 将 `add-food` 规范化为 `food_added` 后再触发 reaction，不新增 endpoint、不额外修改 pet state/food/activity/relationship memory/voice consent。

### TASK-178B: Interaction reaction deterministic eval and safety coverage ✅
- 完成者: Claude B；Codex PM 初审要求补强 add-food integration-path contract 后，Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 708 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 356 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: 新增 `pet_room_reaction_markers_present`、`interaction_reaction_mapping_rules`、`interaction_reaction_read_only_no_extra_fetch`、`interaction_reaction_no_voice_native_pwa_or_surveillance_copy`；覆盖 reaction DOM markers、`petAction` 中 `add-food -> food_added` normalization bridge、mapper action/state/result/fallback 契约、reaction function read-only/no-extra-fetch/no-mutation 边界，以及 no voice/native/PWA/notification/3D/billing/marketplace scope drift。

### TASK-177A: Pet Room deterministic room-load greeting ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 333 tests OK；`python3 evals/run_evals.py` 704 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: Pet Room 新增 deterministic room-load greeting，从 bounded mood/energy/hunger/bond 和 coarse local time bucket 派生 greeting text/meta；新增 `pet-room-greeting`、`pet-room-greeting-text`、`pet-room-greeting-meta` 和 `data-greeting` marker；`roomGreetingFromState()` 复用 `clampState()` 处理 null/undefined/NaN/Infinity/negative/string 等 malformed state，`applyRoomGreeting()` 使用 `textContent`，不调用 provider/network、不修改 pet state/food/activity/relationship memory/voice preview/consent state。

### TASK-177B: Room-load greeting deterministic eval and safety coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 704 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 333 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: 新增 `pet_room_greeting_markers_present`、`room_greeting_state_time_mapping_rules`、`room_greeting_read_only_no_fetch`、`room_greeting_no_voice_native_pwa_or_surveillance_copy`；覆盖 greeting DOM markers、state/time-bucket mapping fallback、function-body read-only/no-fetch/no-mutation/no-surveillance/no-service-worker/no-notification patterns，以及 no voice cloning/recording/native/PWA/marketplace/3D/VRM scope drift。

### TASK-176A: Pet Room CSS-only idle presence signals ✅
- 完成者: Claude A；PM 初审发现 malformed state fallback gap 后要求补强，Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 317 tests OK；`python3 evals/run_evals.py` 700 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: Pet Room robot avatar 新增 CSS-only deterministic idle/presence mapping，从 bounded mood/energy/hunger/bond 映射为 `charging`、`resting`、`alert`、`drifting`、`waiting`；avatar root 暴露 `data-presence` 与 `presence-*` classes；新增 `pet-presence-state`、`pet-presence-icon`、`pet-presence-label`、`pet-presence-detail` markers；`clampState()` 归一化 null/undefined/string/boolean/NaN/Infinity/negative/>100 state values，动态 label/detail 使用 `textContent`，不调用 provider/network、不读麦克风/摄像头/屏幕/位置、不修改 pet state/food/activity/relationship memory/voice preview state。

### TASK-176B: Idle presence deterministic eval and safety coverage ✅
- 完成者: Claude B；PM 初审要求补强 malformed-state coverage 后新增 `presence_state_malformed_state_fallback`，Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 700 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 317 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: 新增/补强 `pet_presence_markers_present`、`presence_state_mapping_rules`、`presence_state_malformed_state_fallback`、`presence_state_read_only_no_fetch`、`presence_state_no_voice_native_or_surveillance_copy`；覆盖 presence markers/classes、bounded state mapping fallback、clamp/coercion/finite/range behavior、function-body read-only/no-fetch/no-mutation/no-service-worker/no-notification patterns，以及 no voice cloning/recording/native/PWA/surveillance/marketplace/3D/VRM scope drift。

### TASK-175A: Pet Room CSS-only expression state mapping ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 297 tests OK；`python3 evals/run_evals.py` 695 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: Pet Room robot avatar 新增 CSS-only deterministic expression mapping，从 mood/energy/hunger 映射为 `hungry`、`sleepy`、`low-energy`、`happy`、`focused`、`calm`；avatar root 暴露 `data-expression` 与 `expression-*` classes；新增 `pet-expression-state`、`pet-expression-icon`、`pet-expression-label`、`pet-expression-detail` markers；动态 label/detail 使用 `textContent`，不调用 provider/network、不读麦克风/摄像头/屏幕/位置、不修改 pet state/food/activity/relationship memory。

### TASK-175B: Expression state deterministic eval and safety coverage ✅
- 完成者: Claude B；PM 初审要求补强弱断言后，4 个 expression eval 在 TASK-175A 合并候选上 active/pass；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 695 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 297 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 安全断言。
- 内容: 新增并补强 `pet_expression_markers_present`、`expression_state_mapping_rules`、`expression_state_read_only_no_fetch`、`expression_state_no_voice_or_surveillance_copy`；覆盖 exact DOM markers/classes、mood/energy/hunger mapping fallback、`expressionFromState`/`applyExpression` function-body read-only/no-fetch/no-mutation/no-surveillance patterns，以及 no voice cloning/recording/background-listening/marketplace/3D/VRM scope drift。

### TASK-174A: Voice preview consent and cost confirmation boundary ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 284 tests OK；`python3 evals/run_evals.py` 691 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面安全断言和 `tts.py` no-audio/no-microphone docstring。
- 内容: `/pet/voice-preview` text fallback response 新增 `requires_user_confirmation`、`confirmation_kind`、`audio_requires_confirmation`、`provider_status`、`food_debit` 等稳定 consent/cost/provider metadata；Pet Room speech bubble 新增 `voice-consent-panel`、`voice-consent-checkbox`、`voice-consent-boundary`、`voice-consent-cost`、`voice-consent-provider` markers；未勾选确认时 UI 显示 bounded consent error 且不 fetch，勾选后仍只展示 text-only fallback 和 no-audio/no-network/no-recording/no-food-debit metadata。

### TASK-174B: Voice consent boundary deterministic eval and safety coverage ✅
- 完成者: Claude B；PM 初审要求补强弱断言后，5 个 voice consent/cost eval 在 TASK-174A 合并候选上 active/pass；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 691 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 284 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面安全断言和 `tts.py` no-audio/no-microphone docstring。
- 内容: 新增/补强 `voice_consent_markers_present`、`voice_consent_unchecked_no_fetch`、`voice_cost_confirmation_metadata`、`voice_cost_confirmation_http_metadata`、`voice_consent_no_recording_or_marketplace_copy`；覆盖 consent DOM markers、unchecked no-fetch control flow、panel/JS metadata、HTTP response metadata、no voice cloning/recording/background-listening/marketplace/payment copy drift。

### TASK-173A: Pet Room speech bubble text fallback surface ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_webui_smoke tests.test_http_server` 281 tests OK；`python3 evals/run_evals.py` 686 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面安全断言。
- 内容: Pet Room 新增 text-only speech bubble surface，包含 `speech-bubble-area`、`speech-bubble`、`speech-bubble-text`、`speech-bubble-meta`、`speech-preview-input`、`speech-preview-btn`、`speech-bubble-error` 等稳定 DOM markers；UI 调用 `/pet/voice-preview`，展示 fallback text、cost/no-audio/no-network/no-recording metadata 和 bounded error；动态文本使用 DOM text API 或 escape helper，不增加真实 TTS、音频、录音、provider/network 调用、food debit、activity 或 relationship-memory mutation。

### TASK-173B: Speech bubble deterministic eval and safety coverage ✅
- 完成者: Claude B；PM 初审要求补强弱断言后，4 个 speech bubble eval 在 TASK-173A 合并候选上 active/pass；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 686 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_webui_smoke tests.test_http_server` 281 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面安全断言。
- 内容: 新增/补强 `speech_bubble` / `voice_preview_ui` deterministic eval，要求全部 speech bubble DOM markers、cost/no-audio/no-provider/no-recording metadata、`speech-bubble-text` fail-closed `textContent` 契约、meta HTML escaping、preview request 包含 `pet_id` 和 `text`，并阻断 voice cloning、recording by default、background listening、marketplace、payment/purchase-pressure copy drift。

### TASK-172A: TTS adapter protocol with text fallback ✅
- 完成者: Claude A；按 PM 初审反馈补上 500 字符 preview 上限并修复 `PetAuthHTTPServerTests` class boundary 后，Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_http_server tests.test_webui_smoke` 274 tests OK；`python3 evals/run_evals.py` 682 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面安全断言和 `tts.py` no-audio docstring。
- 内容: 新增 `mini_agent/tts.py` text-only TTS fallback contract、deterministic `estimate_voice_cost()`、mood context helper 和 `TextFallbackTTSAdapter`；新增只读 `POST /pet/voice-preview`，返回 text fallback、`has_audio: false`、`cost_tokens`、voice profile summary、mood context、no-audio/no-network/no-recording metadata；拒绝 empty/missing/non-string/secret-like/over-500-char preview text，且不回显 secret 或超长文本，不扣 food、不改 state/activity/relationship memory。

### TASK-172B: TTS text fallback deterministic eval and safety coverage ✅
- 完成者: Claude B；按 PM 初审反馈补强 read-only eval，覆盖 activity 和 relationship memory 不变；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 682 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_http_server tests.test_webui_smoke` 274 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面安全断言。
- 内容: 新增 5 个 `tts` deterministic eval，覆盖 text fallback availability、cost metadata transparency、secret rejection/no echo、food/state/activity/relationship-memory read-only boundary，以及 Web UI no recording/background/voice-cloning/payment/marketplace copy；TASK-172A 缺失时 guarded skip，合并后全部 active/pass。

### TASK-171A: Voice Profile v1 contract implementation ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 369 tests OK；`python3 evals/run_evals.py` 677 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 断言；PM recursive probe 通过。
- 内容: 新增 Voice Profile v1 规范化契约，`PetStore.create_pet()` 和 `PetStore.update_identity()` 接受 bounded `voice_profile` 字段：`voice_id`、`speed`、`tone`、`pitch`、`expression_hints`、`speech_style_override`；保留 state/food/activity/relationship memory；递归拒绝 secret-like key/value、audio sample、speaker embedding、clone reference、provider credential 等 unsafe fields；unknown non-secret fields stripped。

### TASK-171B: Voice Profile v1 deterministic eval and safety coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 677 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 369 tests OK；`git diff --check` OK；targeted forbidden-copy scan 仅命中负面 eval 断言。
- 内容: 新增 5 个 `voice_profile` deterministic eval，覆盖 default no-cloning、bounded fields、secret/audio-sample rejection、HTTP create/update contract、Pet Room/Identity Editor no promotional voice/payment/marketplace/background-listening copy；补强 nested dict、list 和 unknown-field secret rejection 覆盖。

### TASK-170A: Phase 2 Voice & Presence product technical plan ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 343 tests OK；`python3 evals/run_evals.py` 672 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted copy scan 仅命中负面边界语句。
- 内容: 在 `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md` 规划 Voice Profile v1 data contract、TTS adapter boundary、Web/PWA presence path、desktop floating pet prerequisites 和 Phase 2 product task candidates；明确不实现 voice/TTS/native/PWA/3D/billing/marketplace。

### TASK-170B: Phase 2 safety, eval, and worker-scaling plan ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 343 tests OK；`python3 evals/run_evals.py` 672 passed, 0 failed, 0 skipped；`git diff --check` OK；targeted copy scan 仅命中负面边界语句。
- 内容: 在 `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md` 规划 no-cloning-without-consent、no-recording-by-default、no-hidden-background-listening、成本透明、presence 隐私边界、deterministic eval/test plan 和 Phase 2 worker scaling；建议 Phase 2 起步继续 A/B，不立即开 C/D。

### TASK-168: Phase 1.5 Pet Room life-feel polish ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 343 tests OK；`python3 evals/run_evals.py` 672 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: Pet Room 新增 deterministic mood summary、identity details、bounded room notice 和 Today diary；Today diary 合并 activity 与 relationship memory，并在记录 shared moment 后即时刷新；新增 6 个 Web UI smoke tests 锁住 DOM markers、mood summary、notice、diary empty/rendered states 和 HTML escaping。

### TASK-169: Commercial model and no-manipulation audit ✅
- 完成者: Claude B；按 PM 初审反馈修复 commercial scan 对审计文档的误报后，Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 343 tests OK；`python3 evals/run_evals.py` 672 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 `docs/knowledge/PHASE_1_COMMERCIAL_NO_MANIPULATION_AUDIT.md`，明确 Token Food 是本地透明 compute energy、会员/扩展包仅为未来选项、Phase 1 无支付/checkout/marketplace/account billing；新增 context-aware `commercial_no_manipulation_scan` eval，扫描 README、Pet Room 和 audit doc，允许负面免责声明但阻断促销、情绪勒索、隐藏成本、voice cloning 和 marketplace pressure 文案。

### TASK-167: Phase 1 MVP release audit ✅
- 完成者: Claude A；Codex PM 初审修正 stale eval 记录和 README demo path 后，CCB reviewer APPROVED。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 337 tests OK；`python3 evals/run_evals.py` 671 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 `docs/knowledge/PHASE_1_MVP_RELEASE_AUDIT.md`，审查 Phase 1 first-use pet loop、Identity Editor、Token Food、care/memory loop、安全/反诱导文案和 README demo path；README 新增 Phase 1 Pet Room 本地体验路径；明确 Phase 1 仍处于 Exit Gate，后续还需 TASK-168、TASK-169、TASK-170，不能直接进入 Phase 2。

### TASK-165: Identity Editor MVP for pet customization ✅
- 完成者: Claude A；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 337 tests OK；`python3 evals/run_evals.py` 671 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 `PetStore.update_identity()`、JSONL identity mutation helper、`POST /pet/update-identity`、`/docs` entry 和 Pet Room Identity Editor；支持更新 name/species/personality_traits/relationship_role/speech_style/voice_profile/taste_profile/skills，保留 pet_id/created_at/state/food/activity/relationship memories，更新 updated_at，拒绝 secret-like identity text，UI invalid JSON 有清晰错误。

### TASK-166: Identity Editor deterministic coverage ✅
- 完成者: Claude B；Codex PM 初审和 reviewer gate 均通过。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 671 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 337 tests OK；`git diff --check` OK。
- 内容: 新增 6 个 deterministic identity editor eval，覆盖 identity update preserves pet_id/created_at/updated_at、state/food balance 不清空、secret input 拒绝、mutation auth、Pet Room editor markers、无 marketplace/voice-cloning/purchase pressure 文案；合并后全部 active/pass。

### TASK-163: Relationship memory MVP for pet shared moments ✅
- 完成者: Claude A；Codex PM 初审确认 relmem API/UI/store 组合通过，唯一 full eval 失败为既有 TTY baseline。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 315 tests OK；`python3 evals/run_evals.py` 664 passed, 1 failed, 0 skipped（`tty_real_screen_startup_bottom_input` 已在 clean HEAD 复现，为既有 baseline）；`git diff --check` OK。
- 内容: 新增 `PetRelationshipMemory`、SQLite/JSONL persistence、`POST /pet/relationship-memory`、`GET /pet/relationship-memory` 和 Pet Room Relationship Memories section；支持 `shared_moment` / `preference` / `task_outcome`，summary/source bounded，importance clamp，secret-like text rejection，mutation auth，HTML escape，recent-first bounded list。

### TASK-164: Relationship memory deterministic coverage ✅
- 完成者: Claude B；按 PM 初审反馈修正 endpoint contract，并收窄 Web UI no-fake-intimacy eval 到 relationship memory 区域。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: 合并 TASK-163 后 7 个 relmem eval 全部 active/pass 且 0 skipped；`python3 evals/run_evals.py` 664 passed, 1 failed, 0 skipped（既有 TTY baseline）；`git diff --check` OK。
- 内容: 新增 7 个 deterministic relationship memory eval，覆盖 supported kinds write/list、limit clamp、response fields、secret rejection/no echo、mutation auth、Pet Room section marker、no fake intimacy/guilt/pressure/hidden purchase copy 和 memory section no secret leak。

### TASK-161: Token food economy estimate and transparent spend loop ✅
- 完成者: Claude A；按 PM 初审反馈修复 unknown action no-echo 安全边界。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 288 tests OK；`python3 evals/run_evals.py` 658 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增只读 `/pet/food-status?pet_id=...&action=feed|chat|voice|work`，返回 balance、cost、can_run、shortfall、reason_label、message；固定本地 MVP 成本 feed=100、chat=25、voice=80、work=150；unknown action 返回 bounded safe error 和 valid_actions，不回显 raw/secret-like input；Pet Room 显示透明 balance 和各 action cost/status，保留 local demo compute food framing，无真实支付或诱导付费。

### TASK-162: Token food economy deterministic coverage ✅
- 完成者: Claude B；按 PM 初审反馈从旧 `/pet/estimate` 改为真实 `/pet/food-status` 契约，并确认组合后 eval 不再 skip。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 658 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 288 tests OK；`git diff --check` OK。
- 内容: 新增 7 个 deterministic token food eval，覆盖 food-status read-only、response shape、固定成本、余额不足 no mutation、unknown action bounded/no-secret、Pet Room balance markers 和 no manipulative copy；TASK-161 缺失时 guarded skip，合并后全部 active/pass。

### TASK-159: Nora-01 robot default identity and living Pet Room redesign ✅
- 完成者: Claude A；Codex PM 集成时先单独提交既有 TTY/CLI baseline 修复，保证主线 eval 重新变绿。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 276 tests OK；合并 TASK-160 后 `python3 evals/run_evals.py` 651 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 默认 `/pet/current` 实例从 `Nora / digital_cat` 调整为 `Nora-01 / robot_pet`，补充 personality、voice profile、taste profile、skills；Web Pet Room 改为模块化 HTML/CSS 机器人电子宠物 avatar，显示 Compute Food / Token Energy、token balance、Life Log，并避免 cat/fox 默认形象和诱导付费文案。

### TASK-160: Nora-01 robot identity/UI deterministic coverage ✅
- 完成者: Claude B；按 PM 初审反馈补强 `nora01_webui_robot_markers`，要求真实 robot avatar DOM/CSS markers 并拒绝 cat/fox markers。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 evals/run_evals.py` 651 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 276 tests OK；`git diff --check` OK。
- 内容: 新增 5 个 deterministic Nora-01 eval：默认 robot identity、bounded identity fields、custom pet create 不强制 robot、Pet Room robot DOM markers、no manipulative monetization copy。

### TASK-157: Pet room MVP and local HTTP pet API ✅
- 完成者: Claude A；Codex PM 集成时保留 `/pet/activity` limit clamp 修复（1..50）和安全类型校验。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: `python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke` 276 tests OK；`python3 evals/run_evals.py` 637 passed, 0 failed, 0 skipped（合并 TASK-158 后）；`git diff --check` OK。
- 内容: 新增 local HTTP pet API：`/pet/current`、`/pet/create`、`/pet/add-food`、`/pet/feed`、`/pet/care`、`/pet/activity`；将 `PetStore` 接入 server；Web UI 新增 Pet Room、宠物状态、喂食/互动/添加 demo food、活动日志；mutation endpoints 继承 HTTP auth，活动日志 HTML escape，API type validation 返回 400。

### TASK-158: Pet room API/UI deterministic coverage ✅
- 完成者: Claude B；Codex PM 手工合入 eval，避免覆盖主仓库既有 TTY eval 改动，并收紧部分断言。
- Reviewer: CCB reviewer APPROVED (`agent_tasks/REVIEW.md`)
- 验证: B 单独 worktree `python3 evals/run_evals.py` 624 passed, 0 failed, 13 skipped；合并 TASK-157 后主仓库 `python3 evals/run_evals.py` 637 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 13 个 deterministic pet HTTP/UI eval，覆盖 current/create/add-food/feed/care/activity/auth/no-secret、Pet Room controls/auth header、activity HTML injection 防护、invalid amount type、invalid identity shape；TASK-157 缺失时安全 skip，合并后全部 active/pass。

### TASK-155: Pet Identity / Pet State deterministic foundation ✅
- 完成者: Claude A；Codex PM 集成时补强 nested `voice_profile`/`taste_profile` secret validation，并将 `voice_profile`、`taste_profile`、`skills` 暴露到 `create_pet` registry tool。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_pets` 51 tests OK；`python3 -m unittest tests.test_pets tests.test_mini_agent` 184 tests OK；`python3 evals/run_evals.py` 633 passed, 0 failed, 0 skipped；`git diff --check` OK。
- 内容: 新增 deterministic `mini_agent.pets` foundation，覆盖 `PetIdentity`、`PetState`、food ledger、activity events、SQLite/JSONL persistence、feed/care transitions、no-negative compute food balance、read tools no-mutation、bounded/no-leak outputs 和 pet registry tools。

### TASK-156: Pet foundation deterministic eval and safety coverage ✅
- 完成者: Claude B；Codex PM 集成时迁移 eval 到 TASK-155 implementation 并确认全部 active/pass。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 633 passed, 0 failed, 0 skipped；`python3 -m unittest tests.test_pets tests.test_mini_agent` 184 tests OK；`git diff --check` OK。
- 内容: 新增 8 个 deterministic pet foundation eval，覆盖 create/get、feed requires balance、ledger no-negative balance、care free state change、registry permissions、read tools no-mutation、sensitive name rejected、activity bounded/no secret leak。

### TASK-153: Nora TTY raw terminal interaction layer v1
- 完成者: Claude A；Codex PM 集成时补强临时 `Working...` TTY status、slash completer eval 和 real `nora` pipe smoke。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 249 tests OK；`python3 evals/run_evals.py` 603 passed；`printf '/model\nexit\n' | python3 -c 'from mini_agent.app import main; main()'` OK；`printf '/model\nexit\n' | nora` OK；`printf '/\nexit\n' | nora` OK；`git diff --check` OK；local package reinstall OK with `prompt_toolkit>=3.0`.
- 内容: 新增 `mini_agent/interactive_cli.py` TTY frontend，TTY stdin/stdout 走 prompt_toolkit `PromptSession`，非 TTY/pipe/tests 继续走 legacy `MiniAgentCLI`；新增 slash command metadata 和 `SlashCompleter`，覆盖 `/`、`/m`、`/mo` → `/model`；TTY 模式使用 bottom toolbar 显示 model/cwd/local-first，抑制 legacy `Working...`/`Done.` 历史噪声并以 carriage-return 临时 status 显示工作中状态；保留 non-TTY legacy lifecycle 和 script compatibility。

### TASK-154: TTY permissions selector and regression coverage
- 完成者: Claude B；Codex PM 集成时接入 TASK-153 的真实 TTY confirmation hook。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 603 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 249 tests OK；`git diff --check` OK。
- 内容: 新增 `PermissionChoice`、`ALLOW_ONCE`、`DENY`、`ALWAYS_ALLOW_SESSION` 和 deny-by-default `selectable_confirm` helper；TTY `InteractiveCLI` 将 `registry.confirm_action` 接到 prompt_toolkit `radiolist_dialog` 的 `Allow once`/`Deny` 选择，非 TTY 继续使用旧 `y/N` fallback；新增 unit/eval 覆盖 slash completion、permission selector wiring、allow/deny labels、denied tool call no-execute 和 no auto-approval。

### TASK-152: Final terminal UX regression eval sweep ✅
- 完成者: Claude B；Codex PM 集成时同步迁移 4 个 durable task/dashboard 旧中文 eval 断言。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 599 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；`git diff --check` OK；`rg -n "===|───|提示:|未知命令|输入 / 查看命令菜单|Nora 已启动|Provider:|Model:|Base URL:|Timeout:|Enabled:|Agent:" mini_agent/cli.py tests/test_cli.py evals/run_evals.py` 仅命中测试/eval forbidden-list 和负断言，`mini_agent/cli.py` 0 命中。
- 内容: 增加 5 个 deterministic terminal UX regression eval，覆盖 startup、status line、slash menu、`/help`、`/wake`、`/model`、`/setup`、`/workers`、`/doctor`、unknown slash、normal/multiline lifecycle 和 full output；锁住 no old panel markers/no old CLI copy/no lifecycle leak/no secret/raw JSON/hidden reasoning leak/compact bounds。

### TASK-151: Final CLI terminal copy consistency sweep ✅
- 完成者: Claude A；Codex PM 集成。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；合并 TASK-152 后 `python3 evals/run_evals.py` 599 passed；`git diff --check` OK；forbidden scan 中 `mini_agent/cli.py` 0 命中。
- 内容: 清理 CLI 用户可见输出残余旧中文/旧配置标签，将 usage、durable task、trace、session、dashboard 等 slash command 文案统一为 compact English；`/wake` 中 `Model:` 收敛为 `model:`；移除 `_section_header()`、`_status_line()` 和 unused `INPUT_SEPARATOR`，不改变模型调用、provider loading、runtime、Web UI 或 worker 语义。

### TASK-150: Error recovery and doctor deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 集成时补强 no-old-recovery-style 断言，锁住 TASK-149 英文 compact 契约。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 594 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；`git diff --check` OK。
- 内容: 为 error recovery、unknown slash 和 `/doctor` 增加 deterministic offline eval，覆盖 401/403/missing-key/timeout/model-not-found/unsupported-provider/rate/quota/port hint、secret no-leak、hint append、unknown slash no model/no lifecycle、doctor llm/provider/data/logs/no secret/no dashboard formatting；PM 补强禁止 `提示:`、`未知命令`、`输入 / 查看命令菜单`、旧中文长提示和旧 doctor suggestions 回归。

### TASK-149: Compact error recovery and doctor surfaces v6 ✅
- 完成者: Claude A；Codex PM 集成。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；合并 TASK-150 后 `python3 evals/run_evals.py` 594 passed；`git diff --check` OK。
- 内容: 将 `_error_recovery_hint()` 从旧中文 `提示:` 长句改为短英文 `hint:`，覆盖 401/403/missing-key/port/timeout/model/provider/rate/quota；unknown slash 改为 `unknown command` + `/`/`/help` guidance；`/doctor` suggestions 改为短英文 bullet；同时将 parse/optional-int 错误文案收敛为 compact English。未改变错误检测语义、模型调用、provider loading、runtime、Web UI 或图标资产。

### TASK-148: /model and /setup compact surface deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 集成时补强旧断言迁移和 no-old-header/no-old-label 覆盖。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 585 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；`git diff --check` OK。
- 内容: 为 `/model` 和 `/setup` compact surface 增加 deterministic offline eval，覆盖 lowercase provider/model/base URL/timeout/enabled labels、Anthropic env hint、multi-provider no secret leak、`/setup` recovery hints、configured setup no key leak、slash commands no `Working...`/`Done.` noise；同步更新旧 `/model`/`/setup` eval 断言，禁止 `=== Nora Setup / Config ===`、`Provider:`/`Model:` 等旧面板文案和旧中文恢复提示回归。

### TASK-147: Compact /model and /setup terminal surfaces v5 ✅
- 完成者: Claude A；Codex PM 集成。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；合并 TASK-148 后 `python3 evals/run_evals.py` 585 passed；`git diff --check` OK。
- 内容: 将 `/model` 收敛为 lowercase compact diagnostics：provider/model/base URL/API-key presence/timeout/enabled 和短恢复提示；将 `/setup` 去掉 `=== Nora Setup / Config ===` 和中文 section header，改为 `current`、`env`、`recovery` 三段 plain-text 配置说明，保留 openai-compatible/anthropic/gemini env 示例与 401/403/timeout/model mismatch/port/rate-limit 恢复提示；不改变 provider loading、model routing、LLM 调用、API key 读取、worker/runtime 或 Web UI 行为。

### TASK-146: Startup header and working indicator deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 集成到主线。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 580 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；`git diff --check` OK。
- 内容: 为 TASK-145 增加 deterministic offline eval，覆盖 `Nora Code` identity、小型 ASCII robot、configured/local model state、workspace path、compact header、normal/multiline `Working...`/`Done.` lifecycle、slash/blank/exit no status noise、no raw prompt/API key/hidden reasoning leak、prompt 保持 `> `；同步更新旧 banner/lifecycle eval 到新的 Claude Code-like 契约。

### TASK-145: Claude Code-like startup header and working indicator ✅
- 完成者: Claude A；Codex PM 集成提交 `7aa3a47`。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 228 tests OK；合并 TASK-146 后 `python3 evals/run_evals.py` 580 passed；`git diff --check` OK。
- 内容: 将 CLI 启动 banner 改成 Claude Code-like 紧凑启动头：左侧小型 Nora ASCII robot，右侧显示 `Nora Code`、模型/本地状态、API-key presence 和当前 workspace 路径；普通 prompt/multiline 模型调用期间显示安全的 `Working...`/`Done.` 状态，不暴露 raw prompt、API key、hidden reasoning 或 raw payload；保留极简 `> ` prompt 和单行 model status，不引入 fullscreen TUI、复杂动画、Web UI redesign 或后端 runtime 语义变更。

### TASK-144: CLI slash surfaces v4 deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 集成后修正旧 eval 断言并补强 no-panel/no-secret/no-lifecycle 覆盖。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 568 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 227 tests OK；`git diff --check` OK。
- 内容: 为 `/`、`/help`、`/wake`、`/model`、`/workers` 增加 deterministic offline eval，覆盖 v4 compact/plain-text surface、required commands、no `===`/`───`/旧中文面板标题、no raw JSON、no model-call lifecycle、no API key/raw prompt/hidden reasoning/raw file content leak、missing `.ccb/` one-line recovery、ready-for-PM-review worker detection；同步更新旧 CLI slash eval 到 v4 契约。

### TASK-143: CLI slash surfaces v4 ✅
- 完成者: Claude A；Codex PM 手动集成并补充 `/model` 短恢复提示、非 git `/wake` fatal 输出过滤。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 227 tests OK；`git diff --check` OK；合并 TASK-144 后 `python3 evals/run_evals.py` 568 passed。
- 内容: 将 `/`、`/help`、`/wake`、`/model`、`/workers` 收敛为短、单调、plain-text slash surfaces：`/` 改为紧凑 command list；`/help` 改为 concise command index；`/wake` 去掉 section bars 并保留 workspace/branch/model/knowledge/task/worker/recovery 摘要；`/model` 去掉 panel header 并保留 provider/model/base URL/API-key presence/enabled/401/model-mismatch hints；`/workers` 改为 A/B one-line summaries 和 missing `.ccb/` one-line recovery；不改变 Web UI、图标/favicon、模型路由、worker runtime 或 Git/tool/durable command 语义。

### TASK-142: CLI default terminal surface v3 deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 清理 dead `INPUT_SEPARATOR` import 并补强 no heavy separator 断言。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 561 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 227 tests OK；`git diff --check` OK。
- 内容: 更新旧 CLI v2 eval 断言以匹配 TASK-141 v3 surface：普通回复无 `Agent:` 前缀、lifecycle 为 `received`/`thinking`/`ready`、默认 input hint 为单行 `model: ... | local-first | / for commands` 且无重 separator；覆盖 slash/blank/exit no lifecycle noise、no intelligence/speed/routing、no API key/raw prompt/hidden reasoning/raw payload leak，以及 `/auto` 输出兼容。

### TASK-141: CLI default terminal surface v3 ✅
- 完成者: Claude A；Codex PM 手动集成到主线。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 227 tests OK；`git diff --check` OK；合并 TASK-142 后 `python3 evals/run_evals.py` 561 passed。
- 内容: 将 Nora 默认终端继续收敛到 Claude Code-like 纯文本表面：保留 `> ` prompt；将重 footer/separator 改为单行 `model: ... | local-first | / for commands`；普通模型回复不再加 `Agent:` 标签；lifecycle 压缩为 `received`、`thinking`、`ready`；slash/blank/exit 保持无 lifecycle 噪声；不改变 Web UI、模型路由、worker/runtime 后端语义或图标/favicon 资产。

### TASK-140: CLI UI v2 deterministic eval coverage ✅
- 完成者: Codex PM 直接完成 eval-only patch；Claude B worktree 未包含 PM 主仓库中未提交的 TASK-139 集成，因此 B 报告 blocked。
- Reviewer: Codex PM APPROVED
- 验证: `python3 evals/run_evals.py` 560 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 226 tests OK；`git diff --check` OK。
- 内容: 更新旧 banner eval 断言以匹配 CLI UI v2 compact surface，新增 minimal `> ` prompt 和 `model: ... | local-first | / for commands` input status line eval，覆盖 no old section headers、local-only `API key: not used`、无 task panel、worker compact summary、no intelligence/speed/routing/no secret leak，以及 slash/lifecycle/plain-text compatibility。

### TASK-139: CLI UI v2 lightweight terminal surface ✅
- 完成者: Claude A；Codex PM 手动集成并补充 disabled/no-settings `API key: not used` 断言。
- Reviewer: Codex PM APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 226 tests OK；`git diff --check` OK；`python3 evals/run_evals.py` 仍有 6 个旧 banner eval 断言失败，留给 TASK-140 更新。
- 内容: 默认 CLI prompt 改为极简 `> `；启动 banner 压缩为轻量 workspace/branch/LLM/API-key/tools/worker/commands surface；新增单行 input status `model: ... | local-first | / for commands`；保留 slash/blank/exit 无 lifecycle 噪声、无 fullscreen TUI、无 dashboard、无 intelligence/speed/routing 默认展示。

### TASK-138: Minimal model routing deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 修正完成报告中的 eval 数量（实际为 21 个）。
- Reviewer: Codex PM (`agent_tasks/REVIEW_TASK_138.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 558 passed；`python3 -m unittest tests.test_model_router tests.test_config tests.test_mini_agent` 178 tests OK；`git diff --check` OK。
- 内容: 为 `inspect_model_routing` 增加 21 个 deterministic offline eval，覆盖 openai-compatible/anthropic/gemini 默认路由、unsupported provider bounded no-echo、missing key disabled route、task/risk/long-context/tool/review hints、invalid context tokens、raw prompt/API key no-leak、capability metadata、registry `local/read` permission、registry no durable task/worker/event mutation、settings injection、no-settings safe error、provider factory compatibility、unknown task/risk defaults 和 stable fallback provider；无 runtime 变更。

### TASK-137: Minimal model routing inspection scaffold v1 ✅
- 完成者: Claude A；Codex PM 手动集成并修正 registry settings 注入、unsupported provider bounded no-echo、fallback provider deterministic ordering 和 temp DB no-mutation test。
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_model_router tests.test_config tests.test_mini_agent` 178 tests OK；`python3 evals/run_evals.py` 537 passed；`git diff --check` OK。
- 内容: 新增只读 `mini_agent/model_router.py` 和 registry tool `inspect_model_routing`，以当前注入的 `LLMSettings` 返回 selected provider/model、policy version、route type、normalized task/risk hints、reason labels、capability hints、fallback provider 和 disabled/unsupported 状态；不调用网络、不创建 LLM client、不 mutation durable task/worker/event/file/memory，不泄漏 API key、raw prompt/task goal、unsupported provider 原文或 secret-like model/provider 值；注册权限为 `ToolPermission(category="local", risk="read")`。

### TASK-136: CLI terminal UI polish deterministic eval coverage ✅
- 完成者: Codex PM 直接完成 eval-only patch；Claude B CCB worktree 因 stale TASK-134 残留未继续使用
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 537 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 225 tests OK；`git diff --check` OK。
- 内容: 为 TASK-135 terminal UI polish 增加 9 个 deterministic offline eval，覆盖启动 landing panel 固定分区、task/worker section、missing/configured key no-leak、normal/multiline exact lifecycle order、slash/blank/exit no lifecycle noise、`/`/`/setup`/`/model`/`/workers`/`/help` plain-text no raw JSON、`API key`/`401 Unauthorized`/`provider/model 不匹配` recovery guidance，以及 lifecycle lines 不泄漏 raw prompt/API key/hidden reasoning/raw payload。

### TASK-135: CLI terminal UI polish v3 ✅
- 完成者: Claude A；Codex PM 手动集成并修正 deterministic 输出和测试契约
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_cli` 79 tests OK；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 225 tests OK；`python3 evals/run_evals.py` 528 passed；`git diff --check` OK。
- 内容: 启动 banner 变成 compact terminal landing panel，包含 `Status`、`Workspace`、`Model`、`Tools`、可选 `Tasks`/`Workers`、`Next` 分区，同时保留 `exit/quit`、workspace、branch、LLM/API-key state、tools count、任务和 worker 摘要；普通 prompt/multiline 增加 deterministic 三段 lifecycle feedback（已接收输入/正在调用模型/模型响应完成）；slash/blank/exit 无 lifecycle 噪声；`/wake`、`/model`、`/setup`、`/workers` 可读性 polish；无 heavy TUI、streaming、hidden reasoning 或 backend runtime 语义变更。

### TASK-134: CLI slash launcher/welcome deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 补强 next-action 精确断言和 configured-key eval 的 tempdir `.env` 隔离
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 528 passed；`python3 -m unittest tests.test_cli` 79 tests OK；`git diff --check -- evals/run_evals.py` OK。
- 内容: 为 TASK-133 CLI slash launcher/welcome 增加 10 个 deterministic offline eval，覆盖 exact `/` menu 结构、必备命令、no model-call/no status noise、no raw JSON、banner next-action hint、核心信息保留、missing/configured key 安全、hidden reasoning marker absence、secret/raw JSON leak prevention；无 runtime 行为变更。

### TASK-133: CLI slash launcher and welcome polish v2 ✅
- 完成者: Claude A；Codex PM 因 A CCB worktree 落后在 `edca78e`，手动移植并修正 TASK-133 增量到当前主线，保留 `/setup` 和 TASK-131/TASK-132 已集成表面
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_cli` 79 tests OK；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 225 tests OK；`python3 evals/run_evals.py` 518 passed；`git diff --check -- mini_agent/cli.py tests/test_cli.py` OK。
- 内容: 新增 exact `/` slash launcher/menu，按 Start/Project/Workers/Memory/Diagnostics/Help 分组展示常用命令并包含 `/setup`；启动 banner 增加 `/`、`/wake`、`/setup` next-action hint，同时保留 workspace/branch/model/key/tools/tasks/workers 信息；`/` 不调用模型、不输出状态噪声、不产生 raw JSON；新增 focused CLI unit tests。

### TASK-132: CLI setup/status UX deterministic eval coverage ✅
- 完成者: Claude B；Codex PM 补强 missing-key 断言并修正完成报告
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 518 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 220 tests OK；`git diff --check` OK。
- 内容: 为 TASK-131 CLI setup/status UX 增加 10 个 deterministic offline eval，覆盖 `/setup` provider/model/base URL/API-key presence、openai-compatible/anthropic/gemini env keys、安全 placeholder/no secret leak、401/missing-key/provider-model mismatch guidance、`/config` alias、普通 prompt 状态输出、slash/blank/exit 无状态噪声、hidden reasoning/no raw JSON/no API key leak；无 runtime 行为变更。

### TASK-131: CLI setup/config and response-status UX v1 ✅
- 完成者: Claude A；Codex PM 因 A CCB worktree 落后在 `67a1145`，手动移植 TASK-131 增量到当前主线，避免带入已合并的 TASK-129 旧 diff
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_cli` 74 tests OK；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 220 tests OK；`python3 evals/run_evals.py` 508 passed；`git diff --check` OK。
- 内容: 新增只读 `/setup` 与 `/config` alias，展示 provider/model/base URL/API key presence、openai-compatible/anthropic/gemini 安全 `.env` 键示例和 missing-key/401/provider-model mismatch 等配置恢复提示；普通 prompt 与 multiline 在 `agent.run(...)` 前后输出 deterministic 状态行，让 CLI 有模型调用反馈；slash/blank/exit 不输出状态噪声；不泄漏 API key、token 或 hidden reasoning。

### TASK-130: CLI UX smoke/eval coverage ✅
- 完成者: Claude B；按 PM 反馈在 TASK-129 合入后重做 eval，覆盖真实 `/wake`、`/model`、`/workers` CLI 表面
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 508 passed；`python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 207 tests OK；`git diff --check` OK。
- 内容: 为 TASK-129 CLI workbench UX 增加 11 个 deterministic offline eval，覆盖启动页 no-model/key-missing/common commands、configured provider/model no secret leak、worker DONE summary、`/wake` 项目面板与非项目恢复提示、`/model` provider/model/base URL/key-safe diagnostics、`/workers` A/B task/DONE/PM inbox 状态、401 recovery hint 自动附加，以及 CLI 输出保持 Markdown/plain-text、无 raw JSON；无 runtime 行为变更。

### TASK-129: CLI wake/setup/status UX v1 ✅
- 完成者: Claude A；按 PM 初审反馈修复启动页 worker DONE 文件识别 bug 并补回归测试
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_cli tests.test_config tests.test_mini_agent` 207 tests OK；`python3 evals/run_evals.py` 497 passed；`git diff --check` OK；PM 手动 probe 确认 banner 可识别 `.ccb/workspaces/claude-a/agent_tasks/A_DONE.md`。
- 内容: 改善 Nora CLI workbench 入口体验，新增 `/wake` 项目唤醒面板、`/model` 模型配置/密钥状态诊断、`/workers` CCB worker 状态面板；启动页新增 workspace、branch、provider/model、API key presence、task/backlog summary、worker summary 和常用命令；agent 响应自动附加常见 provider/config 错误恢复提示；不泄漏 API key 或 secret；保持 deterministic/offline tests。

### TASK-128: Deterministic eval coverage for context compiler local skill catalog bridge v1 ✅
- 完成者: Claude B；按 PM 初审反馈移除弱断言并补强 read-only / registry root-binding 覆盖
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 497 passed；`python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent` 333 tests OK；`git diff --check` OK。
- 内容: 为 TASK-127 `compile_context_pack` local skill catalog bridge 增加 10 个 deterministic offline eval，覆盖 direct compiler 和 registry 路径的有效文件、目录发现与 deterministic ordering、registry `workspace/read` permission、manual + local manifest 合并、traversal/absolute/hidden/denied path safety、malformed `skill_manifest_paths` bounded diagnostics/no raw echo、secret/file/path no-leak、durable task/worker/event read-only no-mutation、workspace-root-bound discovery，以及 existing manual manifest、git status、knowledge excerpt、discover/preview/permission surfaces compatibility；无 runtime 行为变更。

### TASK-127: Context compiler local skill catalog bridge v1 ✅
- 完成者: Claude A；按 PM 初审反馈补强 discovery diagnostics sanitization 和 malformed `skill_manifest_paths` bounded error
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent` 333 tests OK；`python3 evals/run_evals.py` 487 passed；`git diff --check` OK；PM 手动 probe 确认 hidden/missing/malformed `skill_manifest_paths` 不泄漏原始路径或输入。
- 内容: 扩展 `ContextCompiler.compile(...)` 和 registry `compile_context_pack`，支持项目相对 `skill_manifest_paths` 自动发现本地 skill manifests 并生成 bounded/untrusted `Skill Context Preview`；桥接复用 TASK-125 `discover_local_skill_manifests_json(...)` 和既有 `preview_skill_context_json(...)`；支持 JSON string/list path input、manual `skill_manifest_jsons` 与 local manifests 组合、context budget、registry schema 暴露；diagnostics 只输出 coarse reason，不回显 raw hidden/missing/unsafe path 或 malformed JSON string；保持只读、不加载/安装/执行 skill 内容、不 mutation durable state。

### TASK-126: Deterministic eval coverage for local skill manifest catalog discovery v1 ✅
- 完成者: Claude B；Codex PM 补强 registry root binding eval
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 487 passed；`python3 -m unittest tests.test_skills tests.test_mini_agent` 273 tests OK；`git diff --check` OK。
- 内容: 为 TASK-125 `discover_local_skill_manifests` 增加 10 个 deterministic offline eval，覆盖 exact `workspace/read` permission、有效 manifest 文件发现、目录递归与路径排序、`max_files` / `max_file_bytes` / non-JSON 边界、traversal/absolute/hidden/denied path safety、registry workspace root binding、malformed JSON/invalid manifest/unsupported input、secret no-leak、durable task/worker/event read-only no-mutation，以及 inspect/summarize/preview/route/context compiler/list_tool_permissions compatibility。

### TASK-125: Local skill manifest catalog discovery v1 ✅
- 完成者: Claude A；Claude B eval 发现 denied directory direct path bug；Codex PM 补强 hidden/denied parent path check 与 registry root binding
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_skills tests.test_mini_agent` 273 tests OK；`python3 evals/run_evals.py` 487 passed；`git diff --check` OK。
- 内容: 新增只读 `discover_local_skill_manifests` / registry `discover_local_skill_manifests` surface，从 workspace-bound 项目相对路径发现 skill manifest metadata；支持文件/目录输入、稳定排序、最多 50 个 manifest、单文件 64KB、递归深度限制、跳过 hidden/denied directories 和 non-JSON 文件；拒绝 traversal、absolute、unsafe char、secret-like path；复用 skill manifest parser/safe dict/aggregate summary，不加载、不安装、不执行 skill 内容，不 mutation durable state；registry 工具权限为 `ToolPermission(category="workspace", risk="read")`，并忽略调用方传入的 `project_root`。

### TASK-124: Deterministic eval coverage for skill context preview v1 ✅
- 完成者: Claude B
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 477 passed；`python3 -m unittest tests.test_skills tests.test_mini_agent` 242 tests OK；合并后 `python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent` 287 tests OK；`git diff --check` OK。
- 内容: 为 `preview_skill_context` / registry `preview_skill_context` 增加 9 个 deterministic offline eval，覆盖 exact `local/read` permission、有效 skill context preview、stable ordering、`max_skills` 默认/显式/high/zero/negative/bad bounds、malformed outer/non-list/unsupported/individual input、大输入 scan cap、secret no-leak、durable task/worker/event read-only no-mutation，以及 inspect/summarize/route/list_tool_permissions compatibility；无 runtime 变更。

### TASK-123: Skill context compiler preview bridge v1 ✅
- 完成者: Claude A；Codex PM 补强 JSON string/list input 兼容
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_context_compiler tests.test_skills tests.test_mini_agent` 287 tests OK；`python3 evals/run_evals.py` 477 passed；`git diff --check` OK。
- 内容: 扩展 `ContextCompiler.compile(...)` 和 registry `compile_context_pack`，允许 context pack 可选包含 bounded/untrusted `Skill Context Preview` section；桥接复用 TASK-121 `preview_skill_context_json(...)`，只使用 skill manifest metadata，不加载/安装/执行 skill 内容，不外呼，不 mutation durable task/worker/event/memory/trace；支持 list 或 JSON string manifest input、`skill_context_max_skills`、普通 context budget/truncation、safe malformed error section 和 secret-like no-leak。

### TASK-121: Skill context preview surface v1 ✅
- 完成者: Claude A；按 PM 初审反馈修复 malformed/non-list JSON 静默返回、输入扫描无界、bad `max_skills` 抛错/静默 fallback 三类问题。
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_skills tests.test_context_memory tests.test_mini_agent` 284 tests OK；`python3 evals/run_evals.py` 459 passed；`git diff --check` OK；PM bad `max_skills` no-leak/warning probe OK。
- 内容: 新增只读 `preview_skill_context` / registry `preview_skill_context` surface，根据用户 goal 和 skill manifest metadata 选择相关 skill 并返回 bounded/untrusted context hints；输出包含 matched domains/capabilities、workflows、deliverables、required_plugins、risk_boundaries、evals 和 untrusted framing；不加载、不安装、不执行 skill 内容，不 mutation durable task/worker/event；支持 input scan cap 50、`max_skills` 1-20 clamp、bad `max_skills` bounded warning、malformed input safe errors、secret-like no-leak，并保持 inspect/summarize/route compatibility。

### TASK-122: Deterministic eval coverage for skill manifest catalog summary v1 ✅
- 完成者: Claude B；按 PM 初审反馈修复 high-clamp eval，使 `max_skills=999` 使用 60 个 manifests 并断言 clamp 到 50。
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 468 passed；`python3 -m unittest tests.test_skills tests.test_mini_agent` 200 tests OK；`git diff --check` OK。
- 内容: 为 `summarize_skill_manifests` / registry `summarize_skill_manifests` 增加 9 个 deterministic offline eval，覆盖 exact local/read permission、有效 catalog summary、sorted/deduplicated aggregates、default/explicit/high/zero/negative bounds、malformed outer/individual/non-list input bounded errors、secret no-leak、durable task/worker/event read-only no-mutation，以及 inspect/route/list_tool_permissions compatibility；无 runtime 变更。

### TASK-120: Deterministic eval coverage for skill-aware capability routing v1 ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 459 passed；`python3 -m unittest tests.test_plugins tests.test_skills tests.test_mini_agent` 265 tests OK；`git diff --check` OK。
- 内容: 为 TASK-117 的 `skill_manifest_jsons` skill-aware routing path 增加 9 个 deterministic offline eval，覆盖 skill-only routing、combined skill+plugin routing、`required_plugins` / `risk_boundaries` 聚合与排序去重、high-risk boundary 风险提升、malformed outer/individual skill JSON、secret no-leak、durable task/worker/event read-only no-mutation，以及 plugin-only compatibility；无 runtime 变更。

### TASK-119: Skill manifest catalog summary v1 ✅
- 完成者: Claude A；按 PM 初审反馈修复 registry `max_skills` 参数未传递问题
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_skills tests.test_mini_agent` 200 tests OK；`python3 evals/run_evals.py` 450 passed；`git diff --check` OK。
- 内容: 新增只读 `summarize_skill_manifests` surface 和 registry tool，汇总一组 skill manifest metadata；返回 bounded `skills` 列表、valid/invalid counts、domains/capabilities/workflows/deliverables/required_plugins/risk_boundaries/evals 聚合、warnings/errors；支持 JSON string 或 dict manifest、`max_skills` 1-50 clamp、secret-like no-leak、malformed input bounded safe errors，并保持 `ToolPermission(category="local", risk="read")` 与 inspect compatibility。

### TASK-118: Deterministic eval coverage for skill and capability manifest surfaces v1 ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 450 passed；`python3 -m unittest tests.test_plugins tests.test_skills tests.test_mini_agent` 242 tests OK；`git diff --check` OK。
- 内容: 为 `inspect_skill_manifest` 和 `route_capability_request` 增加 14 个 deterministic offline eval，覆盖 exact local/read permission、有效 bounded output、malformed JSON / non-object / invalid list fields safe errors/warnings、secret-like no-leak、durable task/worker/event read-only no-mutation，以及 plugin/skill/routing/MCP/list_tool_permissions compatibility；无 runtime 变更。

### TASK-117: Skill-aware capability routing bridge v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_plugins tests.test_skills tests.test_mini_agent` 265 tests OK；`python3 evals/run_evals.py` 436 passed；`git diff --check` OK；PM combined skill+plugin no-leak / permission / no-mutation probe OK。
- 内容: 扩展只读 `route_capability_request`，支持 `skill_manifest_jsons` 与 `plugin_manifest_jsons` 共同路由；新增候选 skill 输出、top-level `required_plugins` / `risk_boundaries` 聚合、skill deliverables 合并和高风险边界风险提升；保持 plugin-only backwards compatibility；registry 工具增加 `skill_manifest_jsons` 参数，权限仍为 `ToolPermission(category="local", risk="read")`。

### TASK-116: Skill manifest schema and inspection v1 ✅
- 完成者: Claude B；按 PM 初审反馈补强 secret-like `version` no-leak 和 registry permission assertion
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_skills tests.test_mini_agent` 166 tests OK；`python3 evals/run_evals.py` 436 passed；`git diff --check` OK；PM sentinel no-leak / no-mutation probe OK。
- 内容: 新增 `mini_agent/skills.py` skill manifest v1 dataclass、JSON/dict parser、validation result、safe inspection output 和 registry read-only 工具 `inspect_skill_manifest`；覆盖 required identity、bounded strings/lists、unknown field warnings、secret-like name/version/description/list item redaction、direct + registry no-leak、durable task/worker/event read-only no-mutation，以及 exact `ToolPermission(category="local", risk="read")`。

### TASK-115: Capability router scaffold v1 ✅
- 完成者: Claude A；按 PM 初审反馈补强 secret-like plugin `version` no-leak、malformed outer JSON safe error 和 registry permission assertion
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_plugins tests.test_mini_agent` 201 tests OK；`python3 evals/run_evals.py` 436 passed；`git diff --check` OK；PM sentinel no-leak / no-mutation probe OK。
- 内容: 新增 `mini_agent/capability_router.py` 只读 capability routing scaffold 和 registry 工具 `route_capability_request`；根据用户 goal 与已声明 plugin manifest metadata 返回候选插件、匹配 domains/capabilities、聚合风险级别、确认需求和预期交付物；不加载或执行插件、不调用外部服务、不 mutation durable state；输出 bounded 且对 secret-like plugin name/version 做安全处理。

### TASK-114: Deterministic eval coverage for plugin manifest inspection v1 ✅
- 完成者: Claude B；按 PM 初审反馈补强 worker store no-mutation 和 no-plugin-execution eval
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 436 passed；`python3 -m unittest tests.test_plugins tests.test_mcp_server tests.test_mini_agent` 225 tests OK；`git diff --check` OK。
- 内容: 为 `inspect_plugin_manifest` 增加 13 个 deterministic offline eval，覆盖 local/read permission、有效 manifest bounded metadata、malformed JSON / non-object / malformed tools safe errors、duplicate tools、高风险 confirmation 边界、unknown enum normalization no-leak、secret-like redaction、durable task/worker/event read-only no-mutation、plugin inspection 不执行插件代码且不注册工具，以及 MCP/list_tool_permissions compatibility；无 runtime 变更、无网络/模型依赖。

### TASK-113: Plugin manifest schema and inspection v1 ✅
- 完成者: Claude A；按 PM 初审反馈补强 unknown enum / secret-like manifest value no-leak
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_plugins tests.test_mcp_server tests.test_mini_agent` 225 tests OK；`python3 evals/run_evals.py` 423 passed；`git diff --check` OK；PM sentinel no-leak probe OK。
- 内容: 在 `mini_agent/plugins.py` 增加 plugin manifest v1 的 dataclass 模型、JSON/dict parser、validation result、safe inspection 输出和 no-leak normalization；新增 registry read-only 工具 `inspect_plugin_manifest`，权限为 `ToolPermission(category="local", risk="read")`；覆盖必填 identity、tools list、duplicate tools、high-risk confirmation、unknown enum warning、description bounds、domains/capabilities、secret-like redaction、loader compatibility 和 deterministic safe output。

### TASK-112: Deterministic eval coverage for MCP adapter safe tool surface v1 ✅
- 完成者: Claude B；Codex PM 集成时补充 inspection-surface eval
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 423 passed；`python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache` 182 tests OK；`git diff --check` OK。
- 内容: 为 MCP adapter 增加 deterministic offline eval coverage，覆盖 default/custom allowlist、unsafe custom allowlist hide/block、explicit unsafe opt-in、registered-but-not-allowed rejection、safe JSON errors/no secret leak、bounded truncation、memory/calculate compatibility，以及 `inspect_mcp_tool_surface(...)` 完整安全 inspection metadata；无网络、无模型、无共享状态。

### TASK-111: MCP adapter permission-aware tool surface hardening v1 ✅
- 完成者: Claude A；Codex PM 补强 unsafe non-memory write block 和 full inspection helper
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_mcp_server tests.test_mini_agent tests.test_tool_cache` 182 tests OK；`python3 evals/run_evals.py` 423 passed；`git diff --check` OK。
- 内容: 加固 `mini_agent/mcp_server.py`，默认 MCP surface 继续只暴露安全工具；custom allowlist 默认仍会屏蔽 confirmation-required、execute/interact/delete/destructive/external-send/high risk 和非 memory write 工具；新增显式 `allow_unsafe_tools=True` trusted-local opt-in、`validate_allowlist(...)` allowlist 审计，以及 `inspect_mcp_tool_surface(...)` 全量安全元数据 inspection；文档同步更新。

### TASK-110: Deterministic eval coverage for runtime policy hook rule catalog v1 ✅
- 完成者: Claude B；Codex PM 补强 exact permission assertion 和 worker no-mutation eval
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 415 passed；`python3 -m unittest tests.test_durable_workers` 737 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`git diff --check` OK。
- 内容: 为 `describe_runtime_policy_hook_rules(...)` 增加 9 个 deterministic offline eval，覆盖 tool registration + exact `local/read` permission、`policy_version`、完整且排序的 hooks/categories/risks/decisions、10 条 stable rule IDs/order、规则 metadata、catalog priority 与 evaluator priority 对齐、safe bounded no-leak、read-only no durable task/worker/event mutation，以及 policy hook tools/list_tool_permissions/durable task CRUD compatibility；无 runtime 变更。

### TASK-109: Runtime policy hook rule catalog v1 ✅
- 完成者: Claude A
- Reviewer: Codex PM (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 737 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`python3 evals/run_evals.py` 406 passed；`git diff --check` OK。
- 内容: 新增只读 `describe_runtime_policy_hook_rules(...)` registry tool，返回 runtime policy hook kernel 的 `policy_version`、支持的 hooks/categories/risks/decisions 和 10 条 stable rule catalog；规则目录与 `_evaluate_policy_hook_core` 优先级对齐，覆盖 destructive/external-send block、high-risk confirm、hook-specific write/read、generic read/write、default allow；输出仅含 safe bounded metadata，不泄漏 raw action/reason、shell/path/env/request/secret/task/event payload；注册权限为 `ToolPermission(category="local", risk="read")`，不创建 durable event，不 mutation tasks/workers。

### TASK-108: Deterministic eval coverage for runtime policy hook summary v1 ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 406 passed；`python3 -m unittest tests.test_durable_workers` 701 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`git diff --check` OK。
- 内容: 为 `summarize_runtime_policy_hook_evaluations(...)` 增加 11 个 deterministic offline eval，覆盖 decision/hook/category/risk/confirmation/blocked/policy version/recent event ID 聚合计数，hook/decision/category/risk/task_id/worker_id/session_id 过滤，limit bounds，invalid/unsafe filter empty safe errors/no all-events fallback，raw reason/action/shell/env/secret no-leak，read-only no event/task/worker mutation，以及 evaluate/record/list/summary/list_tool_permissions/durable store compatibility；无 runtime 变更。

### TASK-107: Runtime policy hook decision summary v1 ✅
- 完成者: Claude A
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 701 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`python3 evals/run_evals.py` 395 passed；`git diff --check` OK。
- 内容: 新增只读 `summarize_runtime_policy_hook_evaluations(...)` registry tool，聚合 `policy_hook_evaluation` durable events 的 safe bounded summary；支持 hook/decision/category/risk/task_id/worker_id/session_id/limit 过滤；输出 decisions、hooks、categories、risks、requires_confirmation_count、blocked_count、recent_event_ids、policy_versions；无效/不安全 filter 返回 empty summary + safe errors；不泄漏 raw reason/action/sentinel，不 mutation events/tasks/workers。新增 28 个 unit tests 覆盖计数、过滤、limit、no-leak、read-only 和 compatibility。

### TASK-106: Deterministic eval coverage for runtime policy hook event query v1 ✅
- 完成者: Claude B；按 PM 初审反馈补齐 newest-first ordering、raw reason no-leak 和 worker no-mutation eval
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 395 passed；`python3 -m unittest tests.test_durable_workers` 665 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`git diff --check` OK。
- 内容: 为 `list_runtime_policy_hook_evaluations(...)` 增加 12 个 deterministic offline eval，覆盖 safe bounded metadata、newest-first ordering、hook/decision/linkage/combined filters、limit bounds、invalid/unsafe filter no all-events fallback、raw reason/action/shell/env no-leak、read-only no event/task/worker mutation 和 compatibility；无 runtime 变更。

### TASK-105: Runtime policy hook event query v1 ✅
- 完成者: Claude A；按 PM 初审反馈修复完整 hook 过滤和 invalid/unsafe filter 退化为 all-events 的风险
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 665 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`python3 evals/run_evals.py` 383 passed；`git diff --check` OK。
- 内容: 新增只读 `list_runtime_policy_hook_evaluations(...)` registry tool，查询 `policy_hook_evaluation` durable events 的 safe bounded metadata；支持 `hook`、`decision`、`task_id`、`worker_id`、`session_id` 和 `limit` 过滤；hook 过滤复用完整 `_VALID_HOOKS`；无效/不安全非空 filter 返回 bounded empty result + safe errors，不回显 raw sentinel 且不返回无关事件；输出仅包含 event id、created_at、safe linkage、hook/decision/reason_label/policy_version/matched_rules/category/risk/action safe metadata；不 mutation durable events/tasks/workers。

### TASK-104: Deterministic eval coverage for runtime policy hook event recording v1 ✅
- 完成者: Claude B；按 PM 初审反馈修复 event lookup ordering assumption
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 383 passed；`python3 -m unittest tests.test_durable_workers` 635 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`git diff --check` OK。
- 内容: 为 TASK-103 `record_runtime_policy_hook_evaluation` 增加 10 个 deterministic offline eval，覆盖 policy_hook_evaluation event creation、bounded decision metadata、returned event_id queryability、reason/action no-leak、unsupported hook no-event/no-raw-echo、safe/unsafe linkage sanitizer、`evaluate_runtime_policy_hook` read-only boundary、task/worker no-mutation 和 compatibility；无 runtime 变更；eval 通过 returned `event_id` 精确查询 event，避免依赖 `list_events()` 顺序。

### TASK-103: Runtime policy hook evaluation event recording v1 ✅
- 完成者: Claude A；Codex PM 补强 linkage sanitizer 和 registry permission 风险级别
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers` 635 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`python3 evals/run_evals.py` 373 passed；`git diff --check` OK；manual linkage no-leak probe OK。
- 内容: 新增 `POLICY_HOOK_EVALUATION` durable event type 和显式 `record_runtime_policy_hook_evaluation` registry tool；复用 read-only evaluator core logic，成功 supported hook 只写一条 bounded safe policy decision event；保留 `evaluate_runtime_policy_hook` read-only/no-mutation；输出和事件仅含 safe action/decision/reason label/matched rules/policy version/normalized hook/category/risk/linkage metadata；unsupported hook bounded error/no event/no raw leak；不做 enforcement、不自动记录普通工具执行、不 mutation task/worker。

### TASK-102: Deterministic eval coverage for runtime policy hook evaluator v1 ✅
- 完成者: Claude B；按 PM 初审反馈补齐 env-like action 和 workspace path action no-leak eval 断言
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 373 passed；`python3 -m unittest tests.test_durable_workers.RuntimePolicyHookEvaluatorTests` 37 tests OK；`python3 -m unittest tests.test_durable_workers` 607 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`git diff --check` OK。
- 内容: 为 TASK-101 `evaluate_runtime_policy_hook` 增加 9 个 deterministic offline eval，覆盖 allow/confirm/block policy decision、unknown hook bounded error/no raw sentinel、unknown category/risk normalization、raw reason no-leak、secret/path/env-like/workspace-path/shell/long action redaction、安全 action label preservation、read-only no durable task/worker/event mutation，以及 `list_tool_permissions` compatibility；无 runtime 变更。

### TASK-101: Runtime policy hook evaluator v1 ✅
- 完成者: Claude A；Codex PM 因 A 最终 CCB job provider/API 输出噪声，集成 A 工作树已完成补丁并更新准确 DONE 报告
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.RuntimePolicyHookEvaluatorTests` 37 tests OK；`python3 -m unittest tests.test_durable_workers` 607 tests OK；`python3 -m unittest tests.test_durable_events tests.test_config tests.test_mini_agent` 311 tests OK；`python3 evals/run_evals.py` 364 passed；`git diff --check` OK。
- 内容: 新增只读 `evaluate_runtime_policy_hook` registry tool，支持 `pre_tool`、`post_tool`、`pre_edit`、`post_edit`、`pre_shell`、`pre_git`、`pre_plugin_call`、`post_test`、`before_handoff`、`before_commit` 等 hook；输出 bounded policy decision metadata（allow/confirm/block、confirmation/block flags、safe reason label、matched rules、policy version）；不执行 enforcement、不 mutation、不写文件、不调用 shell/git/browser/network/plugin；action/reason/unknown hook 输出安全处理，覆盖 path、shell、env-like、secret-like、all-caps token、workspace path 和 unknown hook sentinel no-leak。

### TASK-100: Deterministic eval coverage for scheduler retry decision event metadata v1 ✅
- 完成者: Claude B
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 364 passed；`python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests tests.test_durable_workers.SchedulerRetryEventMetadataTests` 58 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 737 tests OK；`git diff --check` OK。
- 内容: 为 TASK-099 scheduler retry decision event metadata 增加 6 个 deterministic offline eval，覆盖 tick retry executed event metadata、tick retry skipped missing-capacity metadata、loop retry aggregate/per-tick metadata、`record_event=False` no-event、安全 no-leak 和 compatibility；无 runtime 变更。

### TASK-099: Scheduler retry decision event metadata v1 ✅
- 完成者: Claude A；按 PM 初审反馈补齐 loop event retry aggregate / per-tick metadata
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests` 47 tests OK；`python3 -m unittest tests.test_durable_workers.SchedulerRetryEventMetadataTests` 11 tests OK；`python3 -m unittest tests.test_durable_workers` 570 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 737 tests OK；`python3 evals/run_evals.py` 358 passed；`git diff --check` OK。
- 内容: 扩展 scheduler tick/loop `SCHEDULER_DECISION` durable event metadata；tick actions 增加 bounded retry action fields（executed/skipped/reason/retry_count/max_retries），tick 与 loop API/event payload 增加 `retry_executed`、`retry_skipped`、`retry_failed` aggregate counts，loop event 额外记录 bounded `ticks[]` per-tick retry counts；不持久化 raw results，不泄漏 task goal/steps/failure_reason/workspace/shell/env/request/secrets；保持 `record_event=False` 无 scheduler decision event。

### TASK-098: Deterministic eval coverage for guarded scheduler retry execution v1 ✅
- 完成者: Claude B；按 PM 初审反馈补齐 active ASSIGNED/RUNNING owner 和 stale execution-time guard eval
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 358 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 726 tests OK；`git diff --check` OK。
- 内容: 为 TASK-097 guarded scheduler retry execution 增加 9 个 deterministic offline eval，覆盖 run-once dry-run/no-mutation、non-dry-run retry、tick/loop wrapper retry、active ASSIGNED/RUNNING owner blocking、stale execution-time guard、missing idle capacity skip、closeout before retry/dispatch skipped、安全 no-leak 和 compatibility；无 runtime 变更。

### TASK-097: Guarded scheduler retry execution v1 ✅
- 完成者: Claude A；按 PM 初审反馈补强 idle capacity execution guard、ASSIGNED/RUNNING owner、stale execution-time guard 和 safety no-leak 测试
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecycleRunOnceTests tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests` 71 tests OK；`python3 -m unittest tests.test_durable_workers` 559 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 726 tests OK；`python3 evals/run_evals.py` 349 passed；`git diff --check` OK。
- 内容: 扩展 guarded worker lifecycle execution，让 `run_worker_lifecycle_once` / scheduler tick / scheduler loop 在 `dry_run=False` 时可以执行 planner 输出的 `retry_failed_task` + `retry_available`；执行前重新校验 task still failed、retry_count 未耗尽、无 active ASSIGNED/RUNNING owner、存在 idle capacity；失败或 stale state 返回 bounded safe skipped/failed outcome；保持 `dry_run=True` read-only、dispatch 不执行、closeout > retry > dispatch ordering；输出不泄漏 goal/steps/failure_reason/workspace/shell/env/request/secrets。

### TASK-096: Deterministic eval coverage for scheduler retry planning v1 ✅
- 完成者: Claude B；按 PM 初审反馈补强 RUNNING owner、failure_reason sentinel、read-only/no-mutation 和 filter no-leak 断言
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 349 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 710 tests OK；`git diff --check` OK。
- 内容: 为 scheduler retry planning/explainability 增加 13 个 deterministic offline eval，覆盖 retryable failed task、max-retries exhausted、active ASSIGNED/RUNNING owner blocking、missing idle capacity、retry ordering（closeout > retry > dispatch）、task/worker filter no-leak、planner/explain read-only no-mutation、failure_reason/secret/workspace safety no-leak 和 compatibility；无 runtime 变更。

### TASK-094: Deterministic eval coverage for scheduler blocker explanation v1 ✅
- 完成者: Claude B；包含 PM 初审发现后的 3 行 task filter runtime fix
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 evals/run_evals.py` 336 passed；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 710 tests OK；`git diff --check` OK。
- 内容: 为 `explain_worker_lifecycle_scheduler_state` 增加 13 个 deterministic offline eval，覆盖 empty state、ready closeout、not-ready closeout、pending+idle dispatch availability、pending/no idle、idle/no pending、offline worker、worker/task filters、filtered no-leak、limit/bad args、安全 no-leak 和 compatibility；补充 `task_id` filter 时 top-level `workers` 只返回 `current_task_id` 匹配该 task 的 worker，避免泄漏 unrelated worker id。

### TASK-095: Retryable failed-task planning for worker lifecycle scheduler v1 ✅
- 完成者: Claude A；包含 TASK-093 两个 blocker 修复
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecyclePlannerTests tests.test_durable_workers.WorkerLifecycleExplainStateTests tests.test_durable_workers.RetryableTaskPlannerTests tests.test_durable_workers.RetryableTaskExplainTests tests.test_durable_workers.BlockerFixTests` 77 tests OK；`python3 -m unittest tests.test_durable_workers` 543 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 710 tests OK；`python3 evals/run_evals.py` 323 passed；`git diff --check` OK。
- 内容: 扩展只读 `plan_worker_lifecycle_actions` 与 `explain_worker_lifecycle_scheduler_state`，识别 `failed` 且 `retry_count < max_retries` 且无 active owner worker 的 retryable durable tasks；规划 `retry_failed_task`，保持 closeout > retry > dispatch ordering；explain 输出 `retry_available`、`retry_exhausted`、`retry_blocked_active_worker`、`retry_blocked_missing_capacity`、`retry_not_needed` 等 bounded reason/action metadata；不执行 retry、不 mutation、不泄漏 task goal/steps/file content/reviewer/shell/env/request/workspace paths/secrets；修复 `worker_unavailable` closeout candidate 映射为 `worker_offline`，以及 `worker_id` filter 顶层 tasks 不再泄漏其他 worker 的 task。

### TASK-093: Worker lifecycle scheduler blocker explanation v1 ✅
- 完成者: Claude A；按 PM 三轮初审反馈修正 filter semantics
- Reviewer: CCB reviewer (`agent_tasks/REVIEW.md`) APPROVED
- 验证: `python3 -m unittest tests.test_durable_workers.WorkerLifecycleExplainStateTests` 37 tests OK；`python3 -m unittest tests.test_durable_workers.WorkerLifecycleSchedulerLoopTests tests.test_durable_workers.WorkerLifecycleSchedulerTickTests tests.test_durable_workers.WorkerLifecyclePlannerTests tests.test_durable_workers.WorkerLifecycleExplainStateTests` 102 tests OK；`python3 -m unittest tests.test_durable_workers` 521 tests OK；`python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent` 688 tests OK；`python3 evals/run_evals.py` 323 passed；`python3 -m unittest discover -s tests` 2047 tests OK；`git diff --check` OK。
- 内容: 新增只读 `explain_worker_lifecycle_scheduler_state(worker_id="", task_id="", limit=20)`；复用 worker/task store、closeout candidates 和 planner state，输出 bounded scheduler explain metadata，包括 workers、tasks、closeout candidates、planned actions、blocked reasons 和 next actions；支持 worker/task filter 和 limit validation；解释 ready closeout、waiting/missing apply/lease、offline/running/idle workers、pending unassigned tasks、dispatch available but blocked、no pending/no idle/no action 等 reason labels；输出不泄漏 task goal/steps/file content/reviewer/shell/env/request/workspace paths/secrets，不 mutation。

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
