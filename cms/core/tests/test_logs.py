import json
import logging
import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import ANY

import time_machine
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from gunicorn.config import Config
from gunicorn.glogging import Logger

from cms.core.logs import GunicornJsonFormatter, JSONFormatter

logger = logging.getLogger(__name__)


@time_machine.travel("2025-01-01", tick=False)
class JSONFormatterTestCase(TestCase):
    databases = "__all__"

    def format_log(self, record: logging.LogRecord) -> dict:
        formatted_log = JSONFormatter().format(record)
        try:
            return json.loads(formatted_log)
        except json.decoder.JSONDecodeError:
            return formatted_log

    def test_formats_message(self):
        with self.assertLogs(__name__) as logs:
            logger.info("The message")

        self.assertEqual(
            self.format_log(logs.records[0]),
            {
                "created_at": "2025-01-01T00:00:00",
                "namespace": __name__,
                "severity": 3,
                "event": "The message",
                "data": {},
            },
        )

    def test_formats_error(self):
        with self.assertLogs(__name__) as logs:
            try:
                raise ValueError("Something went wrong")
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("The error message")

        self.assertEqual(
            self.format_log(logs.records[0]),
            {
                "created_at": "2025-01-01T00:00:00",
                "namespace": __name__,
                "severity": 1,
                "event": "The error message",
                "data": {},
                "errors": [
                    {
                        "message": "ValueError: Something went wrong",
                        "stack_trace": [
                            {
                                "file": os.path.abspath(__file__),
                                "function": "test_formats_error",
                                "line": 'raise ValueError("Something went wrong")',
                            }
                        ],
                    }
                ],
            },
        )

    def test_formats_request_error(self):
        with self.assertLogs("django.request") as logs:
            response = self.client.get("/does-not-exist")
            self.assertEqual(response.status_code, 404)

        self.assertEqual(
            self.format_log(logs.records[0]),
            {
                "created_at": "2025-01-01T00:00:00",
                "namespace": "django.request",
                "severity": 2,
                "event": "Not Found: /does-not-exist",
                "data": {"status_code": 404},
            },
        )

    def test_serialization_error(self):
        with self.assertLogs(__name__) as source_logs:
            logger.info("Complex data", extra={"data": logger})

        with self.assertLogs("cms.core.logs") as logs:
            original_message = self.format_log(source_logs.records[0])

        self.assertEqual(original_message, "")

        formatted = self.format_log(logs.records[0])

        self.assertEqual(
            formatted,
            {
                "created_at": "2025-01-01T00:00:00",
                "namespace": "cms.core.logs",
                "severity": 1,
                "event": "Unable to serialize log message to JSON. Dropping message",
                "data": {"original_message": ANY},
                "errors": [ANY],
            },
        )

        self.assertEqual(formatted["errors"][0]["message"], "TypeError: Object of type Logger is not JSON serializable")
        self.assertIn("Complex data", formatted["data"]["original_message"])
        self.assertIn(repr(logger), formatted["data"]["original_message"])


@time_machine.travel("2025-01-01", tick=False)
class GunicornJSONFormatterTestCase(SimpleTestCase):
    def setUp(self):
        self.gunicorn_logger = Logger(Config())

    def format_log(self, record: logging.LogRecord) -> dict:
        return json.loads(GunicornJsonFormatter().format(record))

    def test_gunicorn_access_log_includes_ip_in_internal_env(self):
        """IP address is included when IS_EXTERNAL_ENV=False (internal environment)."""
        response = SimpleNamespace(
            status="200",
            response_length=1024,
            headers=(),
            sent=1024,
        )
        request = RequestFactory(RAW_URI="/").get("/", headers={"host": "testserver"})

        safe_atoms = self.gunicorn_logger.atoms_wrapper_class(
            self.gunicorn_logger.atoms(response, request, request.META, timedelta(seconds=1))
        )

        with self.assertLogs(self.gunicorn_logger.access_log.name) as logs:
            # Bypass gunicorn_logger.access, which does additional configuration checks
            self.gunicorn_logger.access_log.info(self.gunicorn_logger.cfg.access_log_format, safe_atoms)

        formatted = self.format_log(logs.records[0])

        self.assertEqual(formatted["created_at"], "2025-01-01T00:00:00")
        self.assertEqual(formatted["namespace"], "gunicorn.access")
        self.assertEqual(formatted["event"], "http request")
        self.assertEqual(formatted["severity"], 3)
        self.assertIn("ip_address", formatted["http"])
        self.assertEqual(formatted["http"]["ip_address"], "127.0.0.1")

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_gunicorn_access_log_excludes_ip_in_external_env(self):
        """IP address is NOT included when IS_EXTERNAL_ENV=True (external environment)."""
        response = SimpleNamespace(
            status="200",
            response_length=1024,
            headers=(),
            sent=1024,
        )
        request = RequestFactory(RAW_URI="/").get("/", headers={"host": "testserver"})

        safe_atoms = self.gunicorn_logger.atoms_wrapper_class(
            self.gunicorn_logger.atoms(response, request, request.META, timedelta(seconds=1))
        )

        with self.assertLogs(self.gunicorn_logger.access_log.name) as logs:
            # Bypass gunicorn_logger.access, which does additional configuration checks
            self.gunicorn_logger.access_log.info(self.gunicorn_logger.cfg.access_log_format, safe_atoms)

        formatted = self.format_log(logs.records[0])

        self.assertEqual(formatted["created_at"], "2025-01-01T00:00:00")
        self.assertEqual(formatted["namespace"], "gunicorn.access")
        self.assertEqual(formatted["event"], "http request")
        self.assertEqual(formatted["severity"], 3)
        self.assertNotIn("ip_address", formatted["http"])
        self.assertNotIn("127.0.0.1", json.dumps(formatted))
