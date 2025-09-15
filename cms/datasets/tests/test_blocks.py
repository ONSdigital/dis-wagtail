from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from wagtail.blocks import StreamValue

from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset


class TestDatasetStoryBlock(TestCase):
    def setUp(self):
        self.lookup_dataset = Dataset.objects.create(
            namespace="1",
            edition="test1_edition",
            version=1,
            title="test_title",
            description="test_description",
        )

    @override_settings(ONS_WEBSITE_BASE_URL="https://example.com", ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_validation_fails_on_duplicate_datasets(self):
        block = DatasetStoryBlock()
        dataset_duplicate_url = f"https://example.com/datasets/{self.lookup_dataset.namespace}"
        stream_data_cases = [
            [
                ("dataset_lookup", self.lookup_dataset.id),
                ("dataset_lookup", self.lookup_dataset.id),
            ],
            [
                ("dataset_lookup", self.lookup_dataset.id),
                ("manual_link", {"title": "Dataset Title", "url": dataset_duplicate_url}),
            ],
            [  # Check that the trailing slash is ignored
                ("dataset_lookup", self.lookup_dataset.id),
                ("manual_link", {"title": "Dataset Title", "url": dataset_duplicate_url + "/"}),
            ],
            [
                ("manual_link", {"title": "Dataset Title", "url": dataset_duplicate_url}),
                ("manual_link", {"title": "Dataset Title", "url": dataset_duplicate_url}),
            ],
        ]

        for stream_data in stream_data_cases:
            with self.subTest(stream_data=stream_data):
                value = StreamValue(
                    block,
                    stream_data=stream_data,
                )

                with self.assertRaises(ValidationError) as validation_error:
                    block.clean(value)

                self.assertEqual(len(validation_error.exception.block_errors), len(stream_data))
                for error in validation_error.exception.block_errors.values():
                    self.assertEqual(error.message, "Duplicate datasets are not allowed")

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_successful_validation(self):
        block = DatasetStoryBlock()
        second_dataset = Dataset.objects.create(
            namespace="2",
            edition="test_edition_2",
            version=2,
            title="test_title_2",
            description="test description 2",
        )
        stream_data_cases = [
            [
                ("dataset_lookup", self.lookup_dataset.id),
            ],
            [
                ("dataset_lookup", self.lookup_dataset.id),
                ("dataset_lookup", second_dataset.id),
            ],
            [
                ("dataset_lookup", self.lookup_dataset.id),
                (
                    "manual_link",
                    {"title": "Dataset Title", "url": "https://example.com/datasets/foo/editions/bar/versions/1"},
                ),
            ],
            [
                (
                    "manual_link",
                    {"title": "Dataset Title", "url": "https://example.com/datasets/foo/editions/bar/versions/1"},
                ),
            ],
            [
                (
                    "manual_link",
                    {"title": "Dataset Title", "url": "https://example.com/datasets/foo/editions/bar/versions/1"},
                ),
                (
                    "manual_link",
                    {"title": "Dataset Title", "url": "https://example.com/datasets/spam/editions/eggs/versions/1"},
                ),
            ],
        ]

        for stream_data in stream_data_cases:
            with self.subTest(stream_data=stream_data):
                value = StreamValue(
                    block,
                    stream_data=stream_data,
                )

                # Expect clean to not raise any errors
                block.clean(value)
