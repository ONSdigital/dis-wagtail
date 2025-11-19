from django.test import TestCase
from wagtail.blocks import StreamValue

from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset, ONSDataset
from cms.datasets.utils import (
    construct_chooser_dataset_compound_id,
    convert_old_dataset_format,
    deconstruct_chooser_dataset_compound_id,
    extract_edition_from_dataset_url,
    format_datasets_as_document_list,
    get_dataset_for_published_state,
    get_published_from_state,
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
                "title": {"text": lookup_dataset.title, "url": lookup_dataset.url_path},
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
        extracted_version = extract_edition_from_dataset_url(url)
        self.assertIsNone(extracted_version)

        url = ""
        extracted_version = extract_edition_from_dataset_url(url)
        self.assertIsNone(extracted_version)

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

    def test_convert_old_dataset_format_with_bad_data(self):
        new_format_dataset = {
            "dataset_id": None,
            "title": None,
            "description": None,
            "edition": None,
            "latest_version": None,
            "release_date": None,
            "state": None,
        }
        converted_dataset = convert_old_dataset_format({})
        self.assertEqual(converted_dataset, new_format_dataset)

        # Partially wrong data
        converted_dataset = convert_old_dataset_format({"title": "Foobar", "links": "a string instead of dict"})
        partially_formed_dataset = {
            "dataset_id": None,
            "title": "Foobar",
            "description": None,
            "edition": None,
            "latest_version": None,
            "release_date": None,
            "state": None,
        }

        self.assertEqual(converted_dataset, partially_formed_dataset)

        # Partially wrong data with links.latest_version not being a dict
        converted_dataset = convert_old_dataset_format({"title": "Foobar", "links": {"latest_version": "not a dict"}})

        self.assertEqual(converted_dataset, partially_formed_dataset)

    def test_compound_id_construction_and_deconstruction(self):
        dataset_id = "wellbeing-quarterly"
        edition = "september"
        version_id = "9"

        for published in [True, False]:
            with self.subTest(published=published):
                compound_tuple = (dataset_id, edition, version_id, published)
                self.assertEqual(
                    compound_tuple,
                    deconstruct_chooser_dataset_compound_id(
                        construct_chooser_dataset_compound_id(
                            dataset_id=dataset_id,
                            edition=edition,
                            version_id=version_id,
                            published=published,
                        )
                    ),
                )

    def test_deconstruct_compound_id_invalid(self):
        invalid_compound_id = "invalidcompoundidformat"
        with self.assertRaisesRegex(ValueError, f"Invalid compound ID format: {invalid_compound_id}"):
            deconstruct_chooser_dataset_compound_id(invalid_compound_id)

    def test_get_published_from_state(self):
        self.assertTrue(get_published_from_state("published"))
        self.assertTrue(get_published_from_state("PUBLISHED"))

        self.assertFalse(get_published_from_state("draft"))
        self.assertFalse(get_published_from_state("associated"))

    def test_get_dataset_for_published_state(self):
        dataset = ONSDataset(
            id="dataset1",
            title="Test Dataset",
            description="A test dataset",
            edition="2024",
            version="1",
            next=ONSDataset(
                id="dataset1-next",
                title="Test Dataset Next",
                description="Next version of test dataset",
                edition="2025",
                version="1",
            ),
        )

        published_dataset = get_dataset_for_published_state(dataset, True)
        self.assertEqual(published_dataset, dataset)

        unpublished_dataset = get_dataset_for_published_state(dataset, False)
        self.assertEqual(unpublished_dataset, dataset.next)  # pylint: disable=no-member

        # Test when there is no 'next' dataset
        dataset = ONSDataset(
            id="dataset1",
            title="Test Dataset",
            description="A test dataset",
            edition="2024",
            version="1",
        )

        published_dataset = get_dataset_for_published_state(dataset, True)
        self.assertEqual(published_dataset, dataset)
        unpublished_dataset = get_dataset_for_published_state(dataset, False)
        # Since there's no 'next', it should return the original dataset
        self.assertEqual(unpublished_dataset, dataset)
