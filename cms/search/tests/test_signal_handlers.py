from unittest.mock import patch

from django.db.models.signals import post_delete
from django.test import TestCase, override_settings
from wagtail.models import Page, PageViewRestriction
from wagtail.signals import page_published, page_unpublished, post_page_move

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.tests.factories import TopicPageFactory


@override_settings(CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH=True)
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

    def tearDown(self):
        super().tearDown()
        self.mock_publisher.reset_mock()

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
            post_delete.send(sender=Page, instance=page)
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

    @override_settings(CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH=False)
    def test_no_kafka_event_on_unpublish_when_flag_off(self):
        """Test that no Kafka event is sent on unpublish when the flag is off."""
        for page in self.included_pages:
            page_unpublished.send(sender=type(page), instance=page)
            self.mock_publisher.publish_deleted.assert_not_called()

    @override_settings(CMS_SEARCH_NOTIFY_ON_DELETE_OR_UNPUBLISH=False)
    def test_no_kafka_event_on_delete_when_flag_off(self):
        """Test that no Kafka event is sent on delete when the flag is off."""
        for page in self.included_pages:
            post_delete.send(sender=Page, instance=page)
            self.mock_publisher.publish_deleted.assert_not_called()

    def test_on_page_moved_included_pages(self):
        """Test all non excluded pages trigger publish_created_or_updated on move."""
        for page in self.included_pages:
            with self.subTest(page=page):
                post_page_move.send(
                    sender=Page, instance=page, url_path_before="/old-path/", url_path_after="/new-path/"
                )
                self.mock_publisher.publish_created_or_updated.assert_called_once_with(page)
                self.mock_publisher.publish_created_or_updated.reset_mock()

    def test_on_page_moved_ignores_draft_page(self):
        """Draft pages should not trigger publish_created_or_updated on move."""
        page = StatisticalArticlePageFactory()
        page.live = False
        page.save()
        post_page_move.send(sender=Page, instance=page, url_path_before="/old-path/", url_path_after="/new-path/")
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_moved_no_url_change(self):
        """Moves that do not change the URL path should not trigger publish_created_or_updated."""
        page = StatisticalArticlePageFactory()
        post_page_move.send(sender=Page, instance=page, url_path_before="/old-path/", url_path_after="/old-path/")
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_moved_excluded_page(self):
        """Excluded pages should not trigger publish_created_or_updated on move."""
        page = ArticleSeriesPageFactory()
        post_page_move.send(sender=Page, instance=page, url_path_before="/old-path/", url_path_after="/new-path/")
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_moved_private_page(self):
        """Pages with view restrictions should not trigger publish_created_or_updated on move."""
        page = ArticleSeriesPageFactory()
        PageViewRestriction.objects.create(page=page, restriction_type=PageViewRestriction.LOGIN)
        post_page_move.send(sender=Page, instance=page, url_path_before="/old-path/", url_path_after="/new-path/")
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_moved_with_descendants(self):
        """Moving a parent page should trigger publish_created_or_updated for descendants if they are not excluded."""
        topic_page = TopicPageFactory()
        series_page = ArticleSeriesPageFactory(parent=topic_page)
        article_page = StatisticalArticlePageFactory(parent=series_page)

        post_page_move.send(sender=Page, instance=topic_page, url_path_before="/old-path/", url_path_after="/new-path/")

        # Expect only the article page to have search update events published, topic and series pages are excluded
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(article_page)
