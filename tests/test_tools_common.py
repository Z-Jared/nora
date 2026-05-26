import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mini_agent.tools_common import confirm_in_terminal, read_jsonl


class ConfirmInTerminalTests(unittest.TestCase):
    @patch("builtins.input", return_value="y")
    def test_returns_true_for_y(self, mock_input):
        self.assertTrue(confirm_in_terminal("confirm? "))

    @patch("builtins.input", return_value="yes")
    def test_returns_true_for_yes(self, mock_input):
        self.assertTrue(confirm_in_terminal("confirm? "))

    @patch("builtins.input", return_value="YES")
    def test_returns_true_for_uppercase_yes(self, mock_input):
        self.assertTrue(confirm_in_terminal("confirm? "))

    @patch("builtins.input", return_value="n")
    def test_returns_false_for_n(self, mock_input):
        self.assertFalse(confirm_in_terminal("confirm? "))

    @patch("builtins.input", return_value="")
    def test_returns_false_for_empty(self, mock_input):
        self.assertFalse(confirm_in_terminal("confirm? "))

    @patch("builtins.input", side_effect=EOFError)
    def test_returns_false_on_eof(self, mock_input):
        self.assertFalse(confirm_in_terminal("confirm? "))


class ReadJsonlTests(unittest.TestCase):
    def test_reads_valid_jsonl(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"a": 1}\n{"b": 2}\n')
            path = Path(f.name)

        result = read_jsonl(path)

        self.assertEqual(result, [{"a": 1}, {"b": 2}])
        path.unlink()

    def test_returns_empty_list_for_missing_file(self):
        result = read_jsonl(Path("/nonexistent/path.jsonl"))

        self.assertEqual(result, [])

    def test_skips_blank_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"a": 1}\n\n  \n{"b": 2}\n')
            path = Path(f.name)

        result = read_jsonl(path)

        self.assertEqual(result, [{"a": 1}, {"b": 2}])
        path.unlink()

    def test_skips_malformed_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"a": 1}\nnot json\n{"b": 2}\n')
            path = Path(f.name)

        result = read_jsonl(path)

        self.assertEqual(result, [{"a": 1}, {"b": 2}])
        path.unlink()

    def test_returns_empty_list_for_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        result = read_jsonl(path)

        self.assertEqual(result, [])
        path.unlink()


if __name__ == "__main__":
    unittest.main()
