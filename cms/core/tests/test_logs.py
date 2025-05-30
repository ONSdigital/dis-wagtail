import json
import logging
import os
from datetime import timedelta
from types import SimpleNamespace

import time_machine
from django.test import RequestFactory, SimpleTestCase
from gunicorn.config import Config
from gunicorn.glogging import Logger

from cms.core.logs import GunicornJsonFormatter, JSONFormatter

logger = logging.getLogger(__name__)


@time_machine.travel("2025-01-01", tick=False)
class JSONFormatterTestCase(SimpleTestCase):
    def format_log(self, record: logging.LogRecord) -> dict:
        return json.loads(JSONFormatter().format(record))

    def test_formats_message(self):
        with self.assertLogs(__name__) as logs:
            logger.info("The message")

        formatted = self.format_log(logs.records[0])

        self.assertEqual(formatted["created_at"], "2025-01-01T00:00:00")
        self.assertEqual(formatted["namespace"], __name__)
        self.assertEqual(formatted["event"], "The message")
        self.assertEqual(formatted["severity"], 3)

    def test_formats_error(self):
        with self.assertLogs(__name__) as logs:
            try:
                raise ValueError("Something went wrong")
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("The error message")

        formatted = self.format_log(logs.records[0])

        self.assertEqual(formatted["created_at"], "2025-01-01T00:00:00")
        self.assertEqual(formatted["namespace"], __name__)
        self.assertEqual(formatted["event"], "The error message")
        self.assertEqual(formatted["severity"], 1)
        self.assertEqual(
            formatted["errors"],
            [
                {
                    "message": "ValueError('Something went wrong')",
                    "stack_trace": [
                        {
                            "file": os.path.abspath(__file__),
                            "function": "test_formats_error",
                            "line": 'raise ValueError("Something went wrong")',
                        }
                    ],
                }
            ],
        )


@time_machine.travel("2025-01-01", tick=False)
class GunicornJSONFormatterTestCase(SimpleTestCase):
    def setUp(self):
        self.gunicorn_logger = Logger(Config())

    def format_log(self, record: logging.LogRecord) -> dict:
        return json.loads(GunicornJsonFormatter().format(record))

    def test_gunicorn_access_log(self):
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
        self.assertEqual(
            formatted["http"],
            {
                "method": "GET",
                "scheme": "http",
                "host": "testserver",
                "path": "/",
                "query": "",
                "status_code": 200,
                "ended_at": "2025-01-01 00:00:00+00:00",
                "duration": 1000000000,
                "response_content_length": 1024,
            },
        )
