from typing import Any

from wagtail.blocks import StreamValue

from cms.core.utils import format_as_document_list_item


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
