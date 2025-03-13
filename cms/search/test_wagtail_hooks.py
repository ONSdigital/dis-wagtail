from unittest.mock import patch

from django.test import TestCase

from cms.search.wagtail_hooks import EXCLUDED_PAGE_TYPES, page_published, page_unpublished

import wagtail.coreutils

from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.home.models import HomePage

# Pages to exclude

# Article series
# Home page
# Release calendar index
# Theme page
# Topic Page

# Pages to include

# Information Page: Topics: TESTED
# Methodology Page: Topics: TESTED
# Release Calendar Page: No topics:
# Index Page: No topics
# Statistical Article: No topics


class WagtailHooksTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_request = wagtail.coreutils.get_dummy_request()

        cls.excluded_factories = [
            ArticleSeriesPageFactory,
            HomePage,
            ReleaseCalendarIndex,
            ThemePageFactory,
            TopicPageFactory,
        ]

        cls.included_factories = [
            InformationPageFactory,
            MethodologyPageFactory,
            ReleaseCalendarPageFactory,
            StatisticalArticlePageFactory,
        ]

        cls.index_page = IndexPageFactory(slug="custom-slug-1")
        cls.included_factories.append(lambda: cls.index_page)

    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_published_excluded_page_type(self, mock_publisher):
        """Pages in EXCLUDED_PAGE_TYPES should not trigger any publish calls."""
        for factory in self.excluded_factories:
            page = factory()
            page_published(self.mock_request, page)
            mock_publisher.publish_created_or_updated.assert_not_called()

    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_published_included_page_type(self, mock_publisher):
        """Pages not in EXCLUDED_PAGE_TYPES should trigger
        publisher.publish_created_or_updated().
        """
        for factory in self.included_factories:
            page = factory()
            page_published(self.mock_request, page)
            mock_publisher.publish_created_or_updated.assert_called_once_with(page)

            mock_publisher.publish_created_or_updated.reset_mock()

    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_unpublished_excluded_page_type(self, mock_publisher):
        """Pages in EXCLUDED_PAGE_TYPES should not trigger any unpublish calls."""
        for factory in self.excluded_factories:
            page = factory()
            page_unpublished(self.mock_request, page)
            mock_publisher.publish_deleted.assert_not_called()

    @patch("cms.search.wagtail_hooks.publisher")
    def test_page_unpublished_included_page_type(self, mock_publisher):
        """Non-excluded page triggers publish_deleted()."""
        for factory in self.included_factories:
            page = factory()
            page_unpublished(self.mock_request, page)
            mock_publisher.publish_deleted.assert_called_once_with(page)

            mock_publisher.publish_deleted.reset_mock()
