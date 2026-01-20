from datetime import UTC, datetime
from unittest.mock import MagicMock

from django.test import TestCase

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.utils import (
    BundleAPIBundleMetadata,
    build_content_item_for_dataset,
    extract_content_id_from_bundle_response,
    get_bundleable_page_types,
    get_data_admin_action_url,
    get_dataset_preview_key,
    get_language_code_from_page,
    get_pages_in_active_bundles,
    serialize_bundle_content_for_published_release_calendar_page,
)
from cms.core.tests.utils import rebuild_internal_search_index
from cms.methodology.models import MethodologyPage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.models import ReleaseCalendarPage
from cms.standard_pages.models import IndexPage, InformationPage
from cms.topics.models import TopicPage


class BundlesUtilsTestCase(TestCase):
    def test_get_bundleable_page_types(self):
        page_types = get_bundleable_page_types()
        page_types.sort(key=lambda x: x.__name__)
        self.assertListEqual(
            page_types,
            [
                IndexPage,
                InformationPage,
                MethodologyPage,
                ReleaseCalendarPage,
                StatisticalArticlePage,
                TopicPage,
            ],
        )

    def test_get_pages_in_active_bundles(self):
        self.assertListEqual(get_pages_in_active_bundles(), [])

        bundle = BundleFactory()
        published_bundle = BundleFactory(published=True)

        page_in_active_bundle = StatisticalArticlePageFactory()
        page_in_published_bundle = StatisticalArticlePageFactory(parent=page_in_active_bundle.get_parent())
        _page_not_in_bundle = StatisticalArticlePageFactory(parent=page_in_active_bundle.get_parent())

        BundlePageFactory(parent=bundle, page=page_in_active_bundle)
        BundlePageFactory(parent=published_bundle, page=page_in_published_bundle)

        self.assertListEqual(get_pages_in_active_bundles(), [page_in_active_bundle.pk])


class DatasetGetDataAdminActionUrlTests(TestCase):
    """Tests for the get_data_admin_action_url function."""

    def test_get_data_admin_action_url_with_different_actions(self):
        """Test that different actions work correctly."""
        dataset_id = "test-dataset"
        edition_id = "time-series"
        version_id = "2"

        # Test multiple actions

        url = get_data_admin_action_url("edit", dataset_id, edition_id, version_id)
        expected = f"/data-admin/series/{dataset_id}/editions/{edition_id}/versions/{version_id}"
        self.assertEqual(url, expected)

        url = get_data_admin_action_url("preview", dataset_id, edition_id, version_id)
        expected = f"/datasets/{dataset_id}/editions/{edition_id}/versions/{version_id}"
        self.assertEqual(url, expected)


class DatasetContentItemUtilityTests(TestCase):
    """Tests for content item utility functions."""

    def setUp(self):
        # Create a mock dataset object
        self.dataset = type(
            "Dataset",
            (),
            {
                "namespace": "cpih",
                "edition": "time-series",
                "version": 1,
            },
        )()

    def test_build_content_item_for_dataset(self):
        """Test that build_content_item_for_dataset creates the correct structure."""
        content_item = build_content_item_for_dataset(self.dataset)

        expected = {
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": "cpih",
                "edition_id": "time-series",
                "version_id": 1,
            },
            "links": {
                "edit": "/data-admin/series/cpih/editions/time-series/versions/1",
                "preview": "/datasets/cpih/editions/time-series/versions/1",
            },
        }

        self.assertEqual(content_item, expected)

    def test_extract_content_id_from_bundle_response_found(self):
        """Test extracting content_id when the dataset is found in the response."""
        response = {
            "bundle_id": "9e4e3628-fc85-48cd-80ad-e005d9d283ff",
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": "cpih",
                "edition_id": "time-series",
                "title": "Consumer Prices Index",
                "version_id": 1,
            },
            "id": "content-123",
        }

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertEqual(content_id, "content-123")

    def test_extract_content_id_from_bundle_response_not_found(self):
        """Test extracting content_id when the dataset is not found in the response."""
        response = {
            "bundle_id": "9e4e3628-fc85-48cd-80ad-e005d9d283ff",
            "content_type": "DATASET",
            "metadata": {
                "dataset_id": "other-dataset",
                "edition_id": "time-series",
                "title": "Consumer Prices Index",
                "version_id": 1,
            },
            "id": "content-456",
        }

        content_id = extract_content_id_from_bundle_response(response, self.dataset)
        self.assertIsNone(content_id)

    def test_extract_content_id_from_bundle_response_empty_contents(self):
        """Test extracting content_id when the response has no contents."""
        content_id = extract_content_id_from_bundle_response({}, self.dataset)
        self.assertIsNone(content_id)


