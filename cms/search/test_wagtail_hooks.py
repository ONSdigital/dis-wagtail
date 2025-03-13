from unittest.mock import patch

from django.test import TestCase

from cms.search.wagtail_hooks import EXCLUDED_PAGE_TYPES, page_published, page_unpublished


class MockRequest:
    """Simulates the request passed to the wagtail hook."""

    pass


class MockPage:
    """A minimal Page-like mock."""

    def __init__(self, class_name, url_path="/some/path"):
        self.url_path = url_path
        self.__class__.__name__ = class_name


class WagtailHooksTests(TestCase):
    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_published_excluded_page_type(self, mock_publisher):
        """Pages in EXCLUDED_PAGE_TYPES should not trigger any publish calls."""
        for excluded_type in EXCLUDED_PAGE_TYPES:
            page = MockPage(excluded_type)
            page_published(MockRequest(), page)
            mock_publisher.publish_created_or_updated.assert_not_called()

    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_published_included_page_type(self, mock_publisher):
        """Pages not in EXCLUDED_PAGE_TYPES should trigger
        publisher.publish_created_or_updated().
        """
        page = MockPage("IndexPage")
        page_published(MockRequest(), page)
        mock_publisher.publish_created_or_updated.assert_called_once_with(page)

    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_unpublished_excluded_page_type(self, mock_publisher):
        page = MockPage("ThemePage")
        page_unpublished(MockRequest(), page)
        mock_publisher.publish_deleted.assert_not_called()

    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_unpublished_included_page_type(self, mock_publisher):
        """Non-excluded page triggers publish_deleted()."""
        page = MockPage("InformationPage")
        page_unpublished(MockRequest(), page)
        mock_publisher.publish_deleted.assert_called_once_with(page)
