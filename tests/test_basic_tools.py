import unittest

from mini_agent.toolkits.basic import calculate, current_time, make_plan


class CalculateTests(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(calculate("2 + 3"), "5")
        self.assertEqual(calculate("10 - 4"), "6")
        self.assertEqual(calculate("3 * 7"), "21")
        self.assertEqual(calculate("10 / 4"), "2.5")
        self.assertEqual(calculate("10 // 4"), "2")
        self.assertEqual(calculate("10 % 3"), "1")
        self.assertEqual(calculate("2 ** 10"), "1024")

    def test_unary_operators(self):
        self.assertEqual(calculate("-5"), "-5")
        self.assertEqual(calculate("+5"), "5")
        self.assertEqual(calculate("-(3 + 2)"), "-5")

    def test_complex_expression(self):
        self.assertEqual(calculate("(2 + 3) * 4 - 1"), "19")

    def test_syntax_error(self):
        result = calculate("2 +")
        self.assertIn("语法错误", result)

    def test_unsupported_expression(self):
        with self.assertRaises(ValueError):
            calculate("'hello'")

    def test_rejects_function_calls(self):
        with self.assertRaises(ValueError):
            calculate("print(1)")


class CurrentTimeTests(unittest.TestCase):
    def test_returns_formatted_time(self):
        result = current_time()

        self.assertRegex(result, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def test_different_timezone(self):
        result = current_time("UTC")

        self.assertIn("UTC", result)


class MakePlanTests(unittest.TestCase):
    def test_generates_plan(self):
        result = make_plan("add user auth")

        self.assertIn("add user auth", result)
        self.assertIn("目标", result)

    def test_empty_goal(self):
        result = make_plan("")

        self.assertIn("请提供", result)

    def test_whitespace_only_goal(self):
        result = make_plan("   ")

        self.assertIn("请提供", result)


if __name__ == "__main__":
    unittest.main()
