from http import HTTPStatus
from unittest.mock import patch

import requests
import responses
from django.conf import settings
from django.test import TestCase, override_settings

from cms.bundles.clients.api import (
    BundleAPIClient,
    BundleAPIClientError,
    BundleAPIClientError404,
)


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True, DIS_DATASETS_BUNDLE_API_REQUEST_TIMEOUT_SECONDS=5)
class BundleAPIClientTests(TestCase):
    def setUp(self):
        self.base_url = "https://test-api.example.com"

    def test_init_with_access_token_adds_it_to_session_headers(self):
        client = BundleAPIClient(access_token="test")
        self.assertEqual(client.session.headers["Authorization"], "test")

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
            "created_by": {"email": "publisher@ons.gov.uk"},
            "updated_at": "2025-04-04T07:00:00.000Z",
            "last_updated_by": {"email": "publisher@ons.gov.uk"},
            "scheduled_at": "",
            "managed_by": "WAGTAIL",
            "e_tag": "c7e4b9a2f813d6e5f0a9d3c1e7f8b4a5d6c7e9f0",
            "etag_header": "bundle-etag",
        }
        responses.post(
            f"{self.base_url}/bundles",
            json=mock_response_data,
            status=HTTPStatus.CREATED,
            headers={"ETag": "bundle-etag"},
        )

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
                "etag_header": "",
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
            "items": [],
            "etag_header": "updated-etag-123",
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

        result = client.update_bundle("test-bundle-123", bundle_data=bundle_data, etag="etag")

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
            "created_by": {"email": "publisher@ons.gov.uk"},
            "last_updated_by": {"email": "publisher@ons.gov.uk"},
            "scheduled_at": "2025-04-04T07:00:00.000Z",
            "updated_at": "2025-04-04T07:00:00.000Z",
            "managed_by": "WAGTAIL",
            "e_tag": "c7e4b9a2f813d6e5f0a9d3c1e7f8b4a5d6c7e9f0",
            "etag_header": "state-updated-etag-123",
        }
        endpoint = f"{self.base_url}/bundles/test-bundle-123/state"
        responses.put(
            endpoint, json=mock_response_data, status=HTTPStatus.OK, headers={"ETag": "state-updated-etag-123"}
        )

        client = BundleAPIClient(base_url=self.base_url)
        result = client.update_bundle_state("test-bundle-123", state="APPROVED", etag="etag")

        self.assertEqual(result, mock_response_data)
        self.assertTrue(responses.assert_call_count(endpoint, 1))

    @responses.activate
    def test_delete_bundle_success(self):
        responses.delete(f"{self.base_url}/bundles/test-bundle-123", status=HTTPStatus.NO_CONTENT)
        client = BundleAPIClient(base_url=self.base_url)
        result = client.delete_bundle("test-bundle-123")

        self.assertEqual(
            result, {"status": "success", "message": "Operation completed successfully", "etag_header": ""}
        )

    @responses.activate
    def test_get_bundle_contents_success(self):
        mock_response_data = {
            "items": [
                {
                    "id": "content-123",
                    "content_type": "DATASET",
                    "state": "APPROVED",
                    "metadata": {
                        "dataset_id": "cpih",
                        "edition_id": "time-series",
                        "version_id": 1,
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
                        "version_id": 2,
                    },
                    "links": {
                        "edit": "/edit/datasets/inflation/editions/time-series/versions/2",
                        "preview": "/preview/datasets/inflation/editions/time-series/versions/2",
                    },
                },
            ],
            "count": 2,
            "limit": 100,
            "offset": 0,
            "total_count": 2,
        }
        responses.get(
            f"{self.base_url}/bundles/test-bundle-123/contents",
            json=mock_response_data,
            status=HTTPStatus.OK,
            headers={"ETag": "bundle-etag"},
        )

        client = BundleAPIClient(base_url=self.base_url)
        result = client.get_bundle_contents("test-bundle-123")

        mock_response_data["etag_header"] = "bundle-etag"
        self.assertEqual(result, mock_response_data)

    @responses.activate
    def test_get_bundle_contents_empty(self):
        mock_response_data = {"items": [], "count": 0, "limit": 100, "offset": 0, "total_count": 0}
        responses.get(
            f"{self.base_url}/bundles/empty-bundle-123/contents", json=mock_response_data, status=HTTPStatus.OK
        )

        client = BundleAPIClient(base_url=self.base_url)
        result = client.get_bundle_contents("empty-bundle-123")

        mock_response_data["etag_header"] = ""
        self.assertEqual(result, mock_response_data)

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
        with self.assertRaises(BundleAPIClientError404) as context:
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
        self.assertEqual(client.base_url, settings.DIS_DATASETS_BUNDLE_API_BASE_URL)

    def test_client_initialization_with_custom_url(self):
        client = BundleAPIClient(base_url="https://custom-api.example.com")
        self.assertEqual(client.base_url, "https://custom-api.example.com")

    @responses.activate
    def test_timeout_is_applied_from_settings(self):
        client = BundleAPIClient(base_url=self.base_url)

        responses.get(
            f"{self.base_url}/bundles",
            json={"items": [], "count": 0, "limit": 1, "offset": 0, "total_count": 0},
        )

        with patch.object(client.session, "request", wraps=client.session.request) as mock_request:
            client.get_bundles(limit=1, offset=0)
            _, kwargs = mock_request.call_args
            self.assertEqual(kwargs.get("timeout"), 5)


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

        result = client.update_bundle("test-bundle-123", bundle_data=bundle_data, etag="etag")
        self.assertEqual(
            result, {"status": "disabled", "message": "The CMS integration with the Bundle API is disabled"}
        )

        result = client.update_bundle_state("test-bundle-123", state="APPROVED", etag="etag")
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


