from unittest.mock import Mock, patch

import requests
from django.test import TestCase

from cms.bundles.api import DatasetAPIClient, DatasetAPIClientError


class DatasetAPIClientTests(TestCase):
    def setUp(self):
        self.client = DatasetAPIClient(base_url="https://test-api.example.com")

    @patch("cms.bundles.api.requests.Session")
    def test_create_bundle_success(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "test-bundle-123", "title": "Test Bundle"}
        mock_session.request.return_value = mock_response

        bundle_data = {
            "title": "Test Bundle",
            "content": [{"id": "dataset-1", "type": "dataset"}, {"id": "page-1", "type": "page"}],
        }

        result = self.client.create_bundle(bundle_data)

        mock_session.request.assert_called_once_with("POST", "https://test-api.example.com/bundles", json=bundle_data)
        self.assertEqual(result, {"id": "test-bundle-123", "title": "Test Bundle"})

    @patch("cms.bundles.api.requests.Session")
    def test_create_bundle_accepted_response(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"Location": "/bundles/test-bundle-123/status"}
        mock_session.request.return_value = mock_response

        bundle_data = {"title": "Test Bundle", "content": []}

        result = self.client.create_bundle(bundle_data)

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
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test-bundle-123", "title": "Updated Bundle"}
        mock_session.request.return_value = mock_response

        bundle_data = {"title": "Updated Bundle", "content": []}

        result = self.client.update_bundle("test-bundle-123", bundle_data)

        mock_session.request.assert_called_once_with(
            "PUT", "https://test-api.example.com/bundles/test-bundle-123", json=bundle_data
        )
        self.assertEqual(result, {"id": "test-bundle-123", "title": "Updated Bundle"})

    @patch("cms.bundles.api.requests.Session")
    def test_update_bundle_status_success(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test-bundle-123", "status": "APPROVED"}
        mock_session.request.return_value = mock_response

        result = self.client.update_bundle_status("test-bundle-123", "APPROVED")

        mock_session.request.assert_called_once_with(
            "PUT", "https://test-api.example.com/bundles/test-bundle-123/status", json={"status": "APPROVED"}
        )
        self.assertEqual(result, {"id": "test-bundle-123", "status": "APPROVED"})

    @patch("cms.bundles.api.requests.Session")
    def test_delete_bundle_success(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 204
        mock_session.request.return_value = mock_response

        result = self.client.delete_bundle("test-bundle-123")

        mock_session.request.assert_called_once_with(
            "DELETE", "https://test-api.example.com/bundles/test-bundle-123", json=None
        )
        self.assertEqual(result, {"status": "success", "message": "Operation completed successfully"})

    @patch("cms.bundles.api.requests.Session")
    def test_get_dataset_status_success(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "dataset-123", "status": "approved"}
        mock_session.request.return_value = mock_response

        result = self.client.get_dataset_status("dataset-123")

        mock_session.request.assert_called_once_with(
            "GET", "https://test-api.example.com/datasets/dataset-123/status", json=None
        )
        self.assertEqual(result, {"id": "dataset-123", "status": "approved"})

    @patch("cms.bundles.api.requests.Session")
    def test_get_bundle_status_success(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test-bundle-123", "status": "DRAFT"}
        mock_session.request.return_value = mock_response

        result = self.client.get_bundle_status("test-bundle-123")

        mock_session.request.assert_called_once_with(
            "GET", "https://test-api.example.com/bundles/test-bundle-123/status", json=None
        )
        self.assertEqual(result, {"id": "test-bundle-123", "status": "DRAFT"})

    @patch("cms.bundles.api.requests.Session")
    def test_http_error_handling(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session.request.return_value = mock_response

        with self.assertRaises(DatasetAPIClientError) as context:
            self.client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 400 error", str(context.exception))
        self.assertIn("Bad Request", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_unauthorized_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session.request.return_value = mock_response

        with self.assertRaises(DatasetAPIClientError) as context:
            self.client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 401 error", str(context.exception))
        self.assertIn("Unauthorized", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_not_found_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session.request.return_value = mock_response

        with self.assertRaises(DatasetAPIClientError) as context:
            self.client.delete_bundle("nonexistent-bundle")

        self.assertIn("HTTP 404 error", str(context.exception))
        self.assertIn("Not Found", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_server_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_session.request.return_value = mock_response

        with self.assertRaises(DatasetAPIClientError) as context:
            self.client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 500 error", str(context.exception))
        self.assertIn("Server Error", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_network_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_session.request.side_effect = requests.exceptions.ConnectionError("Network error")

        with self.assertRaises(DatasetAPIClientError) as context:
            self.client.create_bundle({"title": "Test"})

        self.assertIn("Network error", str(context.exception))

    @patch("cms.bundles.api.requests.Session")
    def test_json_parsing_error(self, mock_session_class):
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_session.request.return_value = mock_response

        result = self.client.create_bundle({"title": "Test"})

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