class BundleAPIBundleMetadataTests(TestCase):
    """Tests for BundleAPIBundleMetadata dataclass."""

    def test_as_dict_returns_all_fields(self):
        """Test that as_dict returns a dictionary with all fields."""
        data = BundleAPIBundleMetadata(
            title="Test Bundle",
            bundle_type="MANUAL",
            state="DRAFT",
            managed_by="WAGTAIL",
            preview_teams=[],
            scheduled_at=None,
        )

        result = data.as_dict()

        expected = {
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "state": "DRAFT",
            "managed_by": "WAGTAIL",
            "preview_teams": [],
            "scheduled_at": None,
        }
        self.assertEqual(result, expected)

    def test_defaults_managed_by_to_wagtail(self):
        """Test that managed_by defaults to WAGTAIL when not provided."""
        data = BundleAPIBundleMetadata(title="Test")

        self.assertEqual(data.managed_by, "WAGTAIL")

    def test_defaults_bundle_type_to_manual_when_no_schedule(self):
        """Test that bundle_type defaults to MANUAL when scheduled_at is None."""
        data = BundleAPIBundleMetadata(title="Test", scheduled_at=None)

        self.assertEqual(data.bundle_type, "MANUAL")

    def test_defaults_bundle_type_to_scheduled_when_date_provided(self):
        """Test that bundle_type defaults to SCHEDULED when scheduled_at has a value."""
        data = BundleAPIBundleMetadata(title="Test", scheduled_at="2025-12-01T10:00:00Z")

        self.assertEqual(data.bundle_type, "SCHEDULED")

    def test_respects_explicit_bundle_type(self):
        """Test that explicitly set bundle_type is not overridden."""
        data = BundleAPIBundleMetadata(
            title="Test",
            bundle_type="MANUAL",
            scheduled_at="2025-12-01T10:00:00Z",
        )

        self.assertEqual(data.bundle_type, "MANUAL")

    def test_normalizes_preview_teams_none_to_empty_list(self):
        """Test that None preview_teams is normalized to empty list."""
        data = BundleAPIBundleMetadata(title="Test", preview_teams=None)

        self.assertEqual(data.preview_teams, [])

    def test_normalizes_preview_teams_sorting_by_id(self):
        """Test that preview_teams are sorted by id for consistent comparison.

        This ensures that [{"id": "b"}, {"id": "a"}] and [{"id": "a"}, {"id": "b"}]
        are treated as equivalent after normalization.
        """
        data = BundleAPIBundleMetadata(
            title="Test",
            preview_teams=[
                {"id": "team-c"},
                {"id": "team-a"},
                {"id": "team-b"},
            ],
        )

        self.assertEqual(
            data.preview_teams,
            [
                {"id": "team-a"},
                {"id": "team-b"},
                {"id": "team-c"},
            ],
        )

    def test_normalizes_scheduled_at_to_utc_isoformat(self):
        """Test that datetime objects are normalized to UTC ISO-8601 format without microseconds."""
        cases = [
            datetime(2025, 12, 1, 10, 30, 45, tzinfo=UTC),  # UTC datetime
            datetime(2025, 12, 1, 10, 30, 45, 123456, tzinfo=UTC),  # UTC with microseconds
            "2025-12-01T10:30:45Z",  # UTC string Zulu
            "2025-12-01T10:30:45.123456Z",  # UTC string Zulu with microseconds
            "2025-12-01T11:30:45+01:00",  # +1 hour offset
            "2025-12-01T10:30:45",  # Naive datetime string (assumed UTC)
        ]

        for case in cases:
            with self.subTest(case=case):
                data = BundleAPIBundleMetadata(title="Test", scheduled_at=case)
                self.assertEqual(data.scheduled_at, "2025-12-01T10:30:45+00:00")

    def test_returns_unparseable_date_string_unchanged(self):
        """Test that invalid date strings are returned unchanged.

        This defensive behavior prevents crashes on malformed API data.
        """
        data = BundleAPIBundleMetadata(title="Test", scheduled_at="invalid-date")

        self.assertEqual(data.scheduled_at, "invalid-date")

    def test_equality_after_normalization(self):
        """Test that two instances with equivalent data are equal after normalization.

        This validates the core purpose of BundleAPIBundleMetadata: enabling reliable
        comparison of bundle metadata from different sources (CMS vs Bundle API).
        """
        data_1 = BundleAPIBundleMetadata(
            title="Test",
            state="DRAFT",
            preview_teams=[{"id": "b"}, {"id": "a"}],
            scheduled_at=datetime(2025, 12, 1, 10, 0, 0, tzinfo=UTC),
        )

        data_2 = BundleAPIBundleMetadata(
            title="Test",
            state="DRAFT",
            preview_teams=[{"id": "a"}, {"id": "b"}],  # Different order
            scheduled_at="2025-12-01T11:00:00+01:00",  # Same instant in +1 offset
        )

        self.assertEqual(data_1.as_dict(), data_2.as_dict())


