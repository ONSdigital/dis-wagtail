from http import HTTPStatus
from unittest.mock import Mock, patch

import requests
from django.test import TestCase

from cms.bundles.api import DatasetAPIClient, DatasetAPIClientError


class DatasetAPIClientTests(TestCase):
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
        mock_response = self._create_mock_response(
            HTTPStatus.CREATED, {"id": "test-bundle-123", "title": "Test Bundle"}
        )
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        bundle_data = {
            "title": "Test Bundle",
            "content": [{"id": "dataset-1", "type": "dataset"}, {"id": "page-1", "type": "page"}],
        }

        result = client.create_bundle(bundle_data)

        mock_session.request.assert_called_once_with("POST", f"{self.base_url}/bundles", json=bundle_data)
        self.assertEqual(result, {"id": "test-bundle-123", "title": "Test Bundle"})

    @patch("cms.bundles.api.requests.Session")
    def test_create_bundle_accepted_response(self, mock_session_class):
        mock_response = self._create_mock_response(
            HTTPStatus.ACCEPTED, headers={"Location": "/bundles/test-bundle-123/status"}
        )
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        result = client.create_bundle({"title": "Test Bundle", "content": []})

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
        mock_response = self._create_mock_response(HTTPStatus.OK, {"id": "test-bundle-123", "title": "Updated Bundle"})
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        bundle_data = {"title": "Updated Bundle", "content": []}

        result = client.update_bundle("test-bundle-123", bundle_data)

        mock_session.request.assert_called_once_with(
            "PUT", f"{self.base_url}/bundles/test-bundle-123", json=bundle_data
        )
        self.assertEqual(result, {"id": "test-bundle-123", "title": "Updated Bundle"})

    @patch("cms.bundles.api.requests.Session")
    def test_update_bundle_status_success(self, mock_session_class):
        mock_response = self._create_mock_response(HTTPStatus.OK, {"id": "test-bundle-123", "status": "APPROVED"})
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        result = client.update_bundle_status("test-bundle-123", "APPROVED")

        mock_session.request.assert_called_once_with(
            "PUT", f"{self.base_url}/bundles/test-bundle-123/status", json={"status": "APPROVED"}
        )
        self.assertEqual(result, {"id": "test-bundle-123", "status": "APPROVED"})

    @patch("cms.bundles.api.requests.Session")
    def test_delete_bundle_success(self, mock_session_class):
        mock_response = self._create_mock_response(HTTPStatus.NO_CONTENT)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        result = client.delete_bundle("test-bundle-123")

        mock_session.request.assert_called_once_with("DELETE", f"{self.base_url}/bundles/test-bundle-123", json=None)
        self.assertEqual(result, {"status": "success", "message": "Operation completed successfully"})

    @patch("cms.bundles.api.requests.Session")
    def test_get_dataset_status_success(self, mock_session_class):
        mock_response = self._create_mock_response(HTTPStatus.OK, {"id": "dataset-123", "status": "approved"})
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        result = client.get_dataset_status("dataset-123")

        mock_session.request.assert_called_once_with("GET", f"{self.base_url}/datasets/dataset-123/status", json=None)
        self.assertEqual(result, {"id": "dataset-123", "status": "approved"})

    @patch("cms.bundles.api.requests.Session")
    def test_get_bundle_status_success(self, mock_session_class):
        mock_response = self._create_mock_response(HTTPStatus.OK, {"id": "test-bundle-123", "status": "DRAFT"})
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        result = client.get_bundle_status("test-bundle-123")

        mock_session.request.assert_called_once_with(
            "GET", f"{self.base_url}/bundles/test-bundle-123/status", json=None
        )
        self.assertEqual(result, {"id": "test-bundle-123", "status": "DRAFT"})

    @patch("cms.bundles.api.requests.Session")
    def test_http_error_handling(self, mock_session_class):
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.BAD_REQUEST
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session = self._create_mock_session(mock_response)
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        with self.assertRaises(DatasetAPIClientError) as context:
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

        client = DatasetAPIClient(base_url=self.base_url)
        with self.assertRaises(DatasetAPIClientError) as context:
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

        client = DatasetAPIClient(base_url=self.base_url)
        with self.assertRaises(DatasetAPIClientError) as context:
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

        client = DatasetAPIClient(base_url=self.base_url)
        with self.assertRaises(DatasetAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 500 error", str(context.exception))
        self.assertIn("Server Error", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_network_error(self, mock_session_class):
        mock_session = Mock()
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Network error")
        mock_session_class.return_value = mock_session

        client = DatasetAPIClient(base_url=self.base_url)
        with self.assertRaises(DatasetAPIClientError) as context:
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

        client = DatasetAPIClient(base_url=self.base_url)
        result = client.create_bundle({"title": "Test"})

        # Should return success message when JSON parsing fails
        self.assertEqual(result, {"status": "success", "message": "Operation completed successfully"})

    def test_client_initialization_with_default_url(self):
        with patch("cms.bundles.api.settings") as mock_settings:
            mock_settings.ONS_API_BASE_URL = "https://default-api.example.com"

            client = DatasetAPIClient()

            self.assertEqual(client.base_url, "https://default-api.example.com")

    def test_client_initialization_with_custom_url(self):
        client = DatasetAPIClient(base_url="https://custom-api.example.com")

        self.assertEqual(client.base_url, "https://custom-api.example.com")

    def test_client_initialization_with_fallback_url(self):
        with patch("cms.bundles.api.settings") as mock_settings:
            del mock_settings.ONS_API_BASE_URL

            client = DatasetAPIClient()

            self.assertEqual(client.base_url, "https://api.beta.ons.gov.uk/v1")
