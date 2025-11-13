import re
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Any

import responses
from django.conf import settings

from cms.datasets.tests.utils import convert_dataset_to_old_format

TEST_UNPUBLISHED_DATASETS = (
    {
        "dataset_id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "edition": "example-dataset-1",
        "edition_title": "Example Dataset 1",
        "latest_version": {
            "href": "/datasets/example1/editions/example-dataset-1/versions/1",
            "id": "1",
        },
        "release_date": "2025-01-01T00:00:00.000Z",
        "state": "associated",
    },
    {
        "dataset_id": "example2",
        "description": "Second example dataset for functional testing",
        "title": "Personal well-being estimates by local authority",
        "edition": "example-dataset-2",
        "edition_title": "Example Dataset 2",
        "latest_version": {
            "href": "/datasets/example2/editions/example-dataset-2/versions/1",
            "id": "1",
        },
        "release_date": "2025-01-02T00:00:00.000Z",
        "state": "unpublished",
    },
    {
        "dataset_id": "example3",
        "description": "Third example dataset for functional testing",
        "title": "Deaths registered weekly in England and Wales by region",
        "edition": "example-dataset-3",
        "edition_title": "Example Dataset 3",
        "latest_version": {
            "href": "/datasets/example3/editions/example-dataset-3/versions/1",
            "id": "1",
        },
        "release_date": "2025-01-03T00:00:00.000Z",
        "state": "associated",
    },
)

TEST_MIXED_STATES_DATASETS = (
    {
        "dataset_id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "edition": "example-dataset-1",
        "edition_title": "Example Dataset 1",
        "latest_version": {
            "href": "/datasets/example1/editions/example-dataset-1/versions/1",
            "id": "1",
        },
        "release_date": "2025-01-01T00:00:00.000Z",
        "state": "published",
    },
    {
        "dataset_id": "example1",
        "description": "Example dataset for functional testing unpublished",
        "title": "Unpublished Looked Up Dataset",
        "edition": "example-dataset-1",
        "edition_title": "Example Dataset 1",
        "latest_version": {
            "href": "/datasets/example1/editions/example-dataset-1/versions/1",
            "id": "1",
        },
        "release_date": "2025-01-01T00:00:00.000Z",
        "state": "unpublished",
    },
)


def _prepare_datasets_response(datasets: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Prepare the datasets API response format."""
    return {
        "items": datasets,
        "total_count": len(datasets),
    }


@contextmanager
def mock_datasets_responses(
    datasets: list[Mapping[str, Any]], use_old_schema: bool = False
) -> Generator[responses.RequestsMock]:
    """Mock the response from the dataset API, using responses.

    Takes a list of datasets in dictionary json representation and mocks the get calls to both retrieve all datasets
    and potential follow-up calls for each individual dataset.

    Yields the mock responses object, which can be used to make assertions about what exact calls were made.

    Example expected datasets format (matching /v1/dataset-editions API response):
    datasets = [{
        "dataset_id": "example1",
        "title": "Looked Up Dataset",
        "description": "Example dataset for functional testing",
        "edition": "example-dataset-1",
        "edition_title": "Example Dataset 1",
        "latest_version": {
            "href": "/datasets/example1/editions/example-dataset-1/versions/1",
            "id": "1",
        },
        "release_date": "2025-01-01T00:00:00.000Z",
        "state": "associated",
    }]
    """
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock_responses:
        # Mock the list endpoint - need to match with any query parameters
        unpublished_datasets = [d for d in datasets if d["state"] != "published"]
        published_datasets = [d for d in datasets if d["state"] == "published"]

        unpublished_datasets_response = _prepare_datasets_response(unpublished_datasets)
        published_datasets_response = _prepare_datasets_response(published_datasets)

        escaped_editions_url = re.escape(settings.DATASETS_API_EDITIONS_URL)

        # Mock any query string containing published parameter using regex
        mock_responses.get(
            re.compile(rf"{escaped_editions_url}\?.*published=false.*"),
            json=unpublished_datasets_response,
        )

        mock_responses.get(
            re.compile(rf"{escaped_editions_url}\?.*published=true.*"),
            json=published_datasets_response,
        )

        # Mock individual dataset detail endpoints
        for dataset in datasets:
            if use_old_schema:
                # This version uses the old format for detail responses with "current" and "next".
                # Find matching unpublished dataset if exists, otherwise use current dataset.
                unpublished_version = next(
                    (
                        unpublished_dataset
                        for unpublished_dataset in unpublished_datasets
                        if unpublished_dataset["dataset_id"] == dataset["dataset_id"]
                    ),
                    dataset,
                )
                dataset_entry = {
                    "current": convert_dataset_to_old_format(dataset),
                    "next": convert_dataset_to_old_format(unpublished_version),
                }
            else:
                dataset_entry = dataset
            mock_responses.get(
                f"{settings.DATASETS_API_BASE_URL}/{dataset['dataset_id']}",
                json=dataset_entry,
            )

        yield mock_responses
