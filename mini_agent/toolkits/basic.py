import ast
import operator
from datetime import datetime
from zoneinfo import ZoneInfo


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression: str) -> str:
    node = ast.parse(expression, mode="eval")
    return str(_eval_math_node(node.body))


def _eval_math_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left = _eval_math_node(node.left)
        right = _eval_math_node(node.right)
        return _OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_math_node(node.operand))

    raise ValueError("Only numeric math expressions are supported.")


def current_time(timezone: str = "Asia/Shanghai") -> str:
    now = datetime.now(ZoneInfo(timezone))
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")


def make_plan(goal: str) -> str:
    goal = goal.strip()
    if not goal:
        return "请提供要规划的目标。"

    return "\n".join(
        [
            f"目标: {goal}",
            "1. 明确输入、输出和成功标准。",
            "2. 检查现有代码结构和相关测试。",
            "3. 先写覆盖目标行为的测试。",
            "4. 实现最小可用代码，让测试通过。",
            "5. 运行验证，并记录后续风险和改进点。",
        ]
    )
