import logging
from http import HTTPStatus
from typing import Any, Optional

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

    def _make_request(self, method: str, endpoint: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Make a request to the API and handle common errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint relative to base_url
            data: Request data for POST/PUT requests

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
            response = self.session.request(method, url, json=data)
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

    def update_bundle_status(self, bundle_id: str, status: str) -> dict[str, Any]:
        """Update the status of a bundle via the API.

        Args:
            bundle_id: The ID of the bundle to update
            status: New status for the bundle

        Returns:
            API response data
        """
        return self._make_request("PUT", f"/bundles/{bundle_id}/status", data={"status": status})

    def delete_bundle(self, bundle_id: str) -> dict[str, Any]:
        """Delete a bundle via the API.

        Args:
            bundle_id: The ID of the bundle to delete

        Returns:
            API response data
        """
        return self._make_request("DELETE", f"/bundles/{bundle_id}")

    def get_dataset_status(self, dataset_id: str) -> dict[str, Any]:
        """Get the status of a dataset via the API.

        Args:
            dataset_id: The ID of the dataset to check

        Returns:
            API response data containing dataset status
        """
        return self._make_request("GET", f"/datasets/{dataset_id}/status")

    def get_bundle_status(self, bundle_id: str) -> dict[str, Any]:
        """Get the status of a bundle via the API.

        Args:
            bundle_id: The ID of the bundle to check

        Returns:
            API response data containing bundle status
        """
        return self._make_request("GET", f"/bundles/{bundle_id}/status")
