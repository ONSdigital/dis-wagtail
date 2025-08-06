from django.test import TestCase
from wagtail.blocks import StreamValue

from cms.datasets.blocks import DatasetStoryBlock, TimeSeriesPageStoryBlock
from cms.datasets.models import Dataset
from cms.datasets.utils import (
    format_datasets_as_document_list,
    format_document_list_element,
    format_time_series_as_document_list,
)


class TestUtils(TestCase):
    def test_format_document_list_element(self):
        """Test helper function to format data to match the ONS Document List design system component."""
        title = "Test Dataset"
        url = "https://example.com/dataset"
        content_type = "Dataset"
        description = "This is a test dataset description."

        formatted_element = format_document_list_element(
            title=title, url=url, content_type=content_type, description=description
        )

        expected = {
            "title": {"text": title, "url": url},
            "metadata": {"object": {"text": content_type}},
            "description": f"<p>{description}</p>",
        }

        self.assertEqual(formatted_element, expected)

    def test_format_datasets_as_document_list(self):
        lookup_dataset = Dataset.objects.create(
            namespace="LOOKUP",
            edition="lookup_edition",
            version="lookup_version",
            title="test lookup",
            description="lookup description",
        )
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("dataset_lookup", lookup_dataset),
                ("manual_link", manual_dataset),
            ],
        )

        formatted_datasets = format_datasets_as_document_list(datasets)

        self.assertEqual(len(formatted_datasets), 2)
        self.assertEqual(
            formatted_datasets[0],
            {
                "title": {"text": lookup_dataset.title, "url": lookup_dataset.website_url},
                "metadata": {"object": {"text": "Dataset"}},
                "description": f"<p>{lookup_dataset.description}</p>",
            },
        )
        self.assertEqual(
            formatted_datasets[1],
            {
                "title": {"text": manual_dataset["title"], "url": manual_dataset["url"]},
                "metadata": {"object": {"text": "Dataset"}},
                "description": f"<p>{manual_dataset['description']}</p>",
            },
        )

    def test_format_time_series_as_document_list(self):
        title = "Test Time Series"
        url = "https://example.com/dataset"
        page_summary = "This is a Time Series page summary."

        block_value = {"title": title, "url": url, "page_summary": page_summary}

        time_series_data = StreamValue(
            TimeSeriesPageStoryBlock(),
            stream_data=[
                ("time_series_page_link", block_value),
            ],
        )

        formatted_time_series = format_time_series_as_document_list(time_series_data)

        expected = {
            "title": {"text": title, "url": url},
            "metadata": {"object": {"text": "Time series"}},
            "description": f'<p><div class="rich-text">{page_summary}</div></p>',
        }

        self.assertEqual(len(formatted_time_series), 1)
        self.assertEqual(formatted_time_series[0], expected)
