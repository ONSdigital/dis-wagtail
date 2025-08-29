from django.test import TestCase
from wagtail.blocks import StreamValue

from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset
from cms.datasets.utils import format_datasets_as_document_list


class TestUtils(TestCase):
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
