import re
from typing import Any

from wagtail.blocks import StreamValue

from cms.core.formatting_utils import format_as_document_list_item

EDITIONS_PATTERN = re.compile(r"/editions/([^/]+)/")

COMPOUND_ID_PARTS_COUNT = 3


def format_datasets_as_document_list(datasets: StreamValue) -> list[dict[str, Any]]:
    """Takes a StreamValue of dataset blocks (the value of a StreamField of DatasetStoryBlocks).

    Returns the datasets in a list of dictionaries in the format required for the ONS Document List design system
    component.
    See: https://service-manual.ons.gov.uk/design-system/components/document-list
    """
    dataset_documents: list = []
    for dataset in datasets:
        block_value = dataset.value
        if dataset.block_type == "manual_link":
            dataset_document = format_as_document_list_item(
                title=block_value["title"],
                url=block_value["url"],
                content_type="Dataset",
                description=block_value["description"],
            )
        else:
            dataset_document = format_as_document_list_item(
                title=block_value.title,
                url=block_value.website_url,
                content_type="Dataset",
                description=dataset.value.description,
            )

        dataset_documents.append(dataset_document)

    return dataset_documents


def extract_edition_from_dataset_url(url: str) -> str:
    """Extract the edition from a dataset URL.

    Example URL: /datasets/wellbeing-quarterly/editions/september/versions/9
    This would extract "september" as the edition.

    Raises ValueError if the edition cannot be found in the URL.
    """
    edition_match = EDITIONS_PATTERN.search(url)
    if not edition_match:
        raise ValueError(f"Found invalid dataset URL, missing edition: {url}")
    edition = edition_match.group(1)
    return edition


def convert_old_dataset_format(data: dict[str, Any]) -> dict[str, Any]:
    """Convert dataset data from the old format to the new one.

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

    New format:
    {
      "dataset_id": "test-static-dataset-october-9",
      "title": "testing static september 30th 2",
      "edition": "april",
      "edition_title": "April edition of this dataset",
      "latest_version": {
        "href": "/datasets/test-static-dataset-october-9/editions/april/versions/2",
        "id": "2"
      },
      "release_date": "2025-03-06T14:49:23.354Z",
      "state": "associated",
    }
    """
    latest_version = data.get("links", {}).get("latest_version", {})
    return {
        "dataset_id": data.get("id", ""),
        "title": data.get("title", "Title not provided"),
        "description": data.get("description", "Description not provided"),
        "edition": extract_edition_from_dataset_url(latest_version.get("href", "")),
        "latest_version": latest_version,
        "release_date": data.get("last_updated", ""),
        "state": data.get("state", "associated"),
    }


def construct_dataset_compound_id(*, dataset_id: str, edition: str, version_id: str) -> str:
    """Construct a compound ID for the dataset based on dataset_id, edition, and version_id."""
    return f"{dataset_id},{edition},{version_id}"


def deconstruct_dataset_compound_id(compound_id: str) -> tuple[str, str, str]:
    """Deconstruct a compound ID into its components: dataset_id, edition, and version_id."""
    parts = compound_id.split(",")
    if len(parts) != COMPOUND_ID_PARTS_COUNT:
        raise ValueError(f"Invalid compound ID format: {compound_id}")
    return parts[0], parts[1], parts[2]
