from mini_agent.registry import ToolPermission, ToolRegistry


def register_git_tools(registry: ToolRegistry, git_tools) -> None:
    registry.register(
        "git_status",
        "查看当前仓库的 Git 工作区状态。只读，不会修改仓库。",
        git_tools.status,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_diff",
        "查看当前仓库的 Git diff。可指定项目内路径；只读，不会修改仓库。",
        git_tools.diff,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "可选，相对于项目根目录的路径，例如 README.md",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                },
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_log",
        "查看最近 Git 提交。只读，不会修改仓库。",
        git_tools.log,
        parameters={
            "type": "object",
            "properties": {
                "max_count": {
                    "type": "integer",
                    "description": "最多返回多少个提交，默认 5，最大 50",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_current_branch",
        "查看当前 Git 分支。只读，不会修改仓库。",
        git_tools.current_branch,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_branches",
        "列出本地 Git 分支。只读，不会修改仓库。",
        git_tools.branches,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_staged_diff",
        "查看已暂存改动的 Git diff。只读，不会修改仓库。",
        git_tools.staged_diff,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_summarize_changes",
        "汇总当前分支、status、staged/unstaged stat 和最近提交。只读，不会修改仓库。",
        git_tools.summarize_changes,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_review_staged_diff",
        "审查 staged diff 的文件列表、统计和敏感路径提示。只读，不会修改仓库。",
        git_tools.review_staged_diff,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_check_before_commit",
        "提交前检查 staged、unstaged/untracked 和敏感路径状态。只读，不会修改仓库。",
        git_tools.check_before_commit,
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {
                    "type": "integer",
                    "description": "最多返回多少字符，默认 12000",
                }
            },
        },
        permission=ToolPermission(category="git", risk="read"),
    )
    registry.register(
        "git_create_branch",
        "创建本地 Git 分支但不切换。需要用户确认；不会 push、pull、fetch 或修改远程。",
        git_tools.create_branch,
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要创建的本地分支名",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要创建这个分支",
                },
            },
            "required": ["name"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
    registry.register(
        "git_stage_paths",
        "暂存显式指定的项目内路径。需要用户确认；拒绝敏感路径，不支持 git add . 或 git add -A。",
        git_tools.stage_paths,
        parameters={
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要暂存的项目内相对路径列表",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要暂存这些路径",
                },
            },
            "required": ["paths"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
    registry.register(
        "git_unstage_paths",
        "取消暂存显式指定的项目内路径。需要用户确认；拒绝敏感路径。",
        git_tools.unstage_paths,
        parameters={
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要取消暂存的项目内相对路径列表",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要取消暂存这些路径",
                },
            },
            "required": ["paths"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
    registry.register(
        "git_commit_staged",
        "提交已暂存的 Git 改动。需要用户确认；不会自动暂存、不会创建空提交、不会 push。",
        git_tools.commit_staged,
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "本地 commit message",
                },
                "reason": {
                    "type": "string",
                    "description": "说明为什么需要创建这个本地提交",
                },
            },
            "required": ["message"],
        },
        permission=ToolPermission(category="git", risk="write", requires_confirmation=True),
    )
