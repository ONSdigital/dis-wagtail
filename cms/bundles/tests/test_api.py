from http import HTTPStatus
from typing import Literal
from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from cms.bundles.api import (
    BundleAPIClient,
    BundleAPIClientError,
    build_content_item_for_dataset,
    extract_content_id_from_bundle_response,
    get_data_admin_action_url,
)


@override_settings(ONS_BUNDLE_API_ENABLED=True)
class BundleAPIClientTests(TestCase):
    def setUp(self):
        self.base_url = "https://test-api.example.com"

    def _create_mock_response(self, status_code=HTTPStatus.OK, json_data=None, headers=None):
        """Helper method to create a mock response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.raise_for_status.return_value = None
        if json_data:
            mock_response.json.return_value = json_data
        if headers:
            mock_response.headers = headers
        return mock_response

    def _create_mock_session(self, mock_response):
        """Helper method to create a mock session."""
        mock_session = Mock()
        mock_session.request.return_value = mock_response
        return mock_session

    @patch("cms.bundles.api.requests.Session")
    def test_create_bundle_success(self, mock_session_class):
        # Mock response following Bundle API swagger spec
        mock_response_data = {
            "id": "test-bundle-123",
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
            "state": "DRAFT",
            "created_at": "2025-07-14T10:30:00.000Z",
            "created_by": "user-uuid-1",
            "contents": [],
        }
        mock_response = self._create_mock_response(HTTPStatus.CREATED, mock_response_data)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        # Bundle data following Bundle API swagger spec
        bundle_data = {
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
        }

        result = client.create_bundle(bundle_data)

        mock_session.request.assert_called_once_with("POST", f"{self.base_url}/bundles", json=bundle_data)
        self.assertEqual(result, mock_response_data)

    @patch("cms.bundles.api.requests.Session")
    def test_create_bundle_accepted_response(self, mock_session_class):
        mock_response = self._create_mock_response(
            HTTPStatus.ACCEPTED, headers={"Location": "/bundles/test-bundle-123/status"}
        )
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        # Bundle data following Bundle API swagger spec
        bundle_data = {
            "title": "Test Bundle",
            "bundle_type": "SCHEDULED",
            "preview_teams": [{"id": "team-uuid-1"}],
            "scheduled_at": "2025-04-04T07:00:00.000Z",
        }
        result = client.create_bundle(bundle_data)

        self.assertEqual(
            result,
            {
                "status": "accepted",
                "location": "/bundles/test-bundle-123/status",
                "message": "Request accepted and is being processed",
            },
        )

    @patch("cms.bundles.api.requests.Session")
    def test_update_bundle_success(self, mock_session_class):
        # Mock response following Bundle API swagger spec
        mock_response_data = {
            "id": "test-bundle-123",
            "title": "Updated Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
            "state": "DRAFT",
            "created_at": "2025-07-14T10:30:00.000Z",
            "created_by": "user-uuid-1",
            "contents": [],
        }
        mock_response = self._create_mock_response(
            HTTPStatus.OK, mock_response_data, headers={"ETag": "updated-etag-123"}
        )
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        # Bundle data following Bundle API swagger spec
        bundle_data = {
            "title": "Updated Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
        }

        result = client.update_bundle("test-bundle-123", bundle_data)

        mock_session.request.assert_called_once_with(
            "PUT", f"{self.base_url}/bundles/test-bundle-123", json=bundle_data
        )
        self.assertEqual(result, mock_response_data)

    @patch("cms.bundles.api.requests.Session")
    def test_update_bundle_state_success(self, mock_session_class):
        # Mock response following Bundle API swagger spec
        mock_response_data = {
            "id": "test-bundle-123",
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
            "state": "APPROVED",
            "created_at": "2025-07-14T10:30:00.000Z",
            "created_by": "user-uuid-1",
            "contents": [],
        }
        mock_response = self._create_mock_response(
            HTTPStatus.OK, mock_response_data, headers={"ETag": "state-updated-etag-123"}
        )
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        result = client.update_bundle_state("test-bundle-123", "APPROVED")

        mock_session.request.assert_called_once_with(
            "PUT", f"{self.base_url}/bundles/test-bundle-123/state", json={"state": "APPROVED"}
        )
        self.assertEqual(result, mock_response_data)

    @patch("cms.bundles.api.requests.Session")
    def test_delete_bundle_success(self, mock_session_class):
        mock_response = self._create_mock_response(HTTPStatus.NO_CONTENT)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        result = client.delete_bundle("test-bundle-123")

        mock_session.request.assert_called_once_with("DELETE", f"{self.base_url}/bundles/test-bundle-123")
        self.assertEqual(result, {"status": "success", "message": "Operation completed successfully"})

    @patch("cms.bundles.api.requests.Session")
    def test_get_bundle_contents_success(self, mock_session_class):
        mock_response_data = {
            "contents": [
                {
                    "id": "content-123",
                    "content_type": "DATASET",
                    "state": "APPROVED",
                    "metadata": {
                        "dataset_id": "cpih",
                        "edition_id": "time-series",
                        "version_id": "1",
                    },
                    "links": {
                        "edit": "/edit/datasets/cpih/editions/time-series/versions/1",
                        "preview": "/preview/datasets/cpih/editions/time-series/versions/1",
                    },
                },
                {
                    "id": "content-456",
                    "content_type": "DATASET",
                    "state": "DRAFT",
                    "metadata": {
                        "dataset_id": "inflation",
                        "edition_id": "time-series",
                        "version_id": "2",
                    },
                    "links": {
                        "edit": "/edit/datasets/inflation/editions/time-series/versions/2",
                        "preview": "/preview/datasets/inflation/editions/time-series/versions/2",
                    },
                },
            ]
        }
        mock_response = self._create_mock_response(HTTPStatus.OK, mock_response_data)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        result = client.get_bundle_contents("test-bundle-123")

        mock_session.request.assert_called_once_with("GET", f"{self.base_url}/bundles/test-bundle-123/contents")
        self.assertEqual(result, mock_response_data)

    @patch("cms.bundles.api.requests.Session")
    def test_get_bundle_contents_empty(self, mock_session_class):
        mock_response_data = {"contents": []}
        mock_response = self._create_mock_response(HTTPStatus.OK, mock_response_data)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        result = client.get_bundle_contents("empty-bundle-123")

        mock_session.request.assert_called_once_with("GET", f"{self.base_url}/bundles/empty-bundle-123/contents")
        self.assertEqual(result, {"contents": []})

    @patch("cms.bundles.api.requests.Session")
    def test_get_bundle_contents_not_found(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.NOT_FOUND
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.get_bundle_contents("nonexistent-bundle")

        self.assertIn("HTTP 404 error", str(context.exception))
        self.assertIn("Not Found", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_get_bundle_status_success(self, mock_session_class):
        mock_response = self._create_mock_response(HTTPStatus.OK, {"id": "test-bundle-123", "status": "DRAFT"})
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        result = client.get_bundle_status("test-bundle-123")

        mock_session.request.assert_called_once_with("GET", f"{self.base_url}/bundles/test-bundle-123/status")
        self.assertEqual(result, {"id": "test-bundle-123", "status": "DRAFT"})

    @patch("cms.bundles.api.requests.Session")
    def test_http_error_handling(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 400 error", str(context.exception))
        self.assertIn("Bad Request", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_unauthorized_error(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.UNAUTHORIZED
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 401 error", str(context.exception))
        self.assertIn("Unauthorized", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_not_found_error(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.NOT_FOUND
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.delete_bundle("nonexistent-bundle")

        self.assertIn("HTTP 404 error", str(context.exception))
        self.assertIn("Not Found", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_server_error(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 500 error", str(context.exception))
        self.assertIn("Server Error", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_network_error(self, mock_session_class):
        mock_session = Mock()
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Network error")
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("Network error", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_json_parsing_error(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = BundleAPIClient(base_url=self.base_url)
        result = client.create_bundle({"title": "Test"})

        # Should return success message when JSON parsing fails
        self.assertEqual(result, {"status": "success", "message": "Operation completed successfully"})

    def test_client_initialization_with_default_url(self):
        with patch("cms.bundles.api.settings") as mock_settings:
            mock_settings.ONS_API_BASE_URL = "https://default-api.example.com"

            client = BundleAPIClient()

            self.assertEqual(client.base_url, "https://default-api.example.com")

    def test_client_initialization_with_custom_url(self):
        client = BundleAPIClient(base_url="https://custom-api.example.com")

        self.assertEqual(client.base_url, "https://custom-api.example.com")

    def test_client_initialization_with_fallback_url(self):
        with patch("cms.bundles.api.settings") as mock_settings:
            # Create a mock settings object without ONS_API_BASE_URL
            mock_settings.ONS_API_BASE_URL = "https://api.beta.ons.gov.uk/v1"

            client = BundleAPIClient()

            self.assertEqual(client.base_url, "https://api.beta.ons.gov.uk/v1")


@override_settings(ONS_BUNDLE_API_ENABLED=False)
class BundleAPIClientDisabledTests(TestCase):
    def setUp(self):
        self.base_url = "https://test-api.example.com"

    def test_api_disabled_returns_disabled_message(self):
        """Test that API calls return a disabled message when the feature flag is False."""
        client = BundleAPIClient(base_url=self.base_url)

        # Test various API methods
        bundle_data = {"title": "Test Bundle", "content": []}

        result = client.create_bundle(bundle_data)
        self.assertEqual(result, {"status": "disabled", "message": "Bundle API is disabled"})

        result = client.update_bundle("test-bundle-123", bundle_data)
        self.assertEqual(result, {"status": "disabled", "message": "Bundle API is disabled"})

        result = client.update_bundle_state("test-bundle-123", "APPROVED")
        self.assertEqual(result, {"status": "disabled", "message": "Bundle API is disabled"})

        result = client.delete_bundle("test-bundle-123")
        self.assertEqual(result, {"status": "disabled", "message": "Bundle API is disabled"})

        result = client.get_bundle_contents("test-bundle-123")
        self.assertEqual(result, {"status": "disabled", "message": "Bundle API is disabled"})

        result = client.get_bundle_status("test-bundle-123")
        self.assertEqual(result, {"status": "disabled", "message": "Bundle API is disabled"})


class GetDataAdminActionUrlTests(TestCase):
    """Tests for the get_data_admin_action_url function."""

    def test_get_data_admin_action_url_with_different_actions(self):
        """Test that different actions work correctly."""
        dataset_id = "test-dataset"
        edition_id = "time-series"
        version_id = "2"

        # Test multiple actions
        actions: Literal["edit", "preview"] = ["edit", "preview"]
        for action in actions:
            url = get_data_admin_action_url(action, dataset_id, edition_id, version_id)
            expected = f"/{action}/datasets/{dataset_id}/editions/{edition_id}/versions/{version_id}"
            self.assertEqual(url, expected)


class ContentItemUtilityTests(TestCase):
    """Tests for content item utility functions."""

    def setUp(self):
        # Create a mock dataset object
        self.dataset = type(
            "Dataset",
            (),
            {
                "namespace": "cpih",
                "edition": "time-series",
                "version": "1",
            },
        )()

    def test_build_content_item_for_dataset(self):
        """Test that build_content_item_for_dataset creates the correct structure."""
        content_item = build_content_item_for_dataset(self.dataset)

        expected = {
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": "cpih",
                "edition_id": "time-series",
                "version_id": "1",
            },
            "links": {
                "edit": "/edit/datasets/cpih/editions/time-series/versions/1",
                "preview": "/preview/datasets/cpih/editions/time-series/versions/1",
            },
        }

        self.assertEqual(content_item, expected)

    def test_extract_content_id_from_bundle_response_found(self):
        """Test extracting content_id when the dataset is found in the response."""
        response = {
            "contents": [
                {
                    "id": "content-123",
                    "metadata": {
                        "dataset_id": "cpih",
                        "edition_id": "time-series",
                        "version_id": "1",
                    },
                },
                {
                    "id": "content-456",
                    "metadata": {
                        "dataset_id": "other-dataset",
                        "edition_id": "time-series",
                        "version_id": "2",
                    },
                },
            ]
        }

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertEqual(content_id, "content-123")

    def test_extract_content_id_from_bundle_response_not_found(self):
        """Test extracting content_id when the dataset is not found in the response."""
        response = {
            "contents": [
                {
                    "id": "content-456",
                    "metadata": {
                        "dataset_id": "other-dataset",
                        "edition_id": "time-series",
                        "version_id": "2",
                    },
                },
            ]
        }

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertIsNone(content_id)

    def test_extract_content_id_from_bundle_response_empty_contents(self):
        """Test extracting content_id when the response has no contents."""
        response = {"contents": []}

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertIsNone(content_id)

    def test_extract_content_id_from_bundle_response_missing_contents(self):
        """Test extracting content_id when the response has no contents key."""
        response = {}

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertIsNone(content_id)
