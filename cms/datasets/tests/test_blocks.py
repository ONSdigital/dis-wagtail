from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.blocks import StreamValue

from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset


class TestDatasetStoryBlock(TestCase):
    def setUp(self):
        self.lookup_dataset = Dataset.objects.create(
            namespace="1",
            edition="test1_edition",
            version="test_version",
            title="test_title",
            description="test_description",
        )

    def test_validation_fails_on_duplicate_datasets(self):
        block = DatasetStoryBlock()
        dataset_duplicate_url = (
            f"https://example.com/datasets/{self.lookup_dataset.namespace}/editions"
            f"/{self.lookup_dataset.edition}/versions/{self.lookup_dataset.version}"
        )
        stream_data_cases = [
            [
                ("dataset_lookup", self.lookup_dataset.id),
                ("dataset_lookup", self.lookup_dataset.id),
            ],
            [
                ("dataset_lookup", self.lookup_dataset.id),
                ("manual_link", {"url": dataset_duplicate_url}),
            ],
            [
                ("manual_link", {"url": dataset_duplicate_url}),
                ("manual_link", {"url": dataset_duplicate_url}),
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

    def test_successful_validation(self):
        block = DatasetStoryBlock()
        second_dataset = Dataset.objects.create(
            namespace="2",
            edition="test_edition_2",
            version="test_version_2",
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
                ("manual_link", {"url": "https://example.com/datasets/foo/editions/bar/versions/1"}),
            ],
            [
                ("manual_link", {"url": "https://example.com/datasets/foo/editions/bar/versions/1"}),
            ],
            [
                ("manual_link", {"url": "https://example.com/datasets/foo/editions/bar/versions/1"}),
                ("manual_link", {"url": "https://example.com/datasets/spam/editions/eggs/versions/1"}),
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
