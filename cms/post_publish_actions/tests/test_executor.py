# pylint: disable=protected-access
import logging
import time
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.test.utils import override_settings

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
from cms.core.tests import TransactionTestCase
from cms.post_publish_actions import executor
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionStatus, PostPublishActionType


class ExecutorTestCase(TestCase):
    def setUp(self):
        """Ensure any other tests that run haven't left threads behind.

        Add a cleanup to ensure executor is flushed even if tests fail.
        """
        executor.flush_executor()
        self.addCleanup(executor.flush_executor)

    def test_flush(self):
        original_executor = executor._executor
        original_support_executor = executor._support_executor

        executor.flush_executor()

        self.assertIsNot(executor._executor, original_executor)
        self.assertIsNot(executor._support_executor, original_support_executor)

        self.assertTrue(original_executor._shutdown)
        self.assertTrue(original_support_executor._shutdown)

    def test_reset_after_fork(self):
        original_executor = executor._executor
        original_support_executor = executor._support_executor

        executor._reset_executors_after_fork()

        self.assertIsNot(executor._executor, original_executor)
        self.assertIsNot(executor._support_executor, original_support_executor)

        # Original executors will still exist in original thread
        self.assertFalse(original_executor._shutdown)
        self.assertFalse(original_support_executor._shutdown)

    @override_settings(BUNDLE_POST_PUBLISH_CONCURRENCY=7, BUNDLE_POST_PUBLISH_SUPPORT_CONCURRENCY=2)
    def test_executor_sizes_are_independently_configurable(self):
        self.assertEqual(executor._build_executor()._max_workers, 7)
        self.assertEqual(executor._build_support_executor()._max_workers, 2)

    def test_stop_and_wait(self):
        executor.run_in_executor(time.sleep, 1)

        with self.assertLogs("cms.post_publish_actions.executor", level=logging.DEBUG) as logs:
            start_time = time.time()
            executor.executor_stop_and_wait(progress=True)

        self.assertGreater(time.time() - start_time, 0.5)
        self.assertEqual(
            logs.output, ["INFO:cms.post_publish_actions.executor:Waiting for 1 threads running post-publish actions"]
        )

        self.assertTrue(executor._executor._shutdown)
        self.assertTrue(executor._support_executor._shutdown)

    def test_stop_and_wait_no_progress(self):
        executor.run_in_executor(time.sleep, 1)

        with self.assertNoLogs("cms.post_publish_actions.executor", level=logging.DEBUG):
            start_time = time.time()
            executor.executor_stop_and_wait(progress=False)

        self.assertGreater(time.time() - start_time, 0.5)

        self.assertTrue(executor._executor._shutdown)
        self.assertTrue(executor._support_executor._shutdown)

    def test_stop_and_wait_no_tasks(self):
        with self.assertNoLogs("cms.post_publish_actions.executor", level=logging.DEBUG):
            start_time = time.time()
            executor.executor_stop_and_wait(progress=False)

        self.assertLess(time.time() - start_time, 0.1)

        self.assertTrue(executor._executor._shutdown)
        self.assertTrue(executor._support_executor._shutdown)

    @patch("cms.post_publish_actions.executor.close_old_connections")
    def test_closes_old_connections(self, mock_close_old_connections):
        executor.run_in_executor(lambda: None)
        self.assertEqual(mock_close_old_connections.call_count, 2)

    def test_bundle_notifications_run_in_submission_order(self):
        order = []

        def slow_start_notification():
            time.sleep(0.2)
            order.append("start")

        executor.run_bundle_notification_in_support_executor(1, slow_start_notification)
        executor.run_bundle_notification_in_support_executor(1, lambda: order.append("end"))
        executor.wait_for_bundle_notifications(1)
        order.append("post")

        self.assertEqual(order, ["start", "end", "post"])
        self.assertNotIn(1, executor._bundle_notification_futures)

    def test_bundle_notifications_for_different_bundles_are_not_chained(self):
        order = []

        executor.run_bundle_notification_in_support_executor(1, lambda: (time.sleep(0.5), order.append("first")))
        executor.run_bundle_notification_in_support_executor(2, lambda: order.append("second"))
        executor.wait_for_bundle_notifications(2)

        self.assertEqual(order, ["second"])
        executor.wait_for_bundle_notifications(1)

    def test_wait_for_bundle_notifications_without_registration(self):
        executor.wait_for_bundle_notifications(12345)

    def test_swallows_exceptions(self):
        """Test exceptions don't escape worker boundary and are logged."""

        def raises():
            raise ValueError("Failed")

        with self.assertLogs("cms.post_publish_actions.executor", level=logging.ERROR) as logs:
            executor.run_in_executor(raises).result(timeout=10)

        self.assertIn("Unhandled exception in post-publish actions", logs.output[0])
        self.assertIn("ValueError: Failed", logs.output[0])

        # executor still works
        executor.run_in_executor(lambda: None).result(timeout=10)

    @override_settings(BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS=executor.SHUTDOWN_MESSAGE_BUFFER_SECONDS)
    def test_stop_and_wait_reports_actions_running_at_timeout(self):
        executor.run_in_executor(time.sleep, 1)

        with self.assertLogs("cms.post_publish_actions.executor", level=logging.ERROR) as logs:
            executor.executor_stop_and_wait()

        self.assertEqual(len(logs.output), 1)
        self.assertIn("Post-publish actions still running at shutdown", logs.output[0])

        # should keep waiting for the difference between BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS
        # and SHUTDOWN_MESSAGE_BUFFER_SECONDS
        self.assertFalse(any(t.is_alive() for t in executor._executor._threads))


class RunActionTestCase(TransactionTestCase):
    def setUp(self):
        self.handler = MagicMock()

    def test_uses_write_db(self):
        bundle = BundleFactory()
        page = StatisticalArticlePageFactory()

        PostPublishAction.objects.create(page=page, bundle=bundle, action_type=PostPublishActionType.S3_ACL)

        with self.assertNumQueriesConnection(default=6):
            executor.run_action(self.handler, PostPublishActionType.S3_ACL, page.id, bundle.id)

    def test_requires_bundle_id(self):
        with self.assertRaisesMessage(RuntimeError, "Bundle id required"):
            executor.run_action(self.handler, PostPublishActionType.S3_ACL, 123, None)

    def test_runs_handler(self):
        bundle = BundleFactory()
        page = StatisticalArticlePageFactory()

        action = PostPublishAction.objects.create(page=page, bundle=bundle, action_type=PostPublishActionType.S3_ACL)

        executor.run_action(self.handler, PostPublishActionType.S3_ACL, page.id, bundle.id)

        action.refresh_from_db()

        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertIsNotNone(action.finished_at)
        self.assertEqual(action.failed_reason, "")
        self.assertGreater(action.duration.total_seconds(), 0)

        self.handler.assert_called()

    def test_failed_handler(self):
        self.handler.side_effect = ValueError("Failed")

        bundle = BundleFactory()
        page = StatisticalArticlePageFactory()

        action = PostPublishAction.objects.create(page=page, bundle=bundle, action_type=PostPublishActionType.S3_ACL)

        executor.run_action(self.handler, PostPublishActionType.S3_ACL, page.id, bundle.id)

        action.refresh_from_db()

        self.assertEqual(action.status, PostPublishActionStatus.FAILED)
        self.assertIsNotNone(action.finished_at)
        self.assertEqual(action.failed_reason, "ValueError: Failed")
        self.assertGreater(action.duration.total_seconds(), 0)
