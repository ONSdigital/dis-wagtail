from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

import responses

from cms.datasets.models import DATASETS_BASE_API_URL


@contextmanager
def mock_datasets_responses(datasets: list[Mapping[str, Any]]) -> responses.RequestsMock:
    """Mock the response from the dataset API, using responses.
    Takes a list of datasets in dictionary json representation and mocks the get calls to both retrieve all datasets
    and potential follow-up calls for each individual dataset.

    Yields the mock responses object, which can be used to make assertions about what exact calls were made..

    Example expected datasets format:
    datasets = [{
        "id": "example1",
        "description": "Example dataset for functional testing",
        "title": "Looked Up Dataset",
        "version": "1",
        "links": {
            "latest_version": {
                "href": "/datasets/example1/editions/example-dataset-1/versions/1",
                "id": "example1",
            },
        },
    }]
    """
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock_responses:
        mock_responses.add(
            responses.GET,
            DATASETS_BASE_API_URL,
            json={
                "items": datasets,
                "total_count": len(datasets),
            },
        )
        for dataset in datasets:
            mock_responses.add(
                responses.GET,
                f"{DATASETS_BASE_API_URL}/{dataset['id']}",
                json=dataset,
            )

        yield mock_responses
