from http import HTTPStatus
from unittest.mock import patch

import requests
import responses
from django.conf import settings
from django.test import TestCase, override_settings

from cms.datasets.models import ONSDataset, ONSDatasetApiQuerySet


class TestONSDatasetApiQuerySet(TestCase):
    @responses.activate
    def test_count_uses_total_count(self):
        responses.add(
            responses.GET, settings.DATASETS_API_EDITIONS_URL, json={"total_count": 2, "count": 0, "items": []}
        )
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL
        api_queryset.pagination_style = "offset-limit"
        self.assertEqual(api_queryset.count(), 2)

    @responses.activate
    def test_count_defaults_to_item_count(self):
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            json={
                "items": [
                    {"dummy": "test"},
                    {"dummy": "test2"},
                ]
            },
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL
        self.assertEqual(api_queryset.count(), 2)

    def test_with_token_clones_queryset(self):
        """Test that with_token() returns a cloned queryset with token attached."""
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL
        test_token = "test-token-123"  # noqa: S105

        cloned = api_queryset.with_token(test_token)

        # Original should not have token
        self.assertIsNone(api_queryset.token)
        # Clone should have token
        self.assertEqual(cloned.token, test_token)
        # Should be different instances
        self.assertIsNot(api_queryset, cloned)

    def test_clone_preserves_token(self):
        """Test that clone() preserves the token attribute."""
        api_queryset = ONSDatasetApiQuerySet()
        test_token = "original-token"  # noqa: S105
        api_queryset.token = test_token

        cloned = api_queryset.clone()

        self.assertEqual(cloned.token, test_token)
        self.assertIsNot(api_queryset, cloned)

    @override_settings(DATASETS_API_DEFAULT_PAGE_SIZE=50)
    def test_run_query_uses_configured_page_size_limit_when_called(self):
        """Test that run_query() uses the configured page size."""
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL
        api_queryset.pagination_style = "offset-limit"

        with patch.object(
            api_queryset, "fetch_api_response", return_value={"items": [], "total_count": 0}
        ) as mock_fetch:
            list(api_queryset.run_query())

            # Check that fetch_api_response was called with limit=50
            called_params = mock_fetch.call_args[1]["params"]
            self.assertEqual(called_params["limit"], 50)

    @responses.activate
    def test_fetch_api_response_includes_auth_header(self):
        """Test that fetch_api_response() includes Authorization header when token is set."""
        test_token = "test-token"  # noqa: S105
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            json={"items": [], "total_count": 0},
            match=[responses.matchers.header_matcher({"Authorization": test_token})],
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL
        api_queryset.token = test_token

        api_queryset.fetch_api_response()

        # If the request was made without the header, responses would raise an error
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_fetch_api_response_without_token(self):
        """Test that fetch_api_response() works without token."""
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            json={"items": [], "total_count": 0},
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL

        result = api_queryset.fetch_api_response()

        self.assertEqual(result["total_count"], 0)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_fetch_api_response_handles_429_rate_limit(self):
        """Test that 429 rate limit errors are logged and raised."""
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaises(requests.exceptions.HTTPError):
                api_queryset.fetch_api_response()

            mock_logger.warning.assert_called_once_with(
                "Rate limit exceeded when fetching datasets", extra={"url": settings.DATASETS_API_EDITIONS_URL}
            )

    @responses.activate
    def test_fetch_api_response_handles_5xx_errors(self):
        """Test that 5xx server errors are logged and raised."""
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaises(requests.exceptions.HTTPError):
                api_queryset.fetch_api_response()

            mock_logger.error.assert_called_once_with(
                "Server error when fetching datasets",
                extra={"url": settings.DATASETS_API_EDITIONS_URL, "status_code": HTTPStatus.INTERNAL_SERVER_ERROR},
            )

    @responses.activate
    def test_fetch_api_response_handles_request_exception(self):
        """Test that generic request exceptions are logged and raised."""
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = "http://invalid-url-that-will-fail.local"

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaises(requests.exceptions.RequestException):
                api_queryset.fetch_api_response()

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            self.assertEqual(call_args[0][0], "Request failed when fetching datasets")
            self.assertIn("url", call_args[1]["extra"])
            self.assertIn("error", call_args[1]["extra"])

    @responses.activate
    def test_fetch_api_response_raises_on_non_dict_response(self):
        """Test that ValueError is raised when API returns non-dict response (e.g., list)."""
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            json=[{"id": "dataset1"}, {"id": "dataset2"}],
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaisesRegex(ValueError, "Invalid API response format, expected a dictionary-like object"):
                api_queryset.fetch_api_response()

            mock_logger.error.assert_called_once_with(
                "Invalid API response format when fetching datasets",
                extra={"url": settings.DATASETS_API_EDITIONS_URL, "params": {}},
            )

    @responses.activate
    def test_fetch_api_response_raises_on_text_response(self):
        """Test that ValueError is raised when API returns non-dict response (e.g., list)."""
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            body="Just a plain text response",
            content_type="text/plain",
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaisesRegex(ValueError, "Failed to parse JSON response from datasets API"):
                api_queryset.fetch_api_response()

            mock_logger.error.assert_called_once_with(
                "Failed to parse JSON response when fetching datasets",
                extra={"url": settings.DATASETS_API_EDITIONS_URL, "params": {}},
            )

    @responses.activate
    def test_fetch_api_response_raises_on_string_response(self):
        """Test that ValueError is raised when API returns a string instead of dict."""
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            body='"just a string"',
            content_type="application/json",
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaises(ValueError) as context:
                api_queryset.fetch_api_response()

            self.assertEqual(str(context.exception), "Invalid API response format, expected a dictionary-like object")
            mock_logger.error.assert_called_once()

    @responses.activate
    def test_fetch_api_response_succeeds_with_valid_dict(self):
        """Test that valid dict response is processed correctly."""
        valid_response = {"items": [], "total_count": 0, "count": 0}
        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            json=valid_response,
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASETS_API_EDITIONS_URL

        result = api_queryset.fetch_api_response()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["count"], 0)


