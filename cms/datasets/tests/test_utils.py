from django.test import TestCase
from wagtail.blocks import StreamValue

from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset
from cms.datasets.utils import (
    construct_dataset_compound_id,
    convert_old_dataset_format,
    deconstruct_dataset_compound_id,
    extract_edition_from_dataset_url,
    format_datasets_as_document_list,
)


class TestUtils(TestCase):
    def test_format_datasets_as_document_list(self):
        lookup_dataset = Dataset.objects.create(
            namespace="LOOKUP",
            edition="lookup_edition",
            version=1,
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

    def test_extract_edition_from_dataset_url(self):
        url = "/datasets/wellbeing-quarterly/editions/september/versions/9"
        extracted_edition = extract_edition_from_dataset_url(url)
        self.assertEqual(extracted_edition, "september")

    def test_extract_edition_from_dataset_url_invalid(self):
        url = "/datasets/wellbeing-quarterly/versions/9"  # Missing edition part
        with self.assertRaises(ValueError):
            extract_edition_from_dataset_url(url)

    def test_convert_old_dataset_format(self):
        old_format_dataset = {
            "description": "Seasonally and non seasonally-adjusted quarterly estimates of life satisfaction...",
            "id": "wellbeing-quarterly",
            "last_updated": "2023-12-13T09:40:24.204Z",
            "links": {
                "latest_version": {
                    "href": "/datasets/wellbeing-quarterly/editions/september/versions/9",
                    "id": "9",
                },
            },
            "state": "published",
            "title": "Quarterly personal well-being estimates",
        }

        new_format_dataset = {
            "dataset_id": "wellbeing-quarterly",
            "title": "Quarterly personal well-being estimates",
            "description": "Seasonally and non seasonally-adjusted quarterly estimates of life satisfaction...",
            "edition": "september",
            "latest_version": {
                "href": "/datasets/wellbeing-quarterly/editions/september/versions/9",
                "id": "9",
            },
            "release_date": "2023-12-13T09:40:24.204Z",
            "state": "published",
        }

        converted_dataset = convert_old_dataset_format(old_format_dataset)
        self.assertEqual(converted_dataset, new_format_dataset)

    def test_compound_id_construction_and_deconstruction(self):
        dataset_id = "wellbeing-quarterly"
        edition = "september"
        version_id = "9"

        compound_tuple = (dataset_id, edition, version_id)
        self.assertEqual(
            compound_tuple,
            deconstruct_dataset_compound_id(construct_dataset_compound_id(*compound_tuple)),
        )

    def test_deconstruct_compound_id_invalid(self):
        invalid_compound_id = "invalidcompoundidformat"
        with self.assertRaises(ValueError):
            deconstruct_dataset_compound_id(invalid_compound_id)
