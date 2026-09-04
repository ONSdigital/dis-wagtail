import logging
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChartObjectResponse:
    """Typed representation of the 201 response from POST /charts."""

    id: str
    created_at: str
    bucket: str
    key: str
    content_type: str
    size_bytes: int
    width: int
    height: int


class ChartExporterError(Exception):
    """Base exception for ChartExporterClient errors."""

    def __init__(self, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        # Normalise for consistency
        self.errors: list[dict[str, str]] = errors or [{"code": "unknown", "description": message}]


class ChartExporterMalformedRequest(ChartExporterError):
    """400/413/415: a bug in the CMS's request or the exporter's contract. Not retryable."""


class ChartExporterUnavailable(ChartExporterError):
    """500/503/timeout/connection error. Safe to retry."""


class ChartExporterClient:
    """Client for the ONS Chart Exporter API."""

    _MALFORMED_REQUEST_STATUSES = frozenset(
        {HTTPStatus.BAD_REQUEST, HTTPStatus.REQUEST_ENTITY_TOO_LARGE, HTTPStatus.UNSUPPORTED_MEDIA_TYPE}
    )
    _RETRYABLE_STATUSES = frozenset({HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.SERVICE_UNAVAILABLE})

    def __init__(self, *, base_url: str | None = None):
        self.base_url = base_url or settings.CMS_CHART_EXPORTER_API_BASE_URL
        self.session = requests.Session()
        self.is_enabled = settings.CMS_CHART_EXPORTER_API_ENABLED
        self.timeout = settings.CMS_CHART_EXPORTER_API_TIMEOUT_SECONDS
        self.max_retries = settings.CMS_CHART_EXPORTER_API_MAX_RETRIES
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def create_chart(
        self, chart_config: dict[str, Any], *, language: str = "en", device: str = "desktop"
    ) -> ChartObjectResponse | None:
        """POST /charts. Returns None without calling out when the integration is disabled.

        Raises:
            ChartExporterMalformedRequest: for 400/413/415 responses.
            ChartExporterUnavailable: for 500/503/timeout/connection errors, after exhausting retries.
        """
        if not self.is_enabled:
            logger.info("Skipping chart exporter API call because CMS_CHART_EXPORTER_API_ENABLED is False")
            return None

        payload = {"language": language, "device": device, "chart_config": chart_config}
        data = self._request_with_retries("POST", "/charts", payload)
        return ChartObjectResponse(
            id=data["id"],
            created_at=data["created_at"],
            bucket=data["bucket"],
            key=data["key"],
            content_type=data["content_type"],
            size_bytes=data["size_bytes"],
            width=data["width"],
            height=data["height"],
        )

    def _request_with_retries(self, method: str, path: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        """Retry with exponential backoff, but only for retryable (unavailable) failures."""
        attempt = 0
        while True:
            try:
                return self._make_request(method, path, json_payload)
            except ChartExporterUnavailable:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                backoff_seconds = 0.5 * (2 ** (attempt - 1))
                logger.warning(
                    "Retrying chart exporter API request (attempt %d/%d) after %.1fs",
                    attempt,
                    self.max_retries,
                    backoff_seconds,
                )
                time.sleep(backoff_seconds)

    def _make_request(self, method: str, path: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self.session.request(method, url, json=json_payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise self._translate_http_error(exc) from exc
        except requests.exceptions.Timeout as exc:
            logger.warning("Timeout calling chart exporter API %s %s: %s", method, url, exc)
            raise ChartExporterUnavailable(f"Timeout calling chart exporter API: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.warning("Connection error calling chart exporter API %s %s: %s", method, url, exc)
            raise ChartExporterUnavailable(f"Connection error calling chart exporter API: {exc}") from exc

        json_response: dict[str, Any] = response.json()
        return json_response

    def _translate_http_error(self, exc: requests.exceptions.HTTPError) -> ChartExporterError:
        status_code = exc.response.status_code
        errors = self._parse_errors(exc.response)
        message = f"HTTP {status_code} error from chart exporter API"

        if status_code in self._MALFORMED_REQUEST_STATUSES:
            # A bug in the CMS or the exporter's contract: developers need to see this.
            logger.exception("Malformed request to chart exporter API", extra={"status_code": status_code})
            return ChartExporterMalformedRequest(message, errors)

        if status_code in self._RETRYABLE_STATUSES:
            logger.warning("Chart exporter API unavailable: %s", message, extra={"status_code": status_code})
            return ChartExporterUnavailable(message, errors)

        logger.exception("Unexpected error from chart exporter API", extra={"status_code": status_code})
        return ChartExporterError(message, errors)

    @staticmethod
    def _parse_errors(response: requests.Response) -> list[dict[str, str]] | None:
        try:
            errors: list[dict[str, str]] | None = response.json().get("errors")
        except ValueError, requests.exceptions.JSONDecodeError:
            return None
        return errors
