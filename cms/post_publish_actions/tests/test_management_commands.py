import logging
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
from cms.core.tests import TransactionTestCase
from cms.post_publish_actions import registry
from cms.post_publish_actions.executor import flush_executor
from cms.post_publish_actions.management.commands.retry_post_publish_actions import Command as RetryCommand
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionStatus, PostPublishActionType
from cms.post_publish_actions.utils import run_post_publish_actions_for

RETRY_COMMAND_LOGGER = "cms.post_publish_actions.management.commands.retry_post_publish_actions"


class RetryPostPublishActionsTestCase(TransactionTestCase):
    def setUp(self):
        self.bundle = BundleFactory()
        self.page = StatisticalArticlePageFactory()

    def tearDown(self):
        flush_executor()

    def _call_command(self, dry_run=False):
        call_command("retry_post_publish_actions", dry_run=dry_run)

    def _create_stalled_action(self, **kwargs) -> PostPublishAction:
        action = PostPublishAction.objects.create(
            bundle=self.bundle, page=self.page, action_type=PostPublishActionType.SEARCH_UPDATED, **kwargs
        )
        action.enqueued_at = timezone.now() - timedelta(days=1)
        action.save()
        return action

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

    @patch("cms.search.signal_handlers.get_publisher")
    def test_counts_retries(self, mock_get_publisher):
        action = self._create_stalled_action()

        self._call_command()

        action.refresh_from_db()
        mock_get_publisher.assert_called()

        self.assertEqual(action.retry_count, 1)

    @override_settings(BUNDLE_POST_PUBLISH_MAX_RETRIES=2)
    @patch("cms.search.signal_handlers.get_publisher")
    def test_stops_retrying_once_retries_are_exhausted(self, mock_get_publisher):
        action = self._create_stalled_action(retry_count=2, status=PostPublishActionStatus.FAILED)

        with self.assertLogs(RETRY_COMMAND_LOGGER, level=logging.ERROR) as logs:
            self._call_command()

        mock_get_publisher.assert_not_called()

        action.refresh_from_db()
        self.assertEqual(action.status, PostPublishActionStatus.FAILED)
        self.assertEqual(action.retry_count, 2)

        self.assertIn("Post-publish actions have exhausted their retries", logs.output[0])
        self.assertEqual(logs.records[0].exhausted_action_ids, [action.pk])

    @override_settings(BUNDLE_POST_PUBLISH_MAX_RETRIES=2)
    @patch("cms.search.signal_handlers.get_publisher")
    def test_retries_up_to_the_limit(self, mock_get_publisher):
        action = self._create_stalled_action(retry_count=1, status=PostPublishActionStatus.FAILED)

        self._call_command()

        action.refresh_from_db()
        mock_get_publisher.assert_called()

        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertEqual(action.retry_count, 2)

    @override_settings(BUNDLE_POST_PUBLISH_MAX_RETRIES=2)
    def test_republishing_restores_retry_budget(self):
        action = self._create_stalled_action(retry_count=2, status=PostPublishActionStatus.FAILED)

        with patch.dict(registry._registry, {PostPublishActionType.SEARCH_UPDATED: MagicMock()}, clear=True):  # pylint: disable=protected-access
            run_post_publish_actions_for(self.page, self.bundle)

        action.refresh_from_db()
        self.assertEqual(action.retry_count, 0)

        command = RetryCommand()
        self.assertNotIn(action, command._get_exhausted_actions())  # pylint: disable=protected-access

    @patch("cms.search.signal_handlers.get_publisher")
    def test_dry_run_does_not_modify_database(self, mock_get_publisher):
        action = self._create_stalled_action()

        with self.assertLogs(RETRY_COMMAND_LOGGER, level=logging.INFO) as logs:
            self._call_command(dry_run=True)

        mock_get_publisher.assert_not_called()

        self.assertIn(action.id, logs.records[1].action_ids)

        action.refresh_from_db()
        self.assertEqual(action.retry_count, 0)
