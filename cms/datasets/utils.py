import re
from typing import TYPE_CHECKING, Any

from wagtail.blocks import StreamValue

from cms.core.formatting_utils import format_as_document_list_item

if TYPE_CHECKING:
    from cms.datasets.models import ONSDataset

EDITIONS_PATTERN = re.compile(r"/editions/([^/]+)/")

COMPOUND_ID_PARTS_COUNT = 4


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
                url=block_value.url_path,
                content_type="Dataset",
                description=dataset.value.description,
            )

        dataset_documents.append(dataset_document)

    return dataset_documents


def extract_edition_from_dataset_url(url: str) -> str | None:
    """Extract the edition from a dataset URL.

    Example URL: /datasets/wellbeing-quarterly/editions/september/versions/9
    This would extract "september" as the edition.

    Returns None if the edition cannot be found in the URL.
    """
    edition_match = EDITIONS_PATTERN.search(url)
    if not edition_match:
        return None
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
    try:
        latest_version = data.get("links", {}).get("latest_version", None)
        edition = extract_edition_from_dataset_url(latest_version.get("href", ""))
    except (AttributeError, ValueError):
        latest_version = None
        edition = None

    return {
        "dataset_id": data.get("id"),
        "title": data.get("title"),
        "description": data.get("description"),
        "edition": edition,
        "latest_version": latest_version,
        "release_date": data.get("last_updated"),
        "state": data.get("state"),
    }


def construct_chooser_dataset_compound_id(*, dataset_id: str, edition: str, version_id: str, published: bool) -> str:
    """Construct the chooser dataset compound ID used by ONSDataset (API data).

    Format: "<dataset_id>,<edition>,<version_id>,<published>"

    The `published` flag is included only to differentiate published and
    unpublished versions when fetching datasets via the Dataset API.
    It does not form part of the local Dataset model’s uniqueness.
    """
    return f"{dataset_id},{edition},{version_id},{str(published).lower()}"


def deconstruct_chooser_dataset_compound_id(compound_id: str) -> tuple[str, str, str, bool]:
    """Deconstruct a chooser dataset compound ID into its components.

    Splits the compound ID string back into: (dataset_id, edition, version_id, published)
    """
    parts = compound_id.split(",")
    if len(parts) != COMPOUND_ID_PARTS_COUNT:
        raise ValueError(f"Invalid compound ID format: {compound_id}")
    return parts[0], parts[1], parts[2], parts[3] == "true"


def get_published_from_state(state: str) -> bool:
    """Determine if the dataset is published based on its state."""
    return state.lower() == "published"


def get_dataset_for_published_state(dataset: ONSDataset, published: bool) -> ONSDataset:
    return dataset if published else dataset.next or dataset
