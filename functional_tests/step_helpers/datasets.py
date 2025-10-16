from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Any

import responses
from django.conf import settings


@contextmanager
def mock_datasets_responses(datasets: list[Mapping[str, Any]]) -> Generator[responses.RequestsMock]:
    """Mock the response from the dataset API, using responses.

    Takes a list of datasets in dictionary json representation and mocks the get calls to both retrieve all datasets
    and potential follow-up calls for each individual dataset.

    Yields the mock responses object, which can be used to make assertions about what exact calls were made.

    Example expected datasets format:
    datasets = [{
        "id": "example1",
        "dataset_id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "version": "1",
        "edition": "example-dataset-1",
        "latest_version": {"id": "1"},
    }]
    """
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock_responses:
        # Mock the list endpoint
        mock_responses.get(
            settings.DATASET_EDITIONS_API_URL,
            json={
                "items": datasets,
                "total_count": len(datasets),
            },
        )
        # Mock individual dataset detail endpoints
        for dataset in datasets:
            mock_responses.get(
                f"{settings.DATASET_EDITIONS_API_URL}/{dataset['id']}",
                json=dataset,
            )

        yield mock_responses
