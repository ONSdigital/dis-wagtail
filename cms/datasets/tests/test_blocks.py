from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.blocks import StreamValue

from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset


class TestDatasetStoryBlock(TestCase):
    def setUp(self):
        self.dataset = Dataset(
            namespace="1",
            edition="test1_edition",
            version="test_version",
            title="test_title",
            description="test_description",
            url="https://example.com",
        )
        self.dataset.save()

    def test_validation_fails_on_duplicate_datasets(self):
        block = DatasetStoryBlock()
        value = StreamValue(
            block,
            [
                ("dataset_lookup", self.dataset.id),
                ("dataset_lookup", self.dataset.id),
            ],
        )

        with self.assertRaises(ValidationError) as validation_error:
            block.clean(value)

        self.assertEqual(str(validation_error.exception.non_block_errors[0]), "Duplicate datasets are not allowed")

    def test_successful_validation(self):
        block = DatasetStoryBlock()
        value = StreamValue(
            block,
            [
                ("dataset_lookup", self.dataset.id),
            ],
        )

        # Expect clean to not raise any errors
        block.clean(value)
