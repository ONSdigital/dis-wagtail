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
                ("manual_link", {"title": "Dataset Title", "url": "/abc"}),
                ("manual_link", {"title": "Dataset Title", "url": "/abc/"}),
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

    def test_validation_fails_for_different_editions_of_the_same_dataset(self):
        """Topic and related data pages link to the dataset series page, which has no edition in
        its URL. Two different editions of the same dataset therefore both resolve to
        "/datasets/<dataset-id>", making them duplicates even though the editor picked two
        different rows in the chooser.
        """
        block = DatasetStoryBlock()
        other_edition = Dataset.objects.create(
            namespace=self.lookup_dataset.namespace,
            edition="test2_edition",
            version=1,
            title="test_title",
            description="test_description",
        )
        value = StreamValue(
            block,
            stream_data=[
                ("dataset_lookup", self.lookup_dataset.id),
                ("dataset_lookup", other_edition.id),
            ],
        )

        with self.assertRaises(ValidationError) as validation_error:
            block.clean(value)

        self.assertEqual(len(validation_error.exception.block_errors), 2)

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
            [
                (
                    "manual_link",
                    {"title": "Dataset Title", "url": "/datasets/foo/editions/bar/versions/1"},
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


class TestDatasetStoryBlockLinkingToLatestVersion(TestCase):
    """Duplicate validation for pages that link datasets to a specific edition.

    A release is associated with one edition of a dataset, so release calendar pages declare
    their dataset field as DatasetStoryBlock(link_to_latest_version=True) and their looked up
    datasets resolve to "/datasets/<dataset-id>/editions/<edition-id>/versions/" instead of the
    series page. Duplicate validation compares those resolved destinations, so what counts as a
    duplicate differs from the series page context covered by TestDatasetStoryBlock above.

    Note that the resolved URL has no version in it. The website serves the latest published
    version of the edition from that path, which is what makes corrections published after the
    release show up without anyone editing the link.
    """

    def setUp(self):
        # Three chooser selections for one dataset: two versions of the March edition, and the
        # April edition. Only the edition affects the resolved URL, not the version.
        self.march_v1 = Dataset.objects.create(
            namespace="ds",
            edition="march",
            version=1,
            title="March, version 1",
            description="test_description",
        )
        self.march_v2 = Dataset.objects.create(
            namespace="ds",
            edition="march",
            version=2,
            title="March, version 2",
            description="test_description",
        )
        self.april_v1 = Dataset.objects.create(
            namespace="ds",
            edition="april",
            version=1,
            title="April, version 1",
            description="test_description",
        )

    def test_validation_passes_for_different_editions_of_the_same_dataset(self):
        """Two editions of one dataset resolve to different URLs here, so both are allowed.

        This is the main behaviour change: the old validation compared dataset IDs, which made
        this pair a duplicate.
        """
        block = DatasetStoryBlock(link_to_latest_version=True)
        value = StreamValue(
            block,
            stream_data=[
                ("dataset_lookup", self.march_v1.id),
                ("dataset_lookup", self.april_v1.id),
            ],
        )

        # Expect clean to not raise any errors
        block.clean(value)

    def test_validation_fails_for_two_versions_of_the_same_edition(self):
        """Two versions of one edition resolve to the same URL, so they are duplicates.

        The chooser still lists the version, and the CMS still records which version was picked,
        but the version is not part of the resolved URL. Picking March v1 and March v2 on the
        same page therefore produces two identical links, which the editor is told about here.
        """
        block = DatasetStoryBlock(link_to_latest_version=True)
        value = StreamValue(
            block,
            stream_data=[
                ("dataset_lookup", self.march_v1.id),
                ("dataset_lookup", self.march_v2.id),
            ],
        )

        with self.assertRaises(ValidationError) as validation_error:
            block.clean(value)

        self.assertEqual(len(validation_error.exception.block_errors), 2)

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_validation_passes_for_a_manual_link_to_the_series_page(self):
        """A manual link to the series page is allowed alongside a lookup for the same dataset.

        On this page type the lookup resolves to the edition URL, so the series page is a
        genuinely different destination. Under the old dataset ID comparison this pair was
        rejected.
        """
        block = DatasetStoryBlock(link_to_latest_version=True)
        value = StreamValue(
            block,
            stream_data=[
                ("dataset_lookup", self.march_v1.id),
                ("manual_link", {"title": "Dataset Title", "url": "/datasets/ds"}),
            ],
        )

        # Expect clean to not raise any errors
        block.clean(value)
