from typing import TYPE_CHECKING, Any

from wagtail.blocks import StreamValue

from cms.core.formatting_utils import format_as_document_list_item

if TYPE_CHECKING:
    from cms.taxonomy.models import Topic


def format_time_series_as_document_list(time_series: StreamValue) -> list[dict[str, Any]]:
    """Takes a StreamValue of time series blocks (the value of a StreamField of TimeSeriesStoryBlock).

    Returns the time series in a list of dictionaries in the format required for the ONS Document List design system
    component.
    See: https://service-manual.ons.gov.uk/design-system/components/document-list
    """
    time_series_documents: list = []

    for time_series_block in time_series:
        block_value = time_series_block.value
        time_series_document = format_as_document_list_item(
            title=block_value["title"],
            url=block_value["url"],
            content_type="Time series",
            description=block_value["description"],
        )

        time_series_documents.append(time_series_document)

    return time_series_documents


def get_topic_search_url(topic: Topic, suffix: str) -> str:
    """Returns a formatted search relative URL for a topic."""
    return f"/{topic.slug_path}/{suffix}"