class TestONSDataset(TestCase):
    @responses.activate
    def test_from_query_data_with_new_api_structure(self):
        """Test from_query_data() parses the new /v1/dataset-editions response structure."""
        response_dataset = {
            "dataset_id": "test-static-dataset",
            "title": "testing static edit",
            "description": "Test dataset description",
            "edition": "march",
            "edition_title": "July to September 2022",
            "latest_version": {
                "href": "/datasets/test-static-dataset/editions/march/versions/66",
                "id": "66",
            },
            "release_date": "2025-01-01T00:00:00.000Z",
            "state": "associated",
        }

        dataset = ONSDataset.from_query_data(response_dataset)

        self.assertEqual(dataset.id, "test-static-dataset,march,66,false")  # pylint: disable=no-member
        self.assertEqual(dataset.dataset_id, "test-static-dataset")
        self.assertEqual(dataset.title, "testing static edit")  # pylint: disable=no-member
        self.assertEqual(dataset.description, "Test dataset description")  # pylint: disable=no-member
        self.assertEqual(dataset.edition, "march")  # pylint: disable=no-member
        self.assertEqual(dataset.version, "66")  # pylint: disable=no-member

    def test_from_query_data_with_missing_title(self):
        """Test from_query_data() provides fallback for missing title."""
        response_dataset = {
            "dataset_id": "test-dataset",
            "edition": "q1",
            "latest_version": {"id": "1"},
        }

        dataset = ONSDataset.from_query_data(response_dataset)

        self.assertEqual(dataset.title, "Title not provided")  # pylint: disable=no-member

    def test_from_query_data_with_missing_description(self):
        """Test from_query_data() provides fallback for missing description."""
        response_dataset = {
            "dataset_id": "test-dataset",
            "title": "Test Dataset",
            "edition": "q1",
            "latest_version": {"id": "1"},
        }

        dataset = ONSDataset.from_query_data(response_dataset)

        self.assertEqual(dataset.description, "Description not provided")  # pylint: disable=no-member

    def test_from_query_data_with_missing_version(self):
        """Test from_query_data() provides fallback for missing version."""
        response_dataset = {
            "dataset_id": "test-dataset",
            "title": "Test Dataset",
            "description": "Test description",
            "edition": "q1",
        }

        dataset = ONSDataset.from_query_data(response_dataset)

        self.assertEqual(dataset.version, "1")  # pylint: disable=no-member

    @responses.activate
    def test_queryset_integration_with_new_api(self):
        """Test full integration of queryset with new API response."""
        response_data = {
            "items": [
                {
                    "dataset_id": "dataset1",
                    "title": "Dataset 1",
                    "description": "Description 1",
                    "edition": "2024",
                    "latest_version": {"id": "1"},
                    "state": "associated",
                },
                {
                    "dataset_id": "dataset2",
                    "title": "Dataset 2",
                    "description": "Description 2",
                    "edition": "2024-q1",
                    "latest_version": {"id": "2"},
                    "state": "published",
                },
            ],
            "count": 2,
            "offset": 0,
            "limit": 2,
            "total_count": 2,
        }

        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL,
            json=response_data,
        )

        datasets = list(ONSDataset.objects.all())  # pylint: disable=no-member

        self.assertEqual(len(datasets), 2)
        self.assertEqual(datasets[0].id, "dataset1,2024,1,false")
        self.assertEqual(datasets[0].dataset_id, "dataset1")
        self.assertEqual(datasets[0].title, "Dataset 1")
        self.assertEqual(datasets[0].description, "Description 1")
        self.assertEqual(datasets[0].edition, "2024")
        self.assertEqual(datasets[0].version, "1")
        self.assertEqual(datasets[0].next, {})
        self.assertEqual(datasets[1].id, "dataset2,2024-q1,2,true")
        self.assertEqual(datasets[1].dataset_id, "dataset2")
        self.assertEqual(datasets[1].title, "Dataset 2")
        self.assertEqual(datasets[1].description, "Description 2")
        self.assertEqual(datasets[1].edition, "2024-q1")
        self.assertEqual(datasets[1].version, "2")
        self.assertEqual(datasets[1].next, {})

    @responses.activate
    def test_queryset_with_filter(self):
        """Test that the parameter gets passed correctly when filtering."""
        response_data = {
            "items": [
                {
                    "dataset_id": "dataset1",
                    "title": "Dataset 1",
                    "description": "Description 1",
                    "edition": "2024",
                    "latest_version": {"id": "1"},
                },
                {
                    "dataset_id": "dataset2",
                    "title": "Dataset 2",
                    "description": "Description 2",
                    "edition": "2024-q1",
                    "latest_version": {"id": "2"},
                },
            ],
            "count": 2,
            "offset": 0,
            "limit": 2,
            "total_count": 2,
        }

        responses.add(
            responses.GET,
            settings.DATASETS_API_EDITIONS_URL + "?offset=0&published=false",
            json=response_data,
        )

        datasets = list(ONSDataset.objects.filter(published="false"))  # pylint: disable=no-member

        self.assertEqual(len(datasets), 2)

    @responses.activate
    def test_response_with_old_dataset_format(self):
        """Test that the queryset can handle old dataset format with 'current' and 'next'."""
        old_format_response = {
            "current": {
                "id": "dataset1",
                "title": "Dataset 1",
                "description": "Description 1",
                "links": {
                    "latest_version": {
                        "href": "/datasets/dataset1/editions/2024/versions/1",
                        "id": "1",
                    },
                },
                "state": "published",
            },
            "next": {
                "id": "dataset1",
                "title": "Dataset 1 Unpublished",
                "description": "Description 1 Unpublished",
                "links": {
                    "latest_version": {
                        "href": "/datasets/dataset1/editions/2024/versions/2",
                        "id": "2",
                    },
                },
                "state": "unpublished",
            },
        }

        responses.add(
            responses.GET,
            settings.DATASETS_API_BASE_URL + "/dataset1,2024,2,false",
            json=old_format_response,
        )

        dataset = ONSDataset.objects.get(pk="dataset1,2024,2,false")  # pylint: disable=no-member

        self.assertEqual(dataset.id, "dataset1,2024,1,true")
        self.assertEqual(dataset.dataset_id, "dataset1")
        self.assertEqual(dataset.title, "Dataset 1")
        self.assertEqual(dataset.description, "Description 1")
        self.assertEqual(dataset.edition, "2024")
        self.assertEqual(dataset.version, "1")

        self.assertEqual(dataset.next.title, "Dataset 1 Unpublished")
        self.assertEqual(dataset.next.description, "Description 1 Unpublished")
        self.assertEqual(dataset.next.edition, "2024")
        self.assertEqual(dataset.next.version, "2")

    @responses.activate
    def test_response_with_only_next_version(self):
        """Test that the queryset can handle response with only 'next' version (no published version)."""
        only_next_response = {
            "next": {
                "id": "dataset2",
                "title": "Dataset 2 Unpublished",
                "description": "Description 2 Unpublished",
                "links": {
                    "latest_version": {
                        "href": "/datasets/dataset2/editions/2025/versions/1",
                        "id": "1",
                    },
                },
                "state": "unpublished",
            },
        }

        responses.add(
            responses.GET,
            settings.DATASETS_API_BASE_URL + "/dataset2,2025,1,false",
            json=only_next_response,
        )

        dataset = ONSDataset.objects.get(pk="dataset2,2025,1,false")  # pylint: disable=no-member

        # When there's no published version, the main dataset fields should have placeholder values
        self.assertEqual(dataset.title, "No published version")
        self.assertEqual(dataset.description, "Description not provided")

        # The unpublished version should be in the 'next' field
        self.assertEqual(dataset.next.title, "Dataset 2 Unpublished")
        self.assertEqual(dataset.next.description, "Description 2 Unpublished")
