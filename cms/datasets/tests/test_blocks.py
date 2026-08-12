from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from wagtail.blocks import StreamValue

from cms.datasets.blocks import LATEST_VERSION_DUPLICATE_HINT, DatasetStoryBlock
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
                    self.assertIn("Duplicate datasets are not allowed", error.message)

    def test_duplicate_error_message_names_the_shared_destination(self):
        """The note about versions belongs only on pages linking to an edition, so not here."""
        block = DatasetStoryBlock()
        value = StreamValue(
            block,
            stream_data=[
                ("dataset_lookup", self.lookup_dataset.id),
                ("dataset_lookup", self.lookup_dataset.id),
            ],
        )

        with self.assertRaises(ValidationError) as validation_error:
            block.clean(value)

        for error in validation_error.exception.block_errors.values():
            self.assertIn('"/datasets/1"', error.message)
            self.assertNotIn(LATEST_VERSION_DUPLICATE_HINT.strip(), error.message)

    def test_validation_fails_for_different_editions_of_the_same_dataset(self):
        """Both editions resolve to the series page here, so they are duplicates."""
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
    """Duplicate validation where links resolve to an edition rather than the series page.

    What counts as a duplicate differs from the series page context in TestDatasetStoryBlock,
    because the resolved URL names the edition but not the version.
    """

    def setUp(self):
        # Only the edition affects the resolved URL, so two versions of one edition collide and
        # the April edition does not.
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
        """The chooser lists the version, so the message has to explain why these collide."""
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
        for error in validation_error.exception.block_errors.values():
            self.assertIn('"/datasets/ds/editions/march/versions"', error.message)
            self.assertIn(LATEST_VERSION_DUPLICATE_HINT.strip(), error.message)

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_validation_fails_for_a_manual_link_to_the_resolved_url(self):
        """Each case is the March lookup's destination, written a different way."""
        block = DatasetStoryBlock(link_to_latest_version=True)
        manual_url_cases = [
            "/datasets/ds/editions/march/versions/",
            "/datasets/ds/editions/march/versions",
            "https://example.com/datasets/ds/editions/march/versions/",
        ]

        for manual_url in manual_url_cases:
            with self.subTest(manual_url=manual_url):
                value = StreamValue(
                    block,
                    stream_data=[
                        ("dataset_lookup", self.march_v1.id),
                        ("manual_link", {"title": "Dataset Title", "url": manual_url}),
                    ],
                )

                with self.assertRaises(ValidationError) as validation_error:
                    block.clean(value)

                self.assertEqual(len(validation_error.exception.block_errors), 2)
                for error in validation_error.exception.block_errors.values():
                    self.assertIn("Duplicate datasets are not allowed", error.message)

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_validation_fails_for_manual_links_differing_only_by_a_trailing_slash(self):
        """Covered for arbitrary paths in TestDatasetStoryBlock, repeated for edition URLs."""
        block = DatasetStoryBlock(link_to_latest_version=True)
        value = StreamValue(
            block,
            stream_data=[
                ("manual_link", {"title": "Dataset Title", "url": "/datasets/ds/editions/march/versions/"}),
                ("manual_link", {"title": "Dataset Title", "url": "/datasets/ds/editions/march/versions"}),
            ],
        )

        with self.assertRaises(ValidationError) as validation_error:
            block.clean(value)

        self.assertEqual(len(validation_error.exception.block_errors), 2)
        for error in validation_error.exception.block_errors.values():
            self.assertIn("Duplicate datasets are not allowed", error.message)

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["example.com"])
    def test_validation_passes_for_a_manual_link_to_the_series_page(self):
        """Here the lookup resolves to the edition URL, so the series page is a different place."""
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
