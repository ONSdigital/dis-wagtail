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
        if dataset.block_type == "manual_link":
            dataset_document = {
                "title": {"text": dataset.value["title"], "url": dataset.value["url"]},
                "metadata": {"object": {"text": "Dataset"}},
                "description": f"<p>{dataset.value['description']}</p>",
            }
        else:
            dataset_document = {
                "title": {"text": dataset.value.title, "url": dataset.value.website_url},
                "metadata": {"object": {"text": "Dataset"}},
                "description": f"<p>{dataset.value.description}</p>",
            }
        dataset_documents.append(dataset_document)

    return dataset_documents
