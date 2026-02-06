from unittest.mock import call, patch

from django.db.models.signals import post_delete
from django.test import TestCase, override_settings
from wagtail.models import Locale, Page, PageViewRestriction
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
        ]

        # Pages that are NOT in SEARCH_INDEX_EXCLUDED_PAGE_TYPES
        cls.included_pages = [
            InformationPageFactory(),
            MethodologyPageFactory(),
            ReleaseCalendarPageFactory(),
            StatisticalArticlePageFactory(),
            IndexPageFactory(slug="custom-slug-1"),
            TopicPageFactory(),
        ]
        cls.included_page = StatisticalArticlePageFactory()

        cls.en = Locale.get_default()
        cls.cy = Locale.objects.get(language_code="cy")
        cls.en_page = InformationPageFactory(locale=cls.en)
        cls.cy_page = InformationPageFactory(locale=cls.cy)

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

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_publish_only_english_locale(self):
        page_published.send(sender=type(self.en_page), instance=self.en_page)
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(self.en_page)
        self.mock_publisher.publish_created_or_updated.reset_mock()

        page_published.send(sender=type(self.cy_page), instance=self.cy_page)
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["cy"])
    def test_publish_only_welsh_locale(self):
        page_published.send(sender=type(self.cy_page), instance=self.cy_page)
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(self.cy_page)
        self.mock_publisher.publish_created_or_updated.reset_mock()

        page_published.send(sender=type(self.en_page), instance=self.en_page)
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "cy"])
    def test_publish_both_locales(self):
        page_published.send(sender=type(self.en_page), instance=self.en_page)
        page_published.send(sender=type(self.cy_page), instance=self.cy_page)
        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls([call(self.en_page), call(self.cy_page)])

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_unpublish_only_english_locale(self):
        page_unpublished.send(sender=type(self.en_page), instance=self.en_page)
        self.mock_publisher.publish_deleted.assert_called_once_with(self.en_page)
        self.mock_publisher.publish_deleted.reset_mock()

        page_unpublished.send(sender=type(self.cy_page), instance=self.cy_page)
        self.mock_publisher.publish_deleted.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["cy"])
    def test_unpublish_only_welsh_locale(self):
        page_unpublished.send(sender=type(self.cy_page), instance=self.cy_page)
        self.mock_publisher.publish_deleted.assert_called_once_with(self.cy_page)
        self.mock_publisher.publish_deleted.reset_mock()

        page_unpublished.send(sender=type(self.en_page), instance=self.en_page)
        self.mock_publisher.publish_deleted.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "cy"])
    def test_unpublish_both_locales(self):
        page_unpublished.send(sender=type(self.en_page), instance=self.en_page)
        page_unpublished.send(sender=type(self.cy_page), instance=self.cy_page)
        self.assertEqual(self.mock_publisher.publish_deleted.call_count, 2)
        self.mock_publisher.publish_deleted.assert_has_calls([call(self.en_page), call(self.cy_page)])

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_delete_only_english_locale(self):
        post_delete.send(sender=Page, instance=self.en_page)
        self.mock_publisher.publish_deleted.assert_called_once_with(self.en_page)
        self.mock_publisher.publish_deleted.reset_mock()

        post_delete.send(sender=Page, instance=self.cy_page)
        self.mock_publisher.publish_deleted.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["cy"])
    def test_delete_only_welsh_locale(self):
        post_delete.send(sender=Page, instance=self.cy_page)
        self.mock_publisher.publish_deleted.assert_called_once_with(self.cy_page)
        self.mock_publisher.publish_deleted.reset_mock()

        post_delete.send(sender=Page, instance=self.en_page)
        self.mock_publisher.publish_deleted.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "cy"])
    def test_delete_both_locales(self):
        post_delete.send(sender=Page, instance=self.en_page)
        post_delete.send(sender=Page, instance=self.cy_page)
        self.assertEqual(self.mock_publisher.publish_deleted.call_count, 2)
        self.mock_publisher.publish_deleted.assert_has_calls([call(self.en_page), call(self.cy_page)])

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_move_only_english_locale(self):
        post_page_move.send(
            sender=Page, instance=self.en_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(self.en_page, old_url_path="/old-path/")
        self.mock_publisher.publish_created_or_updated.reset_mock()

        post_page_move.send(
            sender=Page, instance=self.cy_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["cy"])
    def test_move_only_welsh_locale(self):
        post_page_move.send(
            sender=Page, instance=self.cy_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(self.cy_page, old_url_path="/old-path/")
        self.mock_publisher.publish_created_or_updated.reset_mock()

        post_page_move.send(
            sender=Page, instance=self.en_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )
        self.mock_publisher.publish_created_or_updated.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "cy"])
    def test_move_both_locales(self):
        post_page_move.send(
            sender=Page, instance=self.en_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )
        post_page_move.send(
            sender=Page, instance=self.cy_page, url_path_before="/old-path/", url_path_after="/new-path/"
        )
        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls(
            [call(self.en_page, old_url_path="/old-path/"), call(self.cy_page, old_url_path="/old-path/")]
        )

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_publish_only_english_with_welsh_alias(self):
        # Create EN source + CY alias to mirror tree sync
        en_page = InformationPageFactory(locale=self.en, title="EN source")
        cy_alias = en_page.copy_for_translation(locale=self.cy, copy_parents=True, alias=True)

        # Fire publish for both
        page_published.send(sender=type(en_page), instance=en_page)
        page_published.send(sender=type(cy_alias), instance=cy_alias)

        # Expect only English to publish
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(en_page)

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "cy"])
    def test_publish_both_locales_with_welsh_alias(self):
        en_page = InformationPageFactory(locale=self.en, title="EN source")
        cy_alias = en_page.copy_for_translation(locale=self.cy, copy_parents=True, alias=True)

        page_published.send(sender=type(en_page), instance=en_page)
        page_published.send(sender=type(cy_alias), instance=cy_alias)

        # Expect both published calls
        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls([call(en_page), call(cy_alias)])

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_slug_changed_only_english_locale(self):
        page = IndexPageFactory(locale=self.en, slug="old-slug-en")
        page.save_revision().publish()
        page.slug = "new-slug-en"
        page.save_revision().publish()
        page.refresh_from_db()
        page_before = page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(page), instance=page, instance_before=page_before)

        self.mock_publisher.publish_created_or_updated.assert_called_once_with(page, old_url_path=page_before.url_path)

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_slug_changed_welsh_ignored_when_only_english_locale(self):
        page = IndexPageFactory(locale=self.cy, slug="old-slug-cy")
        page.save_revision().publish()
        page.slug = "new-slug-cy"
        page.save_revision().publish()
        page.refresh_from_db()
        page_before = page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(page), instance=page, instance_before=page_before)

        self.mock_publisher.publish_created_or_updated.assert_not_called()

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["cy"])
    def test_slug_changed_only_welsh_locale(self):
        page = IndexPageFactory(locale=self.cy, slug="old-slug-cy")
        page.save_revision().publish()
        page.slug = "new-slug-cy"
        page.save_revision().publish()
        page.refresh_from_db()
        page_before = page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(page), instance=page, instance_before=page_before)

        self.mock_publisher.publish_created_or_updated.assert_called_once_with(page, old_url_path=page_before.url_path)

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "cy"])
    def test_slug_changed_both_locales(self):
        en_page = IndexPageFactory(locale=self.en, slug="old-en")
        cy_page = IndexPageFactory(locale=self.cy, slug="old-cy")
        en_page.save_revision().publish()
        cy_page.save_revision().publish()

        en_page.slug = "new-en"
        cy_page.slug = "new-cy"
        en_page.save_revision().publish()
        cy_page.save_revision().publish()
        en_page.refresh_from_db()
        cy_page.refresh_from_db()

        en_before = en_page.revisions.order_by("-created_at")[1].as_object()
        cy_before = cy_page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(en_page), instance=en_page, instance_before=en_before)
        page_slug_changed.send(sender=type(cy_page), instance=cy_page, instance_before=cy_before)

        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls(
            [
                call(en_page, old_url_path=en_before.url_path),
                call(cy_page, old_url_path=cy_before.url_path),
            ]
        )

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_slug_changed_descendants_only_english_locale(self):
        parent = IndexPageFactory(locale=self.en, slug="parent-old-en")
        child_en = IndexPageFactory(parent=parent, locale=self.en)
        child_cy = IndexPageFactory(parent=parent, locale=self.cy)  # Welsh child should be ignored
        parent.save_revision().publish()

        parent.slug = "parent-new-en"
        parent.save_revision().publish()
        parent.refresh_from_db()
        child_en.refresh_from_db()
        child_cy.refresh_from_db()
        parent_before = parent.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(parent), instance=parent, instance_before=parent_before)

        # Only English parent + English child should be published
        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls(
            [
                call(parent, old_url_path=parent_before.url_path),
                call(
                    child_en,
                    old_url_path=build_old_descendant_path(
                        parent_page=parent,
                        descendant_page=child_en,
                        parent_path_before=parent_before.url_path,
                        parent_path_after=parent.url_path,
                    ),
                ),
            ]
        )

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb"])
    def test_slug_changed_with_welsh_alias_only_english_locale(self):
        # EN source + CY alias. Alias should not trigger when only EN included.
        en_page = InformationPageFactory(locale=self.en, slug="old-en")
        cy_alias = en_page.copy_for_translation(locale=self.cy, copy_parents=True, alias=True)
        en_page.save_revision().publish()

        # Change slug on source; publish revision to create instance_before
        en_page.slug = "new-en"
        en_page.save_revision().publish()
        en_page.refresh_from_db()
        en_before = en_page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(en_page), instance=en_page, instance_before=en_before)
        page_slug_changed.send(sender=type(cy_alias), instance=cy_alias, instance_before=en_before)  # alias mirrors

        # Expect only EN publish; CY alias ignored by allow-list
        self.mock_publisher.publish_created_or_updated.assert_called_once_with(en_page, old_url_path=en_before.url_path)

    @override_settings(SEARCH_INDEX_INCLUDED_LANGUAGES=["en-gb", "cy"])
    def test_slug_changed_with_welsh_alias_both_locales(self):
        en_page = InformationPageFactory(locale=self.en, slug="old-en")
        cy_alias = en_page.copy_for_translation(locale=self.cy, copy_parents=True, alias=True)
        en_page.save_revision().publish()

        en_page.slug = "new-en"
        en_page.save_revision().publish()
        en_page.refresh_from_db()
        en_before = en_page.revisions.order_by("-created_at")[1].as_object()

        self.mock_publisher.publish_created_or_updated.reset_mock()
        page_slug_changed.send(sender=type(en_page), instance=en_page, instance_before=en_before)
        page_slug_changed.send(sender=type(cy_alias), instance=cy_alias, instance_before=en_before)

        self.assertEqual(self.mock_publisher.publish_created_or_updated.call_count, 2)
        self.mock_publisher.publish_created_or_updated.assert_has_calls(
            [
                call(en_page, old_url_path=en_before.url_path),
                call(cy_alias, old_url_path=en_before.url_path),
            ]
        )
