from unittest.mock import patch

from django.db.models.signals import post_delete
from django.test import TestCase
from wagtail.models import Page
from wagtail.signals import page_published, page_unpublished

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory


class SearchSignalsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Pages that are in SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        cls.excluded_pages = [
            ArticleSeriesPageFactory(),
            HomePage(),
            ReleaseCalendarIndex(),
            ThemePageFactory(),
            TopicPageFactory(),
        ]

        # Pages that are NOT in SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        cls.included_pages = [
            InformationPageFactory(),
            MethodologyPageFactory(),
            ReleaseCalendarPageFactory(),
            StatisticalArticlePageFactory(),
            IndexPageFactory(slug="custom-slug-1"),
        ]

    def setUp(self):
        super().setUp()

        get_publisher_patcher = patch("cms.search.signal_handlers.get_publisher")
        self.mock_publisher = get_publisher_patcher.start().return_value
        self.addCleanup(get_publisher_patcher.stop)

    def test_on_page_published_excluded_page_type(self):
        """Excluded pages should not trigger publish_created_or_updated."""
        for page in self.excluded_pages:
            # Fire the Wagtail page_published signal
            page_published.send(sender=type(page), instance=page)
            self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_published_included_page_type(self):
        """Included pages should trigger publish_created_or_updated."""
        for page in self.included_pages:
            page_published.send(sender=type(page), instance=page)
            self.mock_publisher.publish_created_or_updated.assert_called_once_with(page)
            self.mock_publisher.publish_created_or_updated.reset_mock()

    def test_on_page_unpublished_excluded_page_type(self):
        """Excluded pages should not trigger publish_deleted."""
        for page in self.excluded_pages:
            # Fire the Wagtail page_unpublished signal
            page_unpublished.send(sender=type(page), instance=page)
            self.mock_publisher.publish_deleted.assert_not_called()

    def test_on_page_unpublished_included_page_type(self):
        """Included pages should trigger publish_deleted."""
        for page in self.included_pages:
            page_unpublished.send(sender=type(page), instance=page)
            self.mock_publisher.publish_deleted.assert_called_once_with(page)
            self.mock_publisher.publish_deleted.reset_mock()

    def test_on_page_deleted_excluded_page_type(self):
        """Excluded pages should not trigger publish_deleted on delete."""
        for page in self.excluded_pages:
            # Fire the Django post_delete signal for a Wagtail Page
            post_delete.send(sender=type(page), instance=page)
            self.mock_publisher.publish_deleted.assert_not_called()

    def test_on_page_deleted_included_page_type(self):
        """Included pages should trigger publish_deleted on delete."""
        for page in self.included_pages:
            post_delete.send(sender=Page, instance=page)
            self.mock_publisher.publish_deleted.assert_called_once_with(page)
            self.mock_publisher.publish_deleted.reset_mock()

    def test_on_page_deleted_draft_page(self):
        """Draft pages should not trigger publish_deleted on delete."""
        for page in self.included_pages:
            # Set the page to be a draft (not live)
            page.live = False
            page.save()

            # Fire the Django post_delete signal for a Wagtail Page
            post_delete.send(sender=Page, instance=page)
            self.mock_publisher.publish_deleted.assert_not_called()
