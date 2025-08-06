from typing import Any

from wagtail.blocks import StreamValue


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
            dataset_document = format_document_list_element(
                title=block_value["title"],
                url=block_value["url"],
                content_type="Dataset",
                description=block_value["description"],
            )
        else:
            dataset_document = format_document_list_element(
                title=block_value.title,
                url=block_value.website_url,
                content_type="Dataset",
                description=dataset.value.description,
            )

        dataset_documents.append(dataset_document)

    return dataset_documents


def format_time_series_as_document_list(time_series: StreamValue) -> list[dict[str, Any]]:
    """Takes a StreamValue of time series blocks (the value of a StreamField of TimeSeriesStoryBlock).

    Returns the time series in a list of dictionaries in the format required for the ONS Document List design system
    component.
    See: https://service-manual.ons.gov.uk/design-system/components/document-list
    """
    time_series_documents: list = []

    for time_series_block in time_series:
        block_value = time_series_block.value
        time_series_document = format_document_list_element(
            title=block_value["title"],
            url=block_value["url"],
            content_type="Time series",
            description=block_value["page_summary"],
        )

        time_series_documents.append(time_series_document)

    return time_series_documents


def format_document_list_element(title: str, url: str, content_type: str, description: str) -> dict[str, Any]:
    """Formats a document list element for the ONS Document List design system component."""
    return {
        "title": {"text": title, "url": url},
        "metadata": {"object": {"text": content_type}},
        "description": f"<p>{description}</p>",
    }
