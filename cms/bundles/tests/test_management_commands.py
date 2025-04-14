from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.models import ModelLogEntry, PageLogEntry

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.home.models import HomePage
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.workflows.models import ReadyToPublishGroupTask
from cms.workflows.tests.utils import mark_page_as_ready_to_publish


class PublishBundlesCommandTestCase(TestCase):
    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

        self.publication_date = timezone.now() - timedelta(minutes=1)
        self.statistical_article = StatisticalArticlePageFactory(title="The Statistical Article", live=False)
        self.statistical_article.save_revision(approved_go_live_at=self.publication_date)

        self.bundle = BundleFactory(approved=True, name="Test Bundle", publication_date=self.publication_date)

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
    @patch("cms.bundles.management.commands.publish_bundles.notify_slack_of_publication_start")
    @patch("cms.bundles.management.commands.publish_bundles.notify_slack_of_publish_end")
    def test_publish_bundle(self, mock_notify_end, mock_notify_start):
        """Test publishing a bundle."""
        # Sanity checks
        self.assertFalse(self.statistical_article.live)
        self.assertFalse(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())
        self.assertFalse(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())

        # Add another page, but publish in the meantime.
        another_page = StatisticalArticlePageFactory(title="The Statistical Article", live=False)
        another_page.save_revision().publish()
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)
        BundlePageFactory(parent=self.bundle, page=another_page)

        self.call_command()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.RELEASED)

        self.statistical_article.refresh_from_db()
        self.assertTrue(self.statistical_article.live)

        # Check notifications were sent
        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)

        # Check that we have a log entry
        self.assertEqual(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 1)
        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 2)

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
    @patch("cms.bundles.management.commands.publish_bundles.notify_slack_of_publication_start")
    @patch("cms.bundles.management.commands.publish_bundles.notify_slack_of_publish_end")
    def test_publish_bundle_with_page_in_workflow(self, mock_notify_end, mock_notify_start):
        """Test publishing a bundle."""
        # Sanity checks
        self.assertFalse(self.statistical_article.live)
        self.assertFalse(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())
        self.assertFalse(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").exists())

        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        mark_page_as_ready_to_publish(self.statistical_article)

        self.assertIsNotNone(self.statistical_article.current_workflow_state)

        self.call_command()

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.RELEASED)

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

        # Check that we have a log entry
        self.assertEqual(ModelLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 1)
        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish.scheduled").count(), 0)
        self.assertEqual(PageLogEntry.objects.filter(action="wagtail.publish").count(), 1)

    def test_publish_bundle_with_release_calendar(self):
        """Test publishing a bundle with an associated release calendar page."""
        release_page = ReleaseCalendarPageFactory(release_date=self.publication_date)
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)
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

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.management.commands.publish_bundles.logger")
    def test_publish_bundle_error_handling(self, mock_logger):
        """Test error handling during bundle publication."""
        BundlePageFactory(parent=self.bundle, page=self.statistical_article)

        # Mock an error during publication
        with patch(
            "cms.bundles.management.commands.publish_bundles.notify_slack_of_publication_start",
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
    @patch("cms.bundles.management.commands.publish_bundles.notify_slack_of_publication_start")
    def test_publish_bundle_with_base_url(self, mock_notify):
        """Test publishing with a configured base URL."""
        self.call_command()

        # Verify notification was called with correct URL
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]

        self.assertEqual(
            call_kwargs["url"], "https://test.ons.gov.uk" + reverse("bundle:inspect", args=(self.bundle.pk,))
        )
        self.assertIn(str(self.bundle.pk), call_kwargs["url"])


class PublishScheduledWithoutBundlesCommandTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.first()
        cls.statistical_article = StatisticalArticlePageFactory(title="The Statistical Article", live=False)
        cls.bundle = BundleFactory(name="Test Bundle", bundled_pages=[cls.statistical_article])

        cls.publication_date = timezone.now() - timedelta(minutes=1)
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
