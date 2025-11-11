from typing import Literal

from django.test import TestCase

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.utils import (
    build_content_item_for_dataset,
    extract_content_id_from_bundle_response,
    get_bundleable_page_types,
    get_data_admin_action_url,
    get_pages_in_active_bundles,
)
from cms.methodology.models import MethodologyPage
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


class GetDataAdminActionUrlTests(TestCase):
    """Tests for the get_data_admin_action_url function."""

    def test_get_data_admin_action_url_with_different_actions(self):
        """Test that different actions work correctly."""
        dataset_id = "test-dataset"
        edition_id = "time-series"
        version_id = "2"

        # Test multiple actions
        actions: Literal["edit", "preview"] = ["edit", "preview"]
        for action in actions:
            url = get_data_admin_action_url(action, dataset_id, edition_id, version_id)
            expected = f"/{action}/datasets/{dataset_id}/editions/{edition_id}/versions/{version_id}"
            self.assertEqual(url, expected)


class ContentItemUtilityTests(TestCase):
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
                "edit": "/edit/datasets/cpih/editions/time-series/versions/1",
                "preview": "/preview/datasets/cpih/editions/time-series/versions/1",
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
