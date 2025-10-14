from http import HTTPStatus
from unittest.mock import patch

import requests
import responses
from django.conf import settings
from django.test import TestCase

from cms.datasets.models import ONSDataset, ONSDatasetApiQuerySet


class TestONSDatasetApiQuerySet(TestCase):
    @responses.activate
    def test_count_uses_total_count(self):
        responses.add(
            responses.GET, settings.DATASET_EDITIONS_API_URL, json={"total_count": 2, "count": 0, "items": []}
        )
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASET_EDITIONS_API_URL
        api_queryset.pagination_style = "offset-limit"
        self.assertEqual(api_queryset.count(), 2)

    @responses.activate
    def test_count_defaults_to_item_count(self):
        responses.add(
            responses.GET,
            settings.DATASET_EDITIONS_API_URL,
            json={
                "items": [
                    {"dummy": "test"},
                    {"dummy": "test2"},
                ]
            },
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASET_EDITIONS_API_URL
        self.assertEqual(api_queryset.count(), 2)

    def test_with_token_clones_queryset(self):
        """Test that with_token() returns a cloned queryset with token attached."""
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASET_EDITIONS_API_URL
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

    @responses.activate
    def test_fetch_api_response_includes_auth_header(self):
        """Test that fetch_api_response() includes Authorization header when token is set."""
        test_token = "test-token"  # noqa: S105
        responses.add(
            responses.GET,
            settings.DATASET_EDITIONS_API_URL,
            json={"items": [], "total_count": 0},
            match=[responses.matchers.header_matcher({"Authorization": f"Bearer {test_token}"})],
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASET_EDITIONS_API_URL
        api_queryset.token = test_token

        api_queryset.fetch_api_response()

        # If the request was made without the header, responses would raise an error
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_fetch_api_response_without_token(self):
        """Test that fetch_api_response() works without token."""
        responses.add(
            responses.GET,
            settings.DATASET_EDITIONS_API_URL,
            json={"items": [], "total_count": 0},
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASET_EDITIONS_API_URL

        result = api_queryset.fetch_api_response()

        self.assertEqual(result["total_count"], 0)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_fetch_api_response_handles_429_rate_limit(self):
        """Test that 429 rate limit errors are logged and raised."""
        responses.add(
            responses.GET,
            settings.DATASET_EDITIONS_API_URL,
            status=HTTPStatus.TOO_MANY_REQUESTS,
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASET_EDITIONS_API_URL

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaises(requests.exceptions.HTTPError):
                api_queryset.fetch_api_response()

            mock_logger.warning.assert_called_once()
            self.assertIn("Rate limit exceeded", mock_logger.warning.call_args[0][0])

    @responses.activate
    def test_fetch_api_response_handles_5xx_errors(self):
        """Test that 5xx server errors are logged and raised."""
        responses.add(
            responses.GET,
            settings.DATASET_EDITIONS_API_URL,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = settings.DATASET_EDITIONS_API_URL

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaises(requests.exceptions.HTTPError):
                api_queryset.fetch_api_response()

            mock_logger.error.assert_called_once()
            self.assertIn("Server error", mock_logger.error.call_args[0][0])

    @responses.activate
    def test_fetch_api_response_handles_request_exception(self):
        """Test that generic request exceptions are logged and raised."""
        api_queryset = ONSDatasetApiQuerySet()
        api_queryset.base_url = "http://invalid-url-that-will-fail.local"

        with patch("cms.datasets.models.logger") as mock_logger:
            with self.assertRaises(requests.exceptions.RequestException):
                api_queryset.fetch_api_response()

            mock_logger.error.assert_called()
            self.assertIn("Request failed", mock_logger.error.call_args[0][0])


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

        self.assertEqual(dataset.id, "test-static-dataset")  # pylint: disable=no-member
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

    def test_from_query_data_backwards_compatible_with_id(self):
        """Test from_query_data() falls back to 'id' field if 'dataset_id' is missing."""
        response_dataset = {
            "id": "legacy-dataset-id",
            "title": "Legacy Dataset",
            "description": "Legacy description",
            "edition": "q1",
            "latest_version": {"id": "5"},
        }

        dataset = ONSDataset.from_query_data(response_dataset)

        self.assertEqual(dataset.id, "legacy-dataset-id")  # pylint: disable=no-member

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
            settings.DATASET_EDITIONS_API_URL,
            json=response_data,
        )

        datasets = list(ONSDataset.objects.all())  # pylint: disable=no-member

        self.assertEqual(len(datasets), 2)
        self.assertEqual(datasets[0].id, "dataset1")
        self.assertEqual(datasets[0].title, "Dataset 1")
        self.assertEqual(datasets[1].id, "dataset2")
        self.assertEqual(datasets[1].edition, "2024-q1")
