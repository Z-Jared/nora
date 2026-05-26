import json
import logging
import unittest

from mini_agent.structured_logging import JsonFormatter, setup_logging


class JsonFormatterTests(unittest.TestCase):
    def test_formats_basic_record(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )

        result = json.loads(formatter.format(record))

        self.assertEqual(result["level"], "INFO")
        self.assertEqual(result["logger"], "test")
        self.assertEqual(result["message"], "hello world")
        self.assertIn("timestamp", result)

    def test_formats_record_with_exception(self):
        formatter = JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="failed", args=(), exc_info=exc_info,
        )

        result = json.loads(formatter.format(record))

        self.assertEqual(result["level"], "ERROR")
        self.assertIn("exception", result)
        self.assertIn("ValueError: boom", result["exception"])

    def test_formats_record_with_extra_data(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="warn", args=(), exc_info=None,
        )
        record.extra_data = {"custom_key": "custom_value", "count": 42}

        result = json.loads(formatter.format(record))

        self.assertEqual(result["custom_key"], "custom_value")
        self.assertEqual(result["count"], 42)

    def test_handles_percent_format_message(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="user %s did %s", args=("alice", "login"), exc_info=None,
        )

        result = json.loads(formatter.format(record))

        self.assertEqual(result["message"], "user alice did login")


class SetupLoggingTests(unittest.TestCase):
    def test_setup_logging_configures_root_logger(self):
        setup_logging(level="DEBUG", json_format=False)

        root = logging.getLogger()
        self.assertEqual(root.level, logging.DEBUG)
        self.assertEqual(len(root.handlers), 1)

    def test_setup_logging_json_format(self):
        setup_logging(level="WARNING", json_format=True)

        root = logging.getLogger()
        handler = root.handlers[0]
        self.assertIsInstance(handler.formatter, JsonFormatter)
        self.assertEqual(root.level, logging.WARNING)

    def test_setup_logging_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())

        setup_logging(level="INFO")

        self.assertEqual(len(root.handlers), 1)

    def test_setup_logging_defaults_to_info(self):
        setup_logging()

        root = logging.getLogger()
        self.assertEqual(root.level, logging.INFO)


if __name__ == "__main__":
    unittest.main()
