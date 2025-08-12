from http import HTTPStatus
from typing import Literal

import requests
import responses
from django.conf import settings
from django.test import TestCase, override_settings

from cms.bundles.clients.api import (
    BundleAPIClient,
    BundleAPIClientError,
    build_content_item_for_dataset,
    extract_content_id_from_bundle_response,
    get_data_admin_action_url,
)


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
class BundleAPIClientTests(TestCase):
    def setUp(self):
        self.base_url = "https://test-api.example.com"

    @responses.activate
    def test_create_bundle_success(self):
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
        responses.post(f"{self.base_url}/bundles", json=mock_response_data, status=HTTPStatus.CREATED)

        client = BundleAPIClient(base_url=self.base_url)
        # Bundle data following Bundle API swagger spec
        bundle_data = {
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
        }

        result = client.create_bundle(bundle_data)

        self.assertEqual(result, mock_response_data)

    @responses.activate
    def test_create_bundle_accepted_response(self):
        responses.post(
            f"{self.base_url}/bundles",
            status=HTTPStatus.ACCEPTED,
            headers={"Location": "/bundles/test-bundle-123/status"},
        )

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

    @responses.activate
    def test_update_bundle_success(self):
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
        responses.put(
            f"{self.base_url}/bundles/test-bundle-123",
            json=mock_response_data,
            status=HTTPStatus.OK,
            headers={"ETag": "updated-etag-123"},
        )

        client = BundleAPIClient(base_url=self.base_url)
        # Bundle data following Bundle API swagger spec
        bundle_data = {
            "title": "Updated Bundle",
            "bundle_type": "MANUAL",
            "preview_teams": [{"id": "team-uuid-1"}],
        }

        result = client.update_bundle("test-bundle-123", bundle_data)

        self.assertEqual(result, mock_response_data)

    @responses.activate
    def test_update_bundle_state_success(self):
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
        endpoint = f"{self.base_url}/bundles/test-bundle-123/state"
        responses.put(
            endpoint, json=mock_response_data, status=HTTPStatus.OK, headers={"ETag": "state-updated-etag-123"}
        )

        client = BundleAPIClient(base_url=self.base_url)
        result = client.update_bundle_state("test-bundle-123", "APPROVED")

        self.assertEqual(result, mock_response_data)
        self.assertTrue(responses.assert_call_count(endpoint, 1))

    @responses.activate
    def test_delete_bundle_success(self):
        responses.delete(f"{self.base_url}/bundles/test-bundle-123", status=HTTPStatus.NO_CONTENT)

        client = BundleAPIClient(base_url=self.base_url)
        result = client.delete_bundle("test-bundle-123")

        self.assertEqual(result, {"status": "success", "message": "Operation completed successfully"})

    @responses.activate
    def test_get_bundle_contents_success(self):
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
        responses.get(
            f"{self.base_url}/bundles/test-bundle-123/contents", json=mock_response_data, status=HTTPStatus.OK
        )

        client = BundleAPIClient(base_url=self.base_url)
        result = client.get_bundle_contents("test-bundle-123")

        self.assertEqual(result, mock_response_data)

    @responses.activate
    def test_get_bundle_contents_empty(self):
        mock_response_data = {"contents": []}
        responses.get(
            f"{self.base_url}/bundles/empty-bundle-123/contents", json=mock_response_data, status=HTTPStatus.OK
        )

        client = BundleAPIClient(base_url=self.base_url)
        result = client.get_bundle_contents("empty-bundle-123")

        self.assertEqual(result, {"contents": []})

    @responses.activate
    def test_get_bundle_contents_not_found(self):
        responses.get(
            f"{self.base_url}/bundles/nonexistent-bundle/contents",
            json={"error": "Bundle not found"},
            status=HTTPStatus.NOT_FOUND,
        )

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.get_bundle_contents("nonexistent-bundle")

        self.assertIn("HTTP 404 error", str(context.exception))
        self.assertIn("Not Found", str(context.exception))

    @responses.activate
    def test_http_error_handling(self):
        responses.post(f"{self.base_url}/bundles", json={"error": "Invalid request"}, status=HTTPStatus.BAD_REQUEST)

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 400 error", str(context.exception))
        self.assertIn("Bad Request", str(context.exception))

    @responses.activate
    def test_unauthorized_error(self):
        responses.post(f"{self.base_url}/bundles", json={"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 401 error", str(context.exception))
        self.assertIn("Unauthorized", str(context.exception))

    @responses.activate
    def test_not_found_error(self):
        responses.delete(
            f"{self.base_url}/bundles/nonexistent-bundle",
            json={"error": "Bundle not found"},
            status=HTTPStatus.NOT_FOUND,
        )

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.delete_bundle("nonexistent-bundle")

        self.assertIn("HTTP 404 error", str(context.exception))
        self.assertIn("Not Found", str(context.exception))

    @responses.activate
    def test_server_error(self):
        responses.post(
            f"{self.base_url}/bundles", json={"error": "Internal server error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR
        )

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("HTTP 500 error", str(context.exception))
        self.assertIn("Server Error", str(context.exception))

    @responses.activate
    def test_network_error(self):
        responses.post(f"{self.base_url}/bundles", body=requests.exceptions.ConnectionError("Network error"))

        client = BundleAPIClient(base_url=self.base_url)
        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("Network error", str(context.exception))

    @responses.activate
    def test_json_parsing_error(self):
        responses.post(f"{self.base_url}/bundles", body="Invalid JSON response", status=HTTPStatus.OK)

        client = BundleAPIClient(base_url=self.base_url)

        with self.assertRaises(BundleAPIClientError) as context:
            client.create_bundle({"title": "Test"})

        self.assertIn("Expecting value: line 1 column 1 (char 0)", str(context.exception))

    def test_client_initialization_with_default_url(self):
        client = BundleAPIClient()
        self.assertEqual(client.base_url, settings.DIS_DATASETS_BUNDLE_BASE_API_URL)

    def test_client_initialization_with_custom_url(self):
        client = BundleAPIClient(base_url="https://custom-api.example.com")
        self.assertEqual(client.base_url, "https://custom-api.example.com")


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
class BundleAPIClientDisabledTests(TestCase):
    def setUp(self):
        self.base_url = "https://test-api.example.com"

    def test_api_disabled_returns_disabled_message(self):
        """Test that API calls return a disabled message when the feature flag is False."""
        client = BundleAPIClient(base_url=self.base_url)

        # Test various API methods
        bundle_data = {"title": "Test Bundle", "content": []}

        result = client.create_bundle(bundle_data)
        self.assertEqual(
            result, {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}
        )

        result = client.update_bundle("test-bundle-123", bundle_data)
        self.assertEqual(
            result, {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}
        )

        result = client.update_bundle_state("test-bundle-123", "APPROVED")
        self.assertEqual(
            result, {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}
        )

        result = client.delete_bundle("test-bundle-123")
        self.assertEqual(
            result, {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}
        )

        result = client.get_bundle_contents("test-bundle-123")
        self.assertEqual(
            result, {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}
        )


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
            "bundle_id": "9e4e3628-fc85-48cd-80ad-e005d9d283ff",
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": "cpih",
                "edition_id": "time-series",
                "title": "Consumer Prices Index",
                "version_id": 1,
            },
            "id": "content-123",
        }

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertEqual(content_id, "content-123")

    def test_extract_content_id_from_bundle_response_not_found(self):
        """Test extracting content_id when the dataset is not found in the response."""
        response = {
            "bundle_id": "9e4e3628-fc85-48cd-80ad-e005d9d283ff",
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": "other-dataset",
                "edition_id": "time-series",
                "title": "Consumer Prices Index",
                "version_id": 1,
            },
            "id": "content-456",
        }

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertIsNone(content_id)

    def test_extract_content_id_from_bundle_response_empty_contents(self):
        """Test extracting content_id when the response has no contents."""
        content_id = extract_content_id_from_bundle_response({}, self.dataset)
        self.assertIsNone(content_id)
