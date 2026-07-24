import time
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import time_machine
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Locale, ModelLogEntry, PageLogEntry

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.management.commands.publish_bundles import Command as PublishBundlesCommand
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory, BundlePageFactory
from cms.core.tests import TransactionTestCase
from cms.datasets.tests.factories import DatasetFactory
from cms.home.models import HomePage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.post_publish_actions.executor import executor_stop_and_wait, flush_executor
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionStatus, PostPublishActionType
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.workflows.models import ReadyToPublishGroupTask
from cms.workflows.tests.utils import mark_page_as_ready_to_publish


@override_settings(BUNDLE_POST_PUBLISH_ACTION_SUBMIT_ON_COMMIT=True)
class PublishBundlesCommandTestCase(TransactionTestCase):
    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

        self.publication_date = timezone.now() - timedelta(minutes=1)
        self.statistical_article = StatisticalArticlePageFactory(title="The Statistical Article", live=False)
        self.statistical_article.save_revision(approved_go_live_at=self.publication_date)

        self.methodology_article = MethodologyPageFactory(title="The Methodology Article")
        self.methodology_article.save_revision()

        self.bundle = BundleFactory(approved=True, name="Test Bundle", publication_date=self.publication_date)

    def tearDown(self):
        flush_executor()

    def call_command(self, *args, **kwargs):
        """Helper to call the management command."""
        call_command(
            "publish_bundles",
            *args,
            stdout=self.stdout,
            stderr=self.stderr,
            **kwargs,
        )

    def test_dry_run_with_no_bundles(self):
        """Test dry run output when there are no bundles to publish."""
        self.bundle.publication_date = timezone.now() + timedelta(minutes=10)
        self.bundle.save(update_fields=["publication_date"])

        self.call_command(dry_run=True)

        output = self.stdout.getvalue()
        self.assertIn("Will do a dry run", output)
        self.assertIn("No bundles to go live", output)

    def test_dry_run_with_bundles(self):
        """Test dry run output when there are bundles to publish."""
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        self.call_command(dry_run=True)

        output = self.stdout.getvalue()
        self.assertIn("Will do a dry run", output)
        self.assertIn("Bundles to be published:", output)
        self.assertIn(f"- {self.bundle.name}", output)
        class_name = self.statistical_article.__class__.__name__
        self.assertIn(
            f"{self.statistical_article.get_admin_display_title()} ({class_name})",
            output,
        )

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.notify_slack_of_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_publish_bundle(self, mock_notify_post_publish_end, mock_notify_end, mock_notify_start):
        """Test publishing a bundle."""
        # Sanity checks
        self.assertFalse(self.statistical_article.live)
        self.assertFalse(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())
        self.assertFalse(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())

        unpublished_page = StatisticalArticlePageFactory(live=False)
        unpublished_page.save_revision()

        # Add another page, but publish in the meantime.
        another_page = StatisticalArticlePageFactory(title="The Statistical Article", live=False)
        another_page.save_revision().publish()

        BundlePageFactory(parent=self.bundle, page=self.statistical_article)
        BundlePageFactory(parent=self.bundle, page=another_page)
        BundlePageFactory(parent=self.bundle, page=unpublished_page)

        self.assertEqual(self.bundle.get_bundled_pages().count(), 3)
        self.assertEqual(self.bundle.get_bundled_pages().not_live().count(), 2)

        self.call_command()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.PUBLISHED)

        self.assertEqual(self.bundle.get_bundled_pages().not_live().count(), 0)
        self.statistical_article.refresh_from_db()
        self.assertTrue(self.statistical_article.live)

        # Check notifications were sent
        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)
        self.assertTrue(mock_notify_post_publish_end.called)
        self.assertFalse(mock_notify_post_publish_end.call_args.kwargs["publish_failed"])

        # Check that we have a log entry
        self.assertEqual(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 1)
        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 3)

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.notify_slack_of_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    @patch("cms.search.signal_handlers.get_publisher")
    def test_publish_bundle_waits_for_action(
        self, mock_get_publisher, mock_notify_post_publish_end, mock_notify_end, mock_notify_start
    ):
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        mock_get_publisher.return_value.publish_created_or_updated.side_effect = lambda *args, **kwargs: time.sleep(3)

        mark_page_as_ready_to_publish(self.statistical_article)

        start_time = time.time()
        self.call_command()

        # Make sure the sleep happened
        self.assertGreater(time.time() - start_time, 3)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.PUBLISHED)

        # Check notifications were sent
        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)
        self.assertTrue(mock_notify_post_publish_end.called)

        mock_get_publisher.return_value.publish_created_or_updated.assert_called()

        self.assertEqual(PostPublishAction.objects.unfinished().count(), 0)

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.notify_slack_of_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    @patch("cms.search.signal_handlers.get_publisher")
    def test_publish_bundle_action_error(
        self, mock_get_publisher, mock_notify_post_publish_end, mock_notify_end, mock_notify_start
    ):
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        mock_get_publisher.return_value.publish_created_or_updated.side_effect = ValueError("Something went wrong")

        mark_page_as_ready_to_publish(self.statistical_article)

        self.call_command()

        mock_get_publisher.return_value.publish_created_or_updated.assert_called()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.PUBLISHED)

        # Check notifications were sent
        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)
        self.assertTrue(mock_notify_post_publish_end.called)

        self.assertEqual(PostPublishAction.objects.unfinished().count(), 0)
        self.assertEqual(PostPublishAction.objects.finished().count(), 2)

        failed_action = PostPublishAction.objects.finished().filter(status=PostPublishActionStatus.FAILED).get()

        self.assertEqual(failed_action.failed_reason, "ValueError: Something went wrong")

    @override_settings(
        SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com", BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS=1
    )
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.notify_slack_of_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    @patch("cms.search.signal_handlers.get_publisher")
    def test_publish_bundle_action_timeout_then_finish(
        self, mock_get_publisher, mock_notify_post_publish_end, mock_notify_end, mock_notify_start
    ):
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        mock_get_publisher.return_value.publish_created_or_updated.side_effect = lambda *args, **kwargs: time.sleep(3)

        mark_page_as_ready_to_publish(self.statistical_article)

        start_time = time.time()
        self.call_command()

        # Check the sleep didn't run
        self.assertLessEqual(time.time() - start_time, 3)
        mock_get_publisher.return_value.publish_created_or_updated.assert_called()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.PUBLISHED)

        executor_stop_and_wait()

        # Check notifications were sent
        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)
        self.assertTrue(mock_notify_post_publish_end.called)

        self.assertEqual(PostPublishAction.objects.unfinished().count(), 0)
        self.assertEqual(PostPublishAction.objects.finished().count(), 2)

        action = PostPublishAction.objects.get(action_type=PostPublishActionType.SEARCH_UPDATED)

        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertIsNotNone(action.timed_out_at)

    @override_settings(
        SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com", BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS=1
    )
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.notify_slack_of_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    @patch("cms.search.signal_handlers.get_publisher")
    def test_publish_bundle_action_timeout(
        self, mock_get_publisher, mock_notify_post_publish_end, mock_notify_end, mock_notify_start
    ):
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        mock_get_publisher.return_value.publish_created_or_updated.side_effect = lambda *args, **kwargs: time.sleep(3)

        mark_page_as_ready_to_publish(self.statistical_article)

        start_time = time.time()
        self.call_command()

        # Check the sleep didn't run
        self.assertLessEqual(time.time() - start_time, 3)
        mock_get_publisher.return_value.publish_created_or_updated.assert_called()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.PUBLISHED)

        # Check notifications were sent
        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)
        self.assertTrue(mock_notify_post_publish_end.called)

        self.assertEqual(PostPublishAction.objects.unfinished().count(), 0)
        self.assertEqual(PostPublishAction.objects.finished().count(), 2)

        action = PostPublishAction.objects.get(action_type=PostPublishActionType.SEARCH_UPDATED)

        # Check timed_out_at was set.
        # Other attributes can't be reliably checked, in case the thread stopped before the assertion runs.
        self.assertIsNotNone(action.timed_out_at)

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.notify_slack_of_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_publish_bundle_with_page_in_workflow(
        self, mock_notify_post_publish_end, mock_notify_end, mock_notify_start
    ):
        """Test publishing a bundle."""
        # Sanity checks
        self.assertFalse(self.statistical_article.live)
        self.assertFalse(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())
        self.assertFalse(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())
        self.assertFalse(PageLogEntry.objects.filter(action="wagtail.publish", page=self.statistical_article).exists())

        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        mark_page_as_ready_to_publish(self.statistical_article)

        self.assertIsNotNone(self.statistical_article.current_workflow_state)

        self.call_command()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.PUBLISHED)

        self.statistical_article.refresh_from_db()
        self.assertTrue(self.statistical_article.live)
        self.assertIsNone(self.statistical_article.current_workflow_state)

        workflow_state = self.statistical_article.workflow_states[0]
        self.assertEqual(workflow_state.status, "approved")
        self.assertEqual(workflow_state.current_task_state.status, "approved")
        self.assertIsInstance(workflow_state.current_task_state.task.specific, ReadyToPublishGroupTask)

        # Check notifications were sent
        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)
        self.assertTrue(mock_notify_post_publish_end.called)

        # Check that we have a log entry
        self.assertEqual(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 1)
        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 0)
        self.assertTrue(PageLogEntry.objects.filter(action="wagtail.publish", page=self.statistical_article).exists())

    def test_publish_bundle_with_only_datasets(self):
        """Test publishing a bundle that only contains datasets and no pages publishes succesfully."""
        DatasetFactory()
        BundleDatasetFactory(parent=self.bundle)
        self.call_command()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.PUBLISHED)

    def test_publish_bundle_with_release_calendar(self):
        """Test publishing a bundle with an associated release calendar page."""
        release_page = ReleaseCalendarPageFactory(release_date=self.publication_date)
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)
        BundlePageFactory(parent=self.bundle, page=self.methodology_article)
        # Create a dummy dataset so that the following BundleDataset instances don't have
        # the same IDs as the datasets created by the BundleDatasetFactory.
        DatasetFactory()
        bundle_dataset_a = BundleDatasetFactory(parent=self.bundle)
        bundle_dataset_b = BundleDatasetFactory(parent=self.bundle)
        bundle_dataset_c = BundleDatasetFactory(parent=self.bundle)
        self.assertEqual(len(release_page.datasets), 0)

        self.bundle.publication_date = None
        self.bundle.release_calendar_page = release_page
        self.bundle.save(update_fields=["publication_date", "release_calendar_page"])

        self.call_command()

        # Check release calendar was updated
        release_page.refresh_from_db()
        self.assertEqual(release_page.status, ReleaseStatus.PUBLISHED)

        content = release_page.content[0].value
        self.assertEqual(content["title"], "Publications")
        self.assertEqual(len(content["links"]), 1)
        self.assertEqual(content["links"][0]["page"].pk, self.statistical_article.pk)

        content = release_page.content[1].value
        self.assertEqual(content["title"], "Quality and methodology")
        self.assertEqual(len(content["links"]), 1)
        self.assertEqual(content["links"][0]["page"].pk, self.methodology_article.pk)

        self.assertEqual(len(release_page.datasets), 3)
        self.assertEqual(release_page.datasets[0].block_type, "dataset_lookup")
        self.assertEqual(release_page.datasets[1].block_type, "dataset_lookup")
        self.assertEqual(release_page.datasets[2].block_type, "dataset_lookup")
        self.assertEqual(release_page.datasets[0].value, bundle_dataset_a.dataset)
        self.assertEqual(release_page.datasets[1].value, bundle_dataset_b.dataset)
        self.assertEqual(release_page.datasets[2].value, bundle_dataset_c.dataset)

    def test_publish_bundle_with_revisions_to_live_page(self):
        """Test publishing a bundle containing a live page with unpublished revisions updates page."""
        # Ensure the page is live
        self.statistical_article.publish(self.statistical_article.get_latest_revision())
        self.statistical_article.refresh_from_db()
        self.assertTrue(self.statistical_article.live)

        # Create a new revision (it will be in draft)
        self.statistical_article.title = "Updated Title"
        new_revision = self.statistical_article.save_revision()

        # Assertions before call_command
        self.statistical_article.refresh_from_db()
        self.assertNotEqual(self.statistical_article.live_revision, new_revision)
        self.assertEqual(self.statistical_article.get_latest_revision(), new_revision)
        self.assertNotEqual(self.statistical_article.title, "Updated Title")

        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        self.call_command()

        # Assertions after call_command
        self.statistical_article.refresh_from_db()
        self.assertEqual(self.statistical_article.live_revision, new_revision)
        self.assertTrue(self.statistical_article.live)
        self.assertEqual(self.statistical_article.title, "Updated Title")

    @patch("cms.bundles.utils.logger")
    def test_publish_bundle_with_no_successful_page_publishes(self, mock_utils_logger):
        """Test that the bundle status is updated to FAILED if no pages were successfully published."""
        # Create a page that will fail to publish (no revisions)
        page_with_no_revisions = StatisticalArticlePageFactory(live=False)
        page_with_no_revisions.revisions.all().delete()

        BundlePageFactory(parent=self.bundle, page=page_with_no_revisions)

        self.call_command()

        # Check bundle status was updated to FAILED
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.FAILED)

        # Check error was logged in utils
        mock_utils_logger.error.assert_any_call(
            "No pages were successfully published",
            extra={
                "bundle_id": self.bundle.pk,
                "event": "publish_failed_no_success",
            },
        )

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.alert_slack_of_bundle_content_failure")
    @patch("cms.bundles.utils.notify_slack_of_bundle_failure")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_failed_bundle_gets_post_publish_end_notification_flagged_as_failed(
        self,
        mock_notify_post_publish_end,
        _mock_notify_failure,
        _mock_alert_content_failure,
        _mock_notify_start,
    ):
        """Test a bnundle that failed to publish doesn't get a green 'publishing has ended' message."""
        page_with_no_revisions = StatisticalArticlePageFactory(live=False)

        # easiest way to force a failure in test
        page_with_no_revisions.revisions.all().delete()

        BundlePageFactory(parent=self.bundle, page=page_with_no_revisions)

        self.call_command()

        # join executor before assert
        executor_stop_and_wait()

        mock_notify_post_publish_end.assert_called_once()
        self.assertTrue(mock_notify_post_publish_end.call_args.kwargs["publish_failed"])

    @patch("cms.bundles.management.commands.publish_bundles.publish_bundle")
    @patch("cms.bundles.management.commands.publish_bundles.logger")
    def test_bundle_no_longer_approved_is_not_published(self, mock_logger, mock_publish_bundle):
        """Test a bundle that was initially approved but moved out of that status isn't published."""
        self.bundle.status = BundleStatus.DRAFT
        self.bundle.save(update_fields=["status"])

        command = PublishBundlesCommand()
        command.bundle_start_times = {}
        command._handle_bundle_action(self.bundle)  # pylint: disable=protected-access

        mock_publish_bundle.assert_not_called()
        mock_logger.error.assert_called_once_with("Bundle no longer approved", extra={"bundle_id": self.bundle.pk})

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_bundle_no_longer_approved_does_not_send_success_notification(self, mock_notify_post_publish_end):
        """Test a bundle that was initially approved but moved out of that status isn't published."""
        self.bundle.status = BundleStatus.DRAFT
        self.bundle.save(update_fields=["status"])

        command = PublishBundlesCommand()
        command.bundle_complete_futures = []
        command._handle_bundle_action(self.bundle)  # pylint: disable=protected-access

        self.assertEqual(command.bundle_complete_futures, [])
        mock_notify_post_publish_end.assert_not_called()

    def test_publish_bundle_with_zero_pages(self):
        """Test that a bundle with zero pages is not marked as published."""
        self.assertEqual(self.bundle.bundled_pages.count(), 0)

        self.call_command()

        # Check bundle status wasn't changed
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.APPROVED)

    def test_publish_bundle_with_welsh_release_calendar(self):
        """Test publishing a bundle with a Welsh release calendar page uses Welsh translations."""
        welsh_locale, _ = Locale.objects.get_or_create(language_code="cy")
        release_page = ReleaseCalendarPageFactory(release_date=self.publication_date, locale=welsh_locale)

        BundlePageFactory(parent=self.bundle, page=self.statistical_article)
        BundlePageFactory(parent=self.bundle, page=self.methodology_article)

        self.bundle.publication_date = None
        self.bundle.release_calendar_page = release_page
        self.bundle.save(update_fields=["publication_date", "release_calendar_page"])

        self.call_command()

        # Check release calendar was updated with Welsh translations
        release_page.refresh_from_db()
        self.assertEqual(release_page.status, ReleaseStatus.PUBLISHED)

        content = release_page.content[0].value
        self.assertEqual(content["title"], "Cyhoeddiadau")
        self.assertEqual(len(content["links"]), 1)
        self.assertEqual(content["links"][0]["page"].pk, self.statistical_article.pk)

        content = release_page.content[1].value
        self.assertEqual(content["title"], "Ansawdd a methodoleg")
        self.assertEqual(len(content["links"]), 1)
        self.assertEqual(content["links"][0]["page"].pk, self.methodology_article.pk)

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.management.commands.publish_bundles.logger")
    def test_publish_bundle_error_handling(self, mock_logger):
        """Test error handling during bundle publication."""
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        # Mock an error during publication
        with patch(
            "cms.bundles.utils.notify_slack_of_publication_start",
            side_effect=Exception("Test error"),
        ):
            self.call_command()

        # Check error was logged
        mock_logger.exception.assert_called_with(
            "Publish failed", extra={"bundle_id": self.bundle.id, "event": "publish_failed"}
        )

        # Check bundle status wasn't changed due to error
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.APPROVED)

    @override_settings(WAGTAILADMIN_BASE_URL="https://test.ons.gov.uk")
    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.utils.notify_slack_of_publication_start")
    @patch("cms.bundles.utils.notify_slack_of_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_publish_bundle_with_base_url(self, mock_notify_post_publish_end, mock_notify_end, mock_notify_start):
        """Test publishing with a configured base URL."""
        self.call_command()

        # Verify notifications were called with correct URL
        for notif in [mock_notify_start, mock_notify_end]:
            notif.assert_called_once()
            call_kwargs = notif.call_args[1]

            self.assertEqual(
                call_kwargs["url"], "https://test.ons.gov.uk" + reverse("bundle:inspect", args=(self.bundle.pk,))
            )
            self.assertIn(str(self.bundle.pk), call_kwargs["url"])

        self.assertTrue(mock_notify_post_publish_end.called)

    @patch("cms.bundles.management.commands.publish_bundles.publish_bundle")
    def test_publish_bundle_include_future(self, mock_publish_bundle):
        with time_machine.travel(self.publication_date - timedelta(seconds=2)):
            self.call_command(include_future=1)

            # 2 seconds before publish, there's nothing to do within 1 second, so nothing happens
            mock_publish_bundle.assert_not_called()
            self.assertLess(timezone.now(), self.publication_date)
            self.assertIn("No bundles to go live.", self.stdout.getvalue())
            self.stdout.seek(0)

            self.call_command(include_future=2)

            self.assertGreater(timezone.now(), self.publication_date)

        # 2 seconds before publish, wait, then publish
        mock_publish_bundle.assert_called_once_with(self.bundle)
        self.assertIn("Found 1 bundle(s) to publish", self.stdout.getvalue())
        self.assertIn(f"Publishing {self.bundle.name} in", self.stdout.getvalue())

    @patch("cms.bundles.management.commands.publish_bundles.publish_bundle")
    def test_publish_bundle_include_future_with_bundle_in_past(self, mock_publish_bundle):
        with time_machine.travel(self.publication_date + timedelta(days=1)):
            self.call_command(include_future=1)

        mock_publish_bundle.assert_called_once_with(self.bundle)

    def test_publish_with_no_bundles(self):
        self.bundle.publication_date = timezone.now() + timedelta(minutes=10)
        self.bundle.save(update_fields=["publication_date"])

        self.call_command()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.APPROVED)

        self.assertIn("No bundles to go live.", self.stdout.getvalue())

    @patch("cms.bundles.management.commands.publish_bundles.publish_bundle")
    def test_publish_with_future_bundles(self, mock_publish_bundle):
        with time_machine.travel(self.publication_date - timedelta(days=1)):
            self.call_command()

        mock_publish_bundle.assert_not_called()
        self.assertIn("No bundles to go live.", self.stdout.getvalue())


class PublishScheduledWithoutBundlesCommandTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.first()
        cls.statistical_article = StatisticalArticlePageFactory(title="The Statistical Article", live=False)
        cls.bundle = BundleFactory(name="Test Bundle", bundled_pages=[cls.statistical_article])

        cls.publication_date = timezone.now().replace(second=0) - timedelta(minutes=1)
        cls.statistical_article.save_revision(approved_go_live_at=cls.publication_date)

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

    def call_command(self, *args, **kwargs):
        """Helper to call the management command."""
        call_command(
            "publish_scheduled_without_bundles",
            *args,
            stdout=self.stdout,
            stderr=self.stderr,
            **kwargs,
        )

    def test_dry_run(self):
        """Test dry run doesn't include our bundled page."""
        self.call_command(dry_run=True)

        output = self.stdout.getvalue()
        self.assertIn("Will do a dry run.", output)
        self.assertIn("No objects to go live.", output)
        self.assertIn("No expired objects to be deactivated found.", output)

    def test_dry_run__with_a_scheduled_page(self):
        """Test dry run doesn't include our bundled page."""
        self.home.save_revision(approved_go_live_at=self.publication_date)

        self.call_command(dry_run=True)

        output = self.stdout.getvalue()
        self.assertIn("Will do a dry run.", output)

        self.assertIn("Revisions to be published:", output)
        self.assertIn(self.home.title, output)

        self.assertFalse(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())

    def test_publish_scheduled_without_bundles__happy_path(self):
        """Checks only a scheduled non-bundled page has been published."""
        self.home.save_revision(approved_go_live_at=self.publication_date)

        self.call_command()

        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 1)

    def test_include_future(self):
        """Checks only a scheduled non-bundled page has been published."""
        self.home.save_revision(approved_go_live_at=self.publication_date)

        with time_machine.travel(self.publication_date - timedelta(seconds=2)):
            self.call_command(include_future=1)

            # 2 seconds before publish, there's nothing to do within 1 second, so nothing happens
            self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 0)
            self.assertLess(timezone.now(), self.publication_date)
            self.assertIn("No objects to go live.", self.stdout.getvalue())

            self.stdout.seek(0)

            self.call_command(include_future=2)

            # 2 seconds before publish, wait, then publish
            self.assertGreater(timezone.now(), self.publication_date)
            self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 1)
            self.assertIn(str(self.home), self.stdout.getvalue())

    def test_publish_include_future_with_page_in_past(self):
        self.home.save_revision(approved_go_live_at=self.publication_date)

        with time_machine.travel(self.publication_date + timedelta(days=1)):
            self.call_command(include_future=1)

        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 1)

    def test_publish_with_future_pages(self):
        self.home.save_revision(approved_go_live_at=self.publication_date)

        with time_machine.travel(self.publication_date - timedelta(days=1)):
            self.call_command(include_future=1)

        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 0)
