import logging
from http import HTTPStatus
from typing import Any, Literal, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BundleAPIMessage:
    REQUEST_ACCEPTED = "Request accepted and is being processed"
    OPERATION_SUCCESS = "Operation completed successfully"


class BundleAPIClientError(Exception):
    """Base exception for BundleAPIClient errors."""


class BundleAPIClient:
    """Client for interacting with the ONS Dataset API bundle endpoints."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the client with the base URL.

        Args:
            base_url: The base URL for the API. If not provided, uses settings.ONS_API_BASE_URL
        """
        self.base_url = base_url or settings.ONS_API_BASE_URL
        self.session = requests.Session()
        self.is_enabled = getattr(settings, "ONS_BUNDLE_API_ENABLED", False)

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            # TODO: Add authentication headers
        )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Make a request to the API and handle common errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint relative to base_url
            data: Request data for POST/PUT requests. Can be a dict (for JSON) or a string.
            params: URL parameters for GET requests

        Returns:
            Response data as dictionary

        Raises:
            BundleAPIClientError: For API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        if not self.is_enabled:
            logger.info("Skipping API call to '%s' because ONS_BUNDLE_API_ENABLED is False", url)
            return {"status": "disabled", "message": "Bundle API is disabled"}

        try:
            request_kwargs: dict[str, Any] = {}
            if data is not None:
                request_kwargs["json"] = data

            if params is not None:
                # Params like pagination from get_bundles() etc.
                request_kwargs["params"] = params

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

    def _process_response(self, response: requests.Response) -> dict[str, Any]:
        """Process successful API responses.

        Args:
            response: The requests Response object

        Returns:
            Response data as a dictionary
        """
        # Handle 202 responses (accepted, but processing)
        if response.status_code == HTTPStatus.ACCEPTED:
            return {
                "status": "accepted",
                "location": response.headers.get("Location", ""),
                "message": BundleAPIMessage.REQUEST_ACCEPTED,
            }

        # Handle 204 responses (no content)
        if response.status_code == HTTPStatus.NO_CONTENT:
            return {"status": "success", "message": BundleAPIMessage.OPERATION_SUCCESS}

        # Try to parse JSON response
        try:
            json_data: dict[str, Any] = response.json()
            return json_data
        except ValueError:
            # Request was successful but returned non-JSON response - handle gracefully
            return {"status": "success", "message": BundleAPIMessage.OPERATION_SUCCESS}

    def _format_http_error(self, error: requests.exceptions.HTTPError, method: str, url: str) -> str:
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

    def create_bundle(self, bundle_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new bundle via the API.

        Args:
            bundle_data: Bundle data containing title and content list

        Returns:
            API response data
        """
        return self._make_request("POST", "/bundles", data=bundle_data)

    def update_bundle(self, bundle_id: str, bundle_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing bundle via the API.

        Args:
            bundle_id: The ID of the bundle to update
            bundle_data: Updated bundle data

        Returns:
            API response data
        """
        return self._make_request("PUT", f"/bundles/{bundle_id}", data=bundle_data)

    def update_bundle_state(self, bundle_id: str, state: str) -> dict[str, Any]:
        """Update the state of a bundle via the API.

        Args:
            bundle_id: The ID of the bundle to update
            state: New state for the bundle (DRAFT, IN_REVIEW, APPROVED, PUBLISHED)

        Returns:
            API response data
        """
        # The swagger spec expects a JSON object with a 'state' field
        return self._make_request("PUT", f"/bundles/{bundle_id}/state", data={"state": state})

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

    def get_bundle_contents(self, bundle_id: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Get the list of contents for a specific bundle.

        Args:
            bundle_id: The ID of the bundle to get contents for.
            limit: The maximum number of items to return. Defaults to 20.
            offset: The starting index of the items to return. Defaults to 0.

        Returns:
            API response data containing the list of contents.
        """
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        if offset < 0:
            raise ValueError("offset must be a non-negative integer")

        params: dict[str, str] = {"limit": str(limit), "offset": str(offset)}
        return self._make_request("GET", f"/bundles/{bundle_id}/contents", params=params)

    def delete_bundle(self, bundle_id: str) -> dict[str, Any]:
        """Delete a bundle via the API.

        Args:
            bundle_id: The ID of the bundle to delete

        Returns:
            API response data
        """
        return self._make_request("DELETE", f"/bundles/{bundle_id}")

    # Note: Currently unused, but kept for future use
    def get_bundles(self, limit: int = 20, offset: int = 0, publish_date: str | None = None) -> dict[str, Any]:
        """Get a list of all bundles.

        Args:
            limit: The maximum number of items to return. Defaults to 20.
            offset: The starting index of the items to return. Defaults to 0.
            publish_date: Filter bundles by their scheduled publication date.

        Returns:
            API response data containing a list of bundles.
        """
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        if offset < 0:
            raise ValueError("offset must be a non-negative integer")

        params: dict[str, str] = {"limit": str(limit), "offset": str(offset)}
        if publish_date:
            params["publish_date"] = publish_date
        return self._make_request("GET", "/bundles", params=params)

    # Note: Currently unused, but kept for future use
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
        response: Bundle API response containing contents array
        dataset: Dataset instance to find in the response

    Returns:
        The content_id if found, None otherwise
    """
    for item in response.get("contents", []):
        metadata = item.get("metadata", {})
        if (
            metadata.get("dataset_id") == dataset.namespace
            and metadata.get("edition_id") == dataset.edition
            and metadata.get("version_id") == dataset.version
        ):
            content_id = item.get("id")
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
