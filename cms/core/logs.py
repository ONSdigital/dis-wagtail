import datetime
from logging import LogRecord
from typing import Any

import json_log_formatter


class JSONFormatter(json_log_formatter.JSONFormatter):
    """A log formatter which outputs JSON and structures log messages as required."""

    def json_record(
        self, message: str, extra: dict[str, str | int | float], record: LogRecord
    ) -> dict[str, str | int | float]:
        record_data: dict = super().json_record(message, extra, record)

        del record_data["time"]

        record_data["created_at"] = datetime.datetime.fromtimestamp(record.created)
        record_data["namespace"] = record.name

        return record_data


class GunicornJsonFormatter(JSONFormatter):
    """A log formatter which extracts the required details from gunicorn's access logger."""

    def json_record(
        self, message: str, extra: dict[str, str | int | float], record: LogRecord
    ) -> dict[str, str | int | float]:
        record_data: dict = super().json_record(message, extra, record)

        record_args: dict[str, Any] = record.args  # type: ignore[assignment]

        response_time = datetime.datetime.strptime(record_args["t"], "[%d/%b/%Y:%H:%M:%S %z]")

        # https://docs.gunicorn.org/en/stable/settings.html#access-log-format
        record_data["http"] = {
            "method": record_args["m"],
            "scheme": record_args["{wsgi.url_scheme}e"],
            "host": record_args["{host}i"],
            "path": record_args["U"],
            "query": record_args["q"],
            "status_code": record_args["s"],
            "ended_at": response_time,
            "duration": record_args["D"] * 1000,
            "response_content_length": record_args["B"],
            "ip_address": record_args["h"],  # This uses the overridden value by django-xff
        }

        return record_data
