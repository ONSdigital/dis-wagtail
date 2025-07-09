import logging
from typing import Any, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DatasetAPIClientError(Exception):
    """Base exception for DatasetAPIClient errors."""

    pass


class DatasetAPIClient:
    """Client for interacting with the ONS Dataset API bundle endpoints."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the client with the base URL.

        Args:
            base_url: The base URL for the API. If not provided, uses settings.ONS_API_BASE_URL
        """
        self.base_url = base_url or getattr(settings, "ONS_API_BASE_URL", "https://api.beta.ons.gov.uk/v1")
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
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
            DatasetAPIClientError: For API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, json=data)
            response.raise_for_status()

            # Handle 202 responses (accepted, but processing)
            if response.status_code == 202:
                return {
                    "status": "accepted",
                    "location": response.headers.get("Location", ""),
                    "message": "Request accepted and is being processed",
                }

            # Handle 204 responses (no content)
            if response.status_code == 204:
                return {"status": "success", "message": "Operation completed successfully"}

            # Try to parse JSON response
            try:
                return response.json()
            except ValueError:
                return {"status": "success", "message": "Operation completed successfully"}

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code} error for {method} {url}"
            if e.response.status_code == 400:
                error_msg += ": Bad Request - Invalid data provided"
            elif e.response.status_code == 401:
                error_msg += ": Unauthorized - Invalid authentication"
            elif e.response.status_code == 404:
                error_msg += ": Not Found - Resource not found"
            elif e.response.status_code == 409:
                error_msg += ": Conflict - Resource already exists or conflict"
            elif e.response.status_code >= 500:
                error_msg += ": Server Error - Internal server error"

            logger.error(error_msg)
            raise DatasetAPIClientError(error_msg) from e

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error for {method} {url}: {e!s}"
            logger.error(error_msg)
            raise DatasetAPIClientError(error_msg) from e

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
