from unittest.mock import call, patch

from django.db.models.signals import post_delete
from django.test import TestCase, override_settings
from wagtail.models import Page, PageViewRestriction
from wagtail.signals import page_published, page_slug_changed, page_unpublished, post_page_move

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.models import ReleaseCalendarIndex
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.search.signal_handlers import build_old_descendant_path
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
        cls.included_page = StatisticalArticlePageFactory()

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

    def test_on_page_published_private_page(self):
        """Pages with view restrictions should not trigger publish_created_or_updated."""
        PageViewRestriction.objects.create(page=self.included_page, restriction_type=PageViewRestriction.LOGIN)
        page_published.send(sender=type(self.included_page), instance=self.included_page)
        self.mock_publisher.publish_created_or_updated.assert_not_called()

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

    def test_on_page_unpublished_private_page(self):
        """Pages with view restrictions should not trigger publish_deleted."""
        PageViewRestriction.objects.create(page=self.included_page, restriction_type=PageViewRestriction.LOGIN)
        page_unpublished.send(sender=type(self.included_page), instance=self.included_page)
        self.mock_publisher.publish_deleted.assert_not_called()

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

    def test_on_page_deleted_private_page(self):
        """Pages with view restrictions should not trigger publish_deleted."""
        PageViewRestriction.objects.create(page=self.included_page, restriction_type=PageViewRestriction.LOGIN)
        post_delete.send(sender=type(self.included_page), instance=self.included_page)
        self.mock_publisher.publish_deleted.assert_not_called()

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
                self.mock_publisher.publish_created_or_updated.assert_called_once_with(page, old_url_path="/old-path/")
                self.mock_publisher.publish_created_or_updated.reset_mock()

    def test_on_page_moved_ignores_draft_page(self):
        """Draft pages should not trigger publish_created_or_updated on move."""
        page = StatisticalArticlePageFactory()
        page.live = False
        page.save()
        post_page_move.send(sender=Page, instance=page, url_path_before="/old-path/", url_path_after="/new-path/")
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_moved_ignores_draft_descendant_page(self):
        """Draft pages should not trigger publish_created_or_updated on move."""
        parent_page = ArticleSeriesPageFactory()
        descendant_page = StatisticalArticlePageFactory(parent=parent_page)
        descendant_page.live = False
        descendant_page.save()
        post_page_move.send(
            sender=Page, instance=parent_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )
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
        page = StatisticalArticlePageFactory()
        PageViewRestriction.objects.create(page=page, restriction_type=PageViewRestriction.LOGIN)
        post_page_move.send(sender=Page, instance=page, url_path_before="/old-path/", url_path_after="/new-path/")
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_moved_private_descendant_page(self):
        """Descendant pages with view restrictions should not trigger publish_created_or_updated on move."""
        parent_page = ArticleSeriesPageFactory()
        descendant_page = StatisticalArticlePageFactory(parent=parent_page)
        PageViewRestriction.objects.create(page=descendant_page, restriction_type=PageViewRestriction.LOGIN)

        post_page_move.send(
            sender=Page, instance=parent_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )

        # Expect no search update events published since the descendant is private
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_moved_with_descendants(self):
        """Moving a parent page should trigger publish_created_or_updated for descendants if they are not excluded."""
        topic_page = TopicPageFactory()
        series_page = ArticleSeriesPageFactory(parent=topic_page)
        article_page = StatisticalArticlePageFactory(parent=series_page)
        url_path_before = "/home/old-path/"

        post_page_move.send(
            sender=Page, instance=topic_page, url_path_before=url_path_before, url_path_after=topic_page.url_path
        )

        # Expect only the article page to have search update events published, topic and series pages are excluded
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(
            article_page,
            old_url_path=build_old_descendant_path(
                parent_page=topic_page,
                descendant_page=article_page,
                parent_path_before=url_path_before,
                parent_path_after=topic_page.url_path,
            ),
        )

    def test_on_page_slug_changed(self):
        """Changing the slug of a page should trigger publish_created_or_updated including the old_url_path."""
        # Set up the page with an initial slug and publish it to ensure we have a revision
        page = IndexPageFactory(slug="old-slug")
        page.save_revision().publish()
        self.mock_publisher.publish_created_or_updated.reset_mock()

        page.slug = "new-slug"
        page.save_revision().publish()
        page.refresh_from_db()

        page_before = page.revisions.order_by("-created_at")[1].as_object()

        page_slug_changed.send(sender=type(page), instance=page, instance_before=page_before)

        # Check that the publisher was called twice: once from the publish
        # and once from the slug change, including the old_url_path
        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls(
            (call(page), call(page, old_url_path=page_before.url_path))
        )

    def test_on_page_slug_changed_with_descendant(self):
        """Changing the slug of a page should trigger publish_created_or_updated including the old_url_path."""
        parent_page = IndexPageFactory(slug="old-slug")
        descendant_page = IndexPageFactory(parent=parent_page)
        parent_page.save_revision().publish()

        parent_page.slug = "new-slug"
        parent_page.save_revision().publish()
        parent_page.refresh_from_db()
        descendant_page.refresh_from_db()
        page_before = parent_page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(parent_page), instance=parent_page, instance_before=page_before)

        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls(
            (
                call(parent_page, old_url_path=page_before.url_path),
                call(
                    descendant_page,
                    old_url_path=build_old_descendant_path(
                        parent_page=parent_page,
                        descendant_page=descendant_page,
                        parent_path_before=page_before.url_path,
                        parent_path_after=parent_page.url_path,
                    ),
                ),
            )
        )

    def test_on_page_slug_changed_excluded_descendant(self):
        """Changing the slug of a page should trigger publish_created_or_updated for descendants
        if they are not excluded.
        """
        parent_page = TopicPageFactory(slug="old-slug")  # An excluded parent page
        descendant_page = ArticleSeriesPageFactory(parent=parent_page)
        parent_page.save_revision().publish()
        parent_page.slug = "new-slug"
        parent_page.save_revision().publish()
        parent_page.refresh_from_db()
        descendant_page.refresh_from_db()

        parent_page_before = parent_page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(parent_page), instance=parent_page, instance_before=parent_page_before)

        # The only descendant page is excluded, so no search update events should be published
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_slug_changed_draft_descendant(self):
        """Changing the slug of a page should trigger publish_created_or_updated for descendants
        if they are not excluded.
        """
        parent_page = ArticleSeriesPageFactory(slug="old-slug")  # An excluded parent page
        descendant_page = StatisticalArticlePageFactory(parent=parent_page)
        descendant_page.live = False
        descendant_page.save()
        parent_page.save_revision().publish()
        parent_page.slug = "new-slug"
        parent_page.save_revision().publish()
        parent_page.refresh_from_db()
        descendant_page.refresh_from_db()

        parent_page_before = parent_page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(parent_page), instance=parent_page, instance_before=parent_page_before)

        # The only descendant page is excluded, so no search update events should be published
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_on_page_slug_changed_private_descendant(self):
        """Changing the slug of a page should trigger publish_created_or_updated for descendants
        if they are not excluded.
        """
        parent_page = ArticleSeriesPageFactory(slug="old-slug")  # An excluded parent page
        descendant_page = StatisticalArticlePageFactory(parent=parent_page)
        PageViewRestriction.objects.create(page=descendant_page, restriction_type=PageViewRestriction.LOGIN)
        parent_page.save_revision().publish()
        parent_page.slug = "new-slug"
        parent_page.save_revision().publish()
        parent_page.refresh_from_db()
        descendant_page.refresh_from_db()

        parent_page_before = parent_page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(parent_page), instance=parent_page, instance_before=parent_page_before)

        # The only descendant page is excluded, so no search update events should be published
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    def test_build_old_descendant_path(self):
        parent_page = ArticleSeriesPageFactory(slug="parent-page")
        descendant_page = StatisticalArticlePageFactory(parent=parent_page, slug="descendant-page")

        old_parent_path = "/home/old-parent-page/"
        expected_old_child_path = "/home/old-parent-page/descendant-page/"

        old_child_path = build_old_descendant_path(
            parent_page=parent_page,
            descendant_page=descendant_page,
            parent_path_before=old_parent_path,
            parent_path_after=parent_page.url_path,
        )

        self.assertEqual(old_child_path, expected_old_child_path)

    def test_build_old_descendant_path_broken_path(self):
        """Test building old descendant path where the child structure
        is not prefixed with the new parent path as expected.
        """
        parent_page = ArticleSeriesPageFactory(slug="parent-page")
        descendant_page = StatisticalArticlePageFactory(parent=parent_page, slug="descendant-page")

        with self.assertLogs(logger="cms.search.signal_handlers", level="ERROR") as assert_logger:
            old_descendant_path = build_old_descendant_path(
                parent_page=parent_page,
                descendant_page=descendant_page,
                parent_path_before="/home/old-parent-page/",
                parent_path_after="/unexpected-mismatching-path/",
            )
            self.assertIsNone(old_descendant_path)
            self.assertEqual(len(assert_logger.output), 1)
            error_log = assert_logger.output[0]
            self.assertIn(
                "Found mismatching descendant page url_path while handling page move, cannot build "
                "old URL path to remove from search index.",
                error_log,
            )
