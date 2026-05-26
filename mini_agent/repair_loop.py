from mini_agent.diagnostics import ALLOWED_TEST_COMMAND, Diagnostics


class RepairLoop:
    def __init__(self, diagnostics: Diagnostics):
        self.diagnostics = diagnostics

    def run(self, max_attempts: int = 2, test_command: str = ALLOWED_TEST_COMMAND, reason: str = "") -> str:
        command = test_command.strip() or ALLOWED_TEST_COMMAND
        if command != ALLOWED_TEST_COMMAND:
            return "拒绝运行修复循环: 命令不在测试白名单内。"

        max_attempts = max(1, min(max_attempts, 3))
        sections = [f"修复测试循环: max_attempts={max_attempts}"]
        last_output = ""
        for attempt in range(1, max_attempts + 1):
            output = self.diagnostics.run_tests(command)
            last_output = output
            summary = _extract_summary(output)
            sections.append(f"attempt {attempt}: {summary}")
            if "exit_code: 0" in output:
                sections.append("结果: 测试已通过，停止循环。")
                return "\n".join(sections)

            diagnosis = self.diagnostics.diagnose_test_failure(output)
            sections.append(diagnosis)
            if attempt < max_attempts:
                sections.append("下一步建议: 根据诊断生成最小 patch，使用 apply_project_patch 申请确认后再继续。")

        sections.append("结果: 已达到最大尝试次数，未自动应用 patch 或提交。")
        if last_output:
            sections.append("最终建议: 检查最后一次失败诊断，手动准备 patch 后再运行测试。")
        return "\n".join(sections)


def _extract_summary(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("summary: "):
            return line.removeprefix("summary: ")
    return "测试失败" if output else "没有测试输出"