@override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
class BundleAPIClientPaginationTests(TestCase):
    def setUp(self):
        self.base_url = "https://test-api.example.com"
        self.bundle_client = BundleAPIClient(base_url=self.base_url)

    @responses.activate
    def test_get_bundle_contents_aggregates_across_pages(self):
        bundle_id = "test-bundle-123"
        page1 = {
            "items": [{"id": "c1"}, {"id": "c2"}],
            "count": 2,
            "limit": 2,
            "offset": 0,
            "total_count": 3,
        }
        page2 = {
            "items": [{"id": "c3"}],
            "count": 1,
            "limit": 2,
            "offset": 2,
            "total_count": 3,
        }
        url = f"{self.base_url}/bundles/{bundle_id}/contents"

        responses.get(
            url,
            json=page1,
            headers={"ETag": "etag-content-1"},
            match=[responses.matchers.query_param_matcher({"limit": "2", "offset": "0"})],
        )
        responses.get(
            url,
            json=page2,
            headers={"ETag": "etag-content-2"},
            match=[responses.matchers.query_param_matcher({"limit": "2", "offset": "2"})],
        )

        result = self.bundle_client.get_bundle_contents(bundle_id, limit=2)

        self.assertEqual([i["id"] for i in result["items"]], ["c1", "c2", "c3"])
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["limit"], 2)
        self.assertEqual(result["offset"], 0)
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["etag_header"], "etag-content-1")
        calls = [c.request.url for c in responses.calls if c.request.url.startswith(url)]
        self.assertEqual(len(calls), 2)

    @responses.activate
    def test_get_bundles_aggregates_and_passes_publish_date(self):
        publish_date = "2025-04-04T07:00:00.000Z"
        page1 = {"items": [{"id": "b1"}], "count": 1, "limit": 1, "offset": 0, "total_count": 2}
        page2 = {"items": [{"id": "b2"}], "count": 1, "limit": 1, "offset": 1, "total_count": 2}
        url = f"{self.base_url}/bundles"

        responses.get(
            url,
            json=page1,
            headers={"ETag": "etag-bundles-1"},
            match=[responses.matchers.query_param_matcher({"limit": "1", "offset": "0", "publish_date": publish_date})],
        )
        responses.get(
            url,
            json=page2,
            headers={"ETag": "etag-bundles-2"},
            match=[responses.matchers.query_param_matcher({"limit": "1", "offset": "1", "publish_date": publish_date})],
        )

        result = self.bundle_client.get_bundles(limit=1, offset=0, publish_date=publish_date)

        self.assertEqual([i["id"] for i in result["items"]], ["b1", "b2"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["total_count"], 2)
        self.assertEqual(result["etag_header"], "etag-bundles-1")
        calls = [c.request.url for c in responses.calls if c.request.url.startswith(url)]
        self.assertEqual(len(calls), 2)

    @responses.activate
    def test_limit_is_clamped_to_max(self):
        bundle_id = "test-bundle-123"

        responses.get(
            f"{self.base_url}/bundles/{bundle_id}/contents",
            json={"items": [{"id": "c1"}], "count": 1, "limit": 1000, "offset": 0, "total_count": 1},
        )

        result = self.bundle_client.get_bundle_contents(bundle_id, limit=5000)
        self.assertEqual(result["limit"], 1000)
        self.assertEqual(result["count"], 1)

    @responses.activate
    def test_start_offset_is_respected(self):
        bundle_id = "test-bundle-123"

        page1 = {
            "items": [{"id": "c3"}],
            "count": 1,
            "limit": 1,
            "offset": 2,
            "total_count": 4,
        }
        page2 = {
            "items": [{"id": "c4"}],
            "count": 1,
            "limit": 1,
            "offset": 3,
            "total_count": 4,
        }
        url = f"{self.base_url}/bundles/{bundle_id}/contents"

        responses.get(
            url,
            json=page1,
            match=[responses.matchers.query_param_matcher({"limit": "1", "offset": "2"})],
        )
        responses.get(
            url,
            json=page2,
            match=[responses.matchers.query_param_matcher({"limit": "1", "offset": "3"})],
        )

        result = self.bundle_client.get_bundle_contents(bundle_id, limit=1, offset=3)
        self.assertEqual([i["id"] for i in result["items"]], ["c4"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["offset"], 0)

    @responses.activate
    def test_default_limit_of_100_is_used_when_not_provided_for_contents(self):
        bundle_id = "test-bundle-123"
        responses.get(
            f"{self.base_url}/bundles/{bundle_id}/contents",
            json={"items": [], "count": 0, "limit": 100, "offset": 0, "total_count": 0},
        )

        result = self.bundle_client.get_bundle_contents(bundle_id)
        self.assertEqual(result["limit"], 100)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total_count"], 0)

    @responses.activate
    def test_limit_below_min_is_clamped_to_one(self):
        bundle_id = "test-bundle-123"
        responses.get(
            f"{self.base_url}/bundles/{bundle_id}/contents",
            json={"items": [{"id": "c1"}], "count": 1, "limit": 1, "offset": 0, "total_count": 1},
        )

        result = self.bundle_client.get_bundle_contents(bundle_id, limit=0)
        self.assertEqual(result["limit"], 1)
        self.assertEqual(result["count"], 1)
