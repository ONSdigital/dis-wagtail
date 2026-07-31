import time
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
from cms.core.tests import TransactionTestCase
from cms.post_publish_actions.executor import flush_executor
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionStatus, PostPublishActionType


class RetryPostPublishActionsTestCase(TransactionTestCase):
    def setUp(self):
        self.bundle = BundleFactory()
        self.page = StatisticalArticlePageFactory()

    def tearDown(self):
        flush_executor()

    def _call_command(self):
        call_command("retry_post_publish_actions")

    def test_noop(self):
        self._call_command()

    @patch("cms.search.signal_handlers.get_publisher")
    def test_runs_timed_out(self, mock_get_publisher):
        action = PostPublishAction.objects.create(
            bundle=self.bundle,
            page=self.page,
            action_type=PostPublishActionType.SEARCH_UPDATED,
        )
        action.enqueued_at = timezone.now() - timedelta(days=1)
        action.save()

        PostPublishAction.objects.all().mark_timed_out()
        action.refresh_from_db()

        self.assertEqual(action.status, PostPublishActionStatus.FAILED)

        self._call_command()

        action.refresh_from_db()
        mock_get_publisher.assert_called()

        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertIsNone(action.timed_out_at)
        self.assertEqual(action.failed_reason, "")

    @patch("cms.search.signal_handlers.get_publisher")
    def test_runs_stuck_running(self, mock_get_publisher):
        action = PostPublishAction.objects.create(
            bundle=self.bundle,
            page=self.page,
            action_type=PostPublishActionType.SEARCH_UPDATED,
            status=PostPublishActionStatus.RUNNING,
        )
        action.enqueued_at = timezone.now() - timedelta(days=1)
        action.save()

        self._call_command()

        action.refresh_from_db()
        mock_get_publisher.assert_called()

        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertIsNotNone(action.finished_at)

    @patch("cms.search.signal_handlers.get_publisher")
    def test_runs_ready(self, mock_get_publisher):
        action = PostPublishAction.objects.create(
            bundle=self.bundle,
            page=self.page,
            action_type=PostPublishActionType.SEARCH_UPDATED,
            status=PostPublishActionStatus.READY,
        )
        action.enqueued_at = timezone.now() - timedelta(days=1)
        action.save()

        self._call_command()

        action.refresh_from_db()
        mock_get_publisher.assert_called()

        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertIsNotNone(action.finished_at)

    @override_settings(BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS=1)
    @patch("cms.search.signal_handlers.get_publisher")
    def test_action_time_out(self, mock_get_publisher):
        mock_get_publisher.side_effect = lambda *args, **kwargs: time.sleep(3)

        action = PostPublishAction.objects.create(
            bundle=self.bundle,
            page=self.page,
            action_type=PostPublishActionType.SEARCH_UPDATED,
        )
        action.enqueued_at = timezone.now() - timedelta(days=1)
        action.save()

        PostPublishAction.objects.all().mark_timed_out()
        action.refresh_from_db()

        self.assertEqual(action.status, PostPublishActionStatus.FAILED)
        original_timeout = action.timed_out_at

        self._call_command()

        action.refresh_from_db()

        self.assertEqual(action.status, PostPublishActionStatus.FAILED)
        self.assertGreater(action.timed_out_at, original_timeout)
        self.assertEqual(action.failed_reason, "Timeout")
