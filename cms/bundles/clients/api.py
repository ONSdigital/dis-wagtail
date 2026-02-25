import logging
from collections.abc import Iterator, Mapping, Sequence
from http import HTTPStatus
from typing import Any

import requests
from django.conf import settings

from cms.bundles.utils import BundleAPIBundleMetadata

logger = logging.getLogger(__name__)


class BundleAPIMessage:
    REQUEST_ACCEPTED = "Request accepted and is being processed"
    OPERATION_SUCCESS = "Operation completed successfully"


class BundleAPIClientError(Exception):
    """Base exception for BundleAPIClient errors."""

    def __init__(self, message: str, errors: Sequence[dict] | None = None):
        """Initialize the exception with a message and optional error details.

        Args:
            message: The error message
            errors: Optional list of error details from the API response
        """
        super().__init__(message)
        self.errors: Sequence[dict] = errors or [{"description": message}]


class BundleAPIClientError404(BundleAPIClientError):
    """Exception for 404 Not Found errors from the Bundle API."""


class BundleAPIClient:
    """Client for interacting with the ONS Dataset Bundle API endpoints.

    API spec (as of 2025-10-27)
    https://github.com/ONSdigital/dis-bundle-api/blob/584dbae87ebcdf38626be8926496add22eb591bd/swagger.yaml
    """

    # Swagger default is 20, maximum is 1000. We prefer a high default for bulk reads.
    DEFAULT_PAGE_LIMIT = 100
    MAX_LIMIT = 1000
    MIN_LIMIT = 1

    def __init__(self, *, base_url: str | None = None, access_token: str | None = None):
        """Initialize the client with the base URL.

        Args:
            base_url: The base URL for the API. If not provided, uses settings.DIS_DATASETS_BUNDLE_API_BASE_URL
            access_token: The user authorisation token, as provided by Florence/DIS auth and stored
                          in the COOKIES[settings.ACCESS_TOKEN_COOKIE_NAME]
        """
        self.base_url = base_url or settings.DIS_DATASETS_BUNDLE_API_BASE_URL
        self.session = requests.Session()
        self.is_enabled = getattr(settings, "DIS_DATASETS_BUNDLE_API_ENABLED", False)
        # Sensible default timeout for outbound HTTP calls. Overridable via settings.
        self.timeout = settings.HTTP_REQUEST_DEFAULT_TIMEOUT_SECONDS

        # Set default headers for all requests
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if access_token is not None:
            # Note: Don't prepend "Bearer " - it's already in the token
            headers["Authorization"] = access_token
        self.session.headers.update(headers)

    @classmethod
    def _normalise_limit(cls, limit: int | None) -> int:
        """Clamp requested limit to swagger bounds, applying a high default for throughput."""
        if limit is None:
            return cls.DEFAULT_PAGE_LIMIT

        return max(cls.MIN_LIMIT, min(limit, cls.MAX_LIMIT))

    def _make_request(  # pylint: disable=too-many-arguments,too-many-locals  # noqa: PLR0913
        self,
        method: str,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        etag: str | None = None,
        timeout: float | int | None = None,
    ) -> dict[str, Any]:
        """Make a request to the API and handle common errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint relative to base_url
            data: Request data for POST/PUT requests. Can be a dict (for JSON) or a string.
            params: URL parameters for GET requests
            etag: Optional entity tag to send as If-Match for write operations
            timeout: Optional per-request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            BundleAPIClientError: For API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        if not self.is_enabled:
            logger.info("Skipping API call to '%s' because DIS_DATASETS_BUNDLE_API_ENABLED is False", url)
            return {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}

        try:
            request_kwargs: dict[str, Any] = {"timeout": timeout or self.timeout}
            if data is not None:
                request_kwargs["json"] = data
            if params is not None:
                # Params like pagination from get_bundles() etc.
                request_kwargs["params"] = params
            if etag is not None:
                # Set If-Match on this request only to avoid sticky headers on the session
                request_kwargs.setdefault("headers", {})
                request_kwargs["headers"]["If-Match"] = etag

            response = self.session.request(method, url, **request_kwargs)
            response.raise_for_status()
            return self._process_response(response)

        except requests.exceptions.HTTPError as e:
            # Import here to avoid circular import
            from cms.bundles.notifications.api_failures import (  # pylint: disable=import-outside-toplevel
                notify_slack_of_third_party_api_failure,
            )
            from cms.bundles.notifications.slack import BundleAlertType  # pylint: disable=import-outside-toplevel

            error_msg, errors = self._format_http_error(e)
            logger_extra: dict[str, Any] = {
                "method": method,
                "url": url,
                "status_code": e.response.status_code,
                "error_message": error_msg,
            }
            if errors:
                logger_extra["api_errors"] = errors

            logger.exception(
                "HTTP error occurred",
                extra=logger_extra,
            )

            # Determine alert type based on status code
            alert_type = (
                BundleAlertType.CRITICAL
                if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
                else BundleAlertType.WARNING
            )

            # Send Slack notification for API failure
            notify_slack_of_third_party_api_failure(
                service_name="Bundle API",
                exception_message=error_msg,
                alert_type=alert_type,
            )

            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise BundleAPIClientError404(error_msg, errors) from e

            raise BundleAPIClientError(error_msg, errors) from e

        except requests.exceptions.RequestException as e:
            # Import here to avoid circular import
            from cms.bundles.notifications.api_failures import (  # pylint: disable=import-outside-toplevel
                notify_slack_of_third_party_api_failure,
            )
            from cms.bundles.notifications.slack import BundleAlertType  # pylint: disable=import-outside-toplevel

            error_msg = f"Network error for {method} {url}: {e!s}"
            logger.error("Network error for %s %s: %s", method, url, e)

            # Send Slack notification for API failure
            notify_slack_of_third_party_api_failure(
                service_name="Bundle API",
                exception_message=error_msg,
                alert_type=BundleAlertType.WARNING,
            )

            raise BundleAPIClientError(error_msg) from e

    @staticmethod
    def _process_response(response: requests.Response) -> dict[str, Any]:
        """Process successful API responses.

        Args:
            response: The requests Response object

        Returns:
            Response data as a dictionary
        """
        etag = response.headers.get("etag", "")

        # Handle 202 responses (accepted, but processing)
        if response.status_code == HTTPStatus.ACCEPTED:
            return {
                "status": "accepted",
                "location": response.headers.get("Location", ""),
                "message": BundleAPIMessage.REQUEST_ACCEPTED,
                "etag_header": etag,
            }

        # Handle 204 responses (no content)
        if response.status_code == HTTPStatus.NO_CONTENT:
            return {"status": "success", "message": BundleAPIMessage.OPERATION_SUCCESS, "etag_header": etag}

        json_data: dict[str, Any] = response.json()
        # ETag is usually returned as a header, so inject it in the response JSON
        json_data["etag_header"] = etag
        return json_data

    @staticmethod
    def _format_http_error(error: requests.exceptions.HTTPError) -> tuple[str, list[dict] | None]:
        """Format HTTP error messages with appropriate context.

        Args:
            error: The HTTPError exception

        Returns:
            Tuple of (formatted error message, list of error details or None)
        """
        status_code = error.response.status_code
        try:
            status_phrase = HTTPStatus(status_code).phrase
        except ValueError:
            # Handle non-standard or unknown status codes gracefully
            status_phrase = "Unknown Error"

        # This message is shown to the user, we don't want to leak URLs or sensitive info
        formatted_msg = f"HTTP {status_code} error: {status_phrase}"

        # Try to extract error details from response body
        errors: list | None = None
        try:
            errors = error.response.json().get("errors")
        except (ValueError, AttributeError, requests.exceptions.JSONDecodeError):
            pass

        return formatted_msg, errors

    def _iter_pages(self, *, path: str, params: Mapping[str, str]) -> Iterator[dict[str, Any]]:
        """Page iterator for endpoints that implement pagination.

        Yields:
          The raw page JSON dict for each page.
        """
        # Ensure page size and start offset are sane
        limit = self._normalise_limit(int(params.get("limit", self.DEFAULT_PAGE_LIMIT)))
        offset = max(0, int(params.get("offset", 0)))

        total_count = None
        current_offset = offset

        while True:
            updated_params = {**params, "limit": str(limit), "offset": str(current_offset)}
            page = self._make_request("GET", path, params=updated_params)

            count = page["count"]
            if total_count is None:
                total_count = page["total_count"]

            yield page

            current_offset += count
            if current_offset >= total_count:
                break

    def _aggregate_paginated(self, *, path: str, params: Mapping[str, str]) -> dict[str, Any]:
        """Collect all pages for a paginated endpoint and return a swagger-shaped payload."""
        if not self.is_enabled:
            logger.info("Skipping API call to '%s' because DIS_DATASETS_BUNDLE_API_ENABLED is False", path)
            return {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}

        all_items: list[dict[str, Any]] = []
        first_page: dict[str, Any] | None = None

        for page in self._iter_pages(path=path, params=params):
            if first_page is None:
                first_page = page
            all_items.extend(page.get("items") or [])

        return {
            "items": all_items,
            "count": len(all_items),
            "limit": int(params["limit"]),
            "offset": 0,
            # total_count is stable; ETag is per page. We keep the first page’s ETag only.
            "total_count": first_page["total_count"] if first_page else len(all_items),
            "etag_header": first_page["etag_header"] if first_page else "",
        }

    # --------------------------
    # Public operations
    # --------------------------

    def create_bundle(self, bundle_data: BundleAPIBundleMetadata) -> dict[str, Any]:
        """Create a new bundle via the API.

        Args:
            bundle_data: Bundle data containing title and content list

        Returns:
            API response data
        """
        return self._make_request("POST", "/bundles", data=bundle_data.as_dict())

    def update_bundle(self, bundle_id: str, *, bundle_data: BundleAPIBundleMetadata, etag: str) -> dict[str, Any]:
        """Update an existing bundle via the API.

        Args:
            bundle_id: The ID of the bundle to update
            bundle_data: Updated bundle data
            etag: The bundle ETag

        Returns:
            API response data
        """
        return self._make_request("PUT", f"/bundles/{bundle_id}", data=bundle_data.as_dict(), etag=etag)

    def update_bundle_state(self, bundle_id: str, *, state: str, etag: str) -> dict[str, Any]:
        """Update the state of a bundle via the API.

        Args:
            bundle_id: The ID of the bundle to update
            state: New state for the bundle (DRAFT, IN_REVIEW, APPROVED, PUBLISHED)
            etag: The bundle ETag

        Returns:
            API response data
        """
        # The swagger spec expects a JSON object with a 'state' field
        return self._make_request("PUT", f"/bundles/{bundle_id}/state", data={"state": state}, etag=etag)

    def add_content_to_bundle(self, bundle_id: str, *, content_item: dict[str, Any]) -> dict[str, Any]:
        """Add a content item to a bundle.

        Args:
            bundle_id: The ID of the bundle to add content to.
            content_item: The content item to add.

        Returns:
            API response data
        """
        return self._make_request("POST", f"/bundles/{bundle_id}/contents", data=content_item)

    def delete_content_from_bundle(self, bundle_id: str, *, content_id: str) -> dict[str, Any]:
        """Delete a content item from a bundle.

        Args:
            bundle_id: The ID of the bundle to delete content from.
            content_id: The ID of the content item to delete.

        Returns:
            API response data
        """
        return self._make_request("DELETE", f"/bundles/{bundle_id}/contents/{content_id}")

    def get_bundle_contents(self, bundle_id: str, *, limit: int | None = None, offset: int = 0) -> dict[str, Any]:
        """Get the list of all contents for a specific bundle.

        Args:
            bundle_id: The ID of the bundle to get contents for.
            limit: The maximum number of items to return. Defaults to DEFAULT_PAGE_LIMIT.
            offset: The starting index of the items to return. Defaults to 0.

        Returns:
            API response data containing the list of contents.
        """
        page_limit = self._normalise_limit(limit)
        start_offset = max(0, offset)

        params = {"limit": str(page_limit), "offset": str(start_offset)}
        return self._aggregate_paginated(path=f"/bundles/{bundle_id}/contents", params=params)

    def delete_bundle(self, bundle_id: str) -> dict[str, Any]:
        """Delete a bundle via the API.

        Args:
            bundle_id: The ID of the bundle to delete

        Returns:
            API response data
        """
        return self._make_request("DELETE", f"/bundles/{bundle_id}")

    def get_bundles(
        self, *, limit: int | None = None, offset: int = 0, publish_date: str | None = None
    ) -> dict[str, Any]:
        """Get a list of all bundles.

        Args:
            limit: The maximum number of items to return. Defaults to DEFAULT_PAGE_LIMIT.
            offset: The starting index of the items to return. Defaults to 0.
            publish_date: Filter bundles by their scheduled publication date.

        Returns:
            API response data containing a list of bundles.
        """
        page_limit = self._normalise_limit(limit)
        start_offset = max(0, offset)

        params: dict[str, str] = {"limit": str(page_limit), "offset": str(start_offset)}
        if publish_date:
            params["publish_date"] = publish_date

        return self._aggregate_paginated(path="/bundles", params=params)

    def get_bundle(self, bundle_id: str) -> dict[str, Any]:
        """Get a specific bundle by its ID.

        Args:
            bundle_id: The ID of the bundle to retrieve.

        Returns:
            API response data for the bundle.
        """
        return self._make_request("GET", f"/bundles/{bundle_id}")

    def get_health(self) -> dict[str, Any]:
        """Get the health status of the API.

        Returns:
            API response data containing the health status.
        """
        return self._make_request("GET", "/health")
