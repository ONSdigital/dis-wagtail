import json
import logging
import traceback
from datetime import datetime
from typing import Any

import json_log_formatter
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest

SEVERITY_MAPPING = {
    logging.WARNING: 2,
    logging.ERROR: 1,
    logging.CRITICAL: 0,
}

logger = logging.getLogger(__name__)


class JSONFormatter(json_log_formatter.JSONFormatter):
    """A log formatter which outputs JSON and structures log messages as required.

    https://github.com/ONSdigital/dp-standards/blob/main/LOGGING_STANDARDS.md
    """

    def json_record(self, message: str, extra: dict[str, Any], record: logging.LogRecord) -> dict[str, Any]:
        extra = extra.copy()

        if isinstance(extra.get("request"), HttpRequest):
            extra.pop("request", None)

        record_data = {
            "created_at": datetime.fromtimestamp(record.created),
            "namespace": record.name,
            "severity": SEVERITY_MAPPING.get(record.levelno, 3),  # Default to INFO
            "event": message,
            "data": extra,
        }

        if record.exc_info:
            record_data["errors"] = [
                {
                    "message": traceback.format_exception_only(record.exc_info[1])[0].strip(),
                    "stack_trace": [
                        {"file": summary.filename, "function": summary.name, "line": summary.line}
                        for summary in traceback.extract_tb(record.exc_info[2])
                    ],
                }
            ]

        return record_data

    def to_json(self, record: dict) -> str:
        """Converts the record dict to a JSON string.

        If encoding fails, log a message with context.
        """
        try:
            return json.dumps(record, cls=DjangoJSONEncoder)
        except (TypeError, ValueError):
            # NB: Care must be taken that this message is JSON serializable, to avoid recursion issues.
            logger.exception(
                "Unable to serialize log message to JSON. Dropping message",
                extra={"original_message": str(record)},
            )
            return ""


class GunicornAccessJSONFormatter(JSONFormatter):
    """A log formatter which extracts the required details from gunicorn's access logger."""

    DATE_FORMAT = "[%d/%b/%Y:%H:%M:%S %z]"

    def json_record(
        self, message: str, extra: dict[str, str | int | float], record: logging.LogRecord
    ) -> dict[str, str | int | float]:
        record_data: dict = super().json_record(message, extra, record)

        record_data["event"] = "http request"

        record_args: dict[str, Any] = record.args  # type: ignore[assignment]

        response_time = datetime.strptime(record_args["t"], self.DATE_FORMAT)

        # https://docs.gunicorn.org/en/stable/settings.html#access-log-format
        record_data["http"] = {
            "method": record_args["m"],
            "scheme": record_args["{wsgi.url_scheme}e"],
            "host": record_args["{host}i"],
            "path": record_args["U"],
            "query": record_args["q"],
            "status_code": int(record_args["s"]),
            "ended_at": response_time,
            "duration": record_args["D"] * 1000,
            "response_content_length": record_args["B"],
        }

        if not settings.IS_EXTERNAL_ENV:
            record_data["http"]["ip_address"] = record_args["h"]  # This uses the overridden value by django-xff

        return record_data
