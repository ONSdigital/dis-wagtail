from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Any

import responses
from django.conf import settings

from cms.datasets.tests.utils import convert_dataset_to_old_format


@contextmanager
def mock_datasets_responses(
    datasets: list[Mapping[str, Any]], with_unpublished: bool = False
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
        mock_responses.get(
            settings.DATASETS_API_EDITIONS_URL,
            json={
                "items": datasets,
                "total_count": len(datasets),
            },
            match_querystring=False,
        )
        # Mock individual dataset detail endpoints
        for dataset in datasets:
            if with_unpublished:
                # This version uses the old format for detail responses with "current" and "next"
                dataset_entry = {
                    "current": convert_dataset_to_old_format(dataset),
                    "next": convert_dataset_to_old_format(
                        {
                            **dataset,
                            "title": dataset["title"] + " unpublished",
                            "latest_version": {
                                "href": dataset["latest_version"]["href"],
                                "id": str(int(dataset["latest_version"]["id"]) + 1),
                            },
                        }
                    ),
                }
            else:
                dataset_entry = dataset
            mock_responses.get(
                f"{settings.DATASETS_API_BASE_URL}/{dataset['dataset_id']}",
                json=dataset_entry,
            )

        yield mock_responses
