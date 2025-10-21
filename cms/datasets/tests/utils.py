from typing import Any


def convert_dataset_to_old_format(dataset: dict[str, Any]) -> dict[str, Any]:
    """Convert a dataset from the new /v1/dataset-editions format to the old format.

    Old format:
    {
      "description": "Seasonally and non seasonally-adjusted quarterly estimates of life satisfaction...",
      "id": "wellbeing-quarterly",
      "last_updated": "2023-12-13T09:40:24.204Z",
      "links": {
        "latest_version": {
          "href": "https://api.beta.ons.gov.uk/v1/datasets/wellbeing-quarterly/editions/time-series/versions/9",
          "id": "9"
        },
      },
      "state": "published",
      "title": "Quarterly personal well-being estimates",
    }

    NOTE: This should only be used for testing purposes to simulate old-format responses.
    The reverse of this function is implemented in cms.datasets.utils.convert_old_dataset_format.
    """
    old_format = {
        "description": dataset.get("description", "Description not provided"),
        "id": dataset.get("dataset_id", dataset.get("id", "")),
        "last_updated": dataset.get("release_date", ""),
        "links": {
            "latest_version": dataset.get("latest_version", {}),
        },
        "state": dataset.get("state", "associated"),
        "title": dataset.get("title", "Title not provided"),
    }
    return old_format
