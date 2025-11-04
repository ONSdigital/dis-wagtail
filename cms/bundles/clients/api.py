import logging
from collections.abc import Iterator, Mapping
from http import HTTPStatus
from typing import Any, Literal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BundleAPIMessage:
    REQUEST_ACCEPTED = "Request accepted and is being processed"
    OPERATION_SUCCESS = "Operation completed successfully"


class BundleAPIClientError(Exception):
    """Base exception for BundleAPIClient errors."""


class BundleAPIClient:
    """Client for interacting with the ONS Dataset Bundle API endpoints.

    https://github.com/ONSdigital/dis-bundle-api/blob/bd5e75290f3f1595d496902a73744e2084056944/swagger.yaml
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
        self.timeout = settings.DIS_DATASETS_BUNDLE_API_REQUEST_TIMEOUT_SECONDS

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

    def _make_request(  # pylint: disable=too-many-arguments,too-many-positional-arguments  # noqa: PLR0913
        self,
        method: str,
        endpoint: str,
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
            error_msg = self._format_http_error(e, method, url)
            logger.error("HTTP error occurred: %s", error_msg)
            raise BundleAPIClientError(error_msg) from e

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error for {method} {url}: {e!s}"
            logger.error("Network error for %s %s: %s", method, url, e)
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
    def _format_http_error(error: requests.exceptions.HTTPError, method: str, url: str) -> str:
        """Format HTTP error messages with appropriate context.

        Args:
            error: The HTTPError exception
            method: HTTP method used
            url: URL that failed

        Returns:
            Formatted error message
        """
        status_code = error.response.status_code
        base_msg = f"HTTP {status_code} error for {method} {url}"

        try:
            return f"{base_msg}: {HTTPStatus(status_code).phrase}"
        except ValueError:
            # Handle non-standard or unknown status codes gracefully
            return f"{base_msg}: Unknown Error"

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
            all_items.extend(page["items"])

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

    def create_bundle(self, bundle_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new bundle via the API.

        Args:
            bundle_data: Bundle data containing title and content list

        Returns:
            API response data
        """
        return self._make_request("POST", "/bundles", data=bundle_data)

    def update_bundle(self, bundle_id: str, bundle_data: dict[str, Any], etag: str) -> dict[str, Any]:
        """Update an existing bundle via the API.

        Args:
            bundle_id: The ID of the bundle to update
            bundle_data: Updated bundle data
            etag: The bundle ETag

        Returns:
            API response data
        """
        return self._make_request("PUT", f"/bundles/{bundle_id}", data=bundle_data, etag=etag)

    def update_bundle_state(self, bundle_id: str, state: str, etag: str) -> dict[str, Any]:
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

    def add_content_to_bundle(self, bundle_id: str, content_item: dict[str, Any]) -> dict[str, Any]:
        """Add a content item to a bundle.

        Args:
            bundle_id: The ID of the bundle to add content to.
            content_item: The content item to add.

        Returns:
            API response data
        """
        return self._make_request("POST", f"/bundles/{bundle_id}/contents", data=content_item)

    def delete_content_from_bundle(self, bundle_id: str, content_id: str) -> dict[str, Any]:
        """Delete a content item from a bundle.

        Args:
            bundle_id: The ID of the bundle to delete content from.
            content_id: The ID of the content item to delete.

        Returns:
            API response data
        """
        return self._make_request("DELETE", f"/bundles/{bundle_id}/contents/{content_id}")

    def get_bundle_contents(self, bundle_id: str, limit: int | None = None, offset: int = 0) -> dict[str, Any]:
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

    def get_bundles(self, limit: int | None = None, offset: int = 0, publish_date: str | None = None) -> dict[str, Any]:
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


def build_content_item_for_dataset(dataset: Any) -> dict[str, Any]:
    """Build a content item dict for a dataset following Bundle API swagger spec.

    Args:
        dataset: A Dataset instance with namespace, edition, and version fields

    Returns:
        A dictionary representing a ContentItem for the Bundle API
    """
    return {
        "content_type": "DATASET",
        "metadata": {
            "dataset_id": dataset.namespace,
            "edition_id": dataset.edition,
            "version_id": dataset.version,
        },
        "links": {
            "edit": get_data_admin_action_url("edit", dataset.namespace, dataset.edition, dataset.version),
            "preview": get_data_admin_action_url("preview", dataset.namespace, dataset.edition, dataset.version),
        },
    }


def extract_content_id_from_bundle_response(response: dict[str, Any], dataset: Any) -> str | None:
    """Extract content_id from Bundle API response for a specific dataset.

    Args:
        response: Bundle API response
        dataset: Dataset instance to find in the response

    Returns:
        The content_id if found, None otherwise
    """
    metadata = response.get("metadata", {})
    if (
        metadata.get("dataset_id") == dataset.namespace
        and metadata.get("edition_id") == dataset.edition
        and metadata.get("version_id") == dataset.version
    ):
        content_id = response.get("id")
        return content_id if content_id is not None else None

    return None


def get_data_admin_action_url(
    action: Literal["edit", "preview"], dataset_id: str, edition_id: str, version_id: str
) -> str:
    """Generate a relative URL for dataset actions in the ONS Data Admin interface.

    This function constructs relative URLs for dataset operations in the ONS Data Admin
    system, which is used for editing and previewing datasets.

    Args:
        action: The action to perform ("edit", "preview")
        dataset_id: The unique identifier for the dataset
        edition_id: The edition identifier for the dataset
        version_id: The version identifier for the dataset

    Returns:
        A relative URL string for the specified dataset action

    Example:
        >>> get_data_admin_action_url("edit", "cpih", "time-series", "1")
        "/edit/datasets/cpih/editions/time-series/versions/1"
    """
    return f"/{action}/datasets/{dataset_id}/editions/{edition_id}/versions/{version_id}"