class BundleAPIBundleMetadataHelperTests(TestCase):
    """Tests for BundleAPIBundleMetadata class methods.

    These tests verify the class methods correctly construct BundleAPIBundleMetadata instances.
    The main normalization testing is in BundleAPIBundleMetadataTests above.

    Tests:
    - from_bundle: Converts CMS Bundle model -> BundleAPIBundleMetadata
    - from_api_response: Converts Bundle API JSON -> BundleAPIBundleMetadata
    """

    def test_from_bundle_creates_normalized_instance(self):
        """Test that from_bundle converts Bundle model to BundleAPIBundleMetadata."""
        bundle = BundleFactory(name="Test Bundle")

        result = BundleAPIBundleMetadata.from_bundle(bundle)

        self.assertIsInstance(result, BundleAPIBundleMetadata)
        self.assertEqual(result.title, "Test Bundle")
        self.assertEqual(result.managed_by, "WAGTAIL")
        self.assertIsNotNone(result.state)

    def test_from_api_response_creates_normalized_instance(self):
        """Test that from_api_response creates BundleAPIBundleMetadata correctly."""
        api_response = {
            "title": "Test Bundle",
            "bundle_type": "MANUAL",
            "state": "DRAFT",
            "managed_by": "WAGTAIL",
            "preview_teams": [{"id": "team1"}],
            "scheduled_at": "2025-12-01T10:00:00Z",
        }

        result = BundleAPIBundleMetadata.from_api_response(api_response)

        self.assertIsInstance(result, BundleAPIBundleMetadata)
        self.assertEqual(result.title, "Test Bundle")
        self.assertEqual(result.bundle_type, "MANUAL")
        self.assertEqual(result.state, "DRAFT")
        self.assertEqual(result.managed_by, "WAGTAIL")
        self.assertEqual(result.preview_teams, [{"id": "team1"}])
        self.assertEqual(result.scheduled_at, "2025-12-01T10:00:00+00:00")

    def test_from_api_response_normalizes_via_dataclass(self):
        """Test that normalization happens via BundleAPIBundleMetadata.__post_init__.

        Verifies that preview_teams=None and microseconds are normalized.
        """
        api_response = {
            "title": "Test",
            "state": "DRAFT",
            "preview_teams": None,
            "scheduled_at": "2025-12-01T10:30:45.123456Z",
        }

        result = BundleAPIBundleMetadata.from_api_response(api_response)

        self.assertEqual(result.preview_teams, [])
        self.assertEqual(result.scheduled_at, "2025-12-01T10:30:45+00:00")


class DatasetPreviewKeyTests(TestCase):
    """Tests for the get_dataset_preview_key function."""

    def test_get_dataset_preview_key_generates_correct_format(self):
        """Test that the function generates the correct preview key format."""
        dataset_id = "cpih"
        edition_id = "time-series"
        version_id = "1"

        key = get_dataset_preview_key(dataset_id, edition_id, version_id)
        expected = "dataset-cpih-time-series-1"

        self.assertEqual(key, expected)


class GetLanguageCodeFromPageTests(TestCase):
    """Tests for the get_language_code_from_page function."""

    def test_normalizes_en_gb_to_en(self):
        """Test that 'en-gb' locale is normalized to 'en'."""
        mock_page = MagicMock()
        mock_page.locale.language_code = "en-gb"

        result = get_language_code_from_page(mock_page)

        self.assertEqual(result, "en")

    def test_returns_cy_unchanged(self):
        """Test that 'cy' (Welsh) locale is returned unchanged."""
        mock_page = MagicMock()
        mock_page.locale.language_code = "cy"

        result = get_language_code_from_page(mock_page)

        self.assertEqual(result, "cy")

    def test_returns_other_locales_unchanged(self):
        """Test that other locale codes are returned unchanged."""
        mock_page = MagicMock()
        mock_page.locale.language_code = "fr"

        result = get_language_code_from_page(mock_page)

        self.assertEqual(result, "fr")


class SerializeBundleContentTranslationTests(TestCase):
    """Tests for translation of section titles in bundle content serialization."""

    def test_english_section_titles(self):
        """Test that section titles are in English when language_code is 'en'."""
        bundle = BundleFactory()
        article = StatisticalArticlePageFactory()
        methodology = MethodologyPageFactory()
        BundlePageFactory(parent=bundle, page=article)
        BundlePageFactory(parent=bundle, page=methodology)

        content = serialize_bundle_content_for_published_release_calendar_page(bundle, language_code="en")

        self.assertEqual(len(content), 2)
        self.assertEqual(content[0]["value"]["title"], "Publications")
        self.assertEqual(content[1]["value"]["title"], "Quality and methodology")

    def test_welsh_section_titles(self):
        """Test that section titles are in Welsh when language_code is 'cy'."""
        bundle = BundleFactory()
        article = StatisticalArticlePageFactory()
        methodology = MethodologyPageFactory()
        BundlePageFactory(parent=bundle, page=article)
        BundlePageFactory(parent=bundle, page=methodology)

        rebuild_internal_search_index()

        content = serialize_bundle_content_for_published_release_calendar_page(bundle, language_code="cy")

        self.assertEqual(len(content), 2)
        self.assertEqual(content[0]["value"]["title"], "Cyhoeddiadau")
        self.assertEqual(content[1]["value"]["title"], "Ansawdd a methodoleg")

    def test_default_language_is_english(self):
        """Test that the default language code is English."""
        bundle = BundleFactory()
        article = StatisticalArticlePageFactory()
        BundlePageFactory(parent=bundle, page=article)

        content = serialize_bundle_content_for_published_release_calendar_page(bundle)

        self.assertEqual(content[0]["value"]["title"], "Publications")
