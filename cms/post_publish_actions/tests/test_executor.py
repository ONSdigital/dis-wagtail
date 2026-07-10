# pylint: disable=protected-access
import logging
import time
from unittest.mock import MagicMock, patch

from django.test import TestCase

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

    def test_stop_and_wait(self):
        executor.run_in_executor(time.sleep, 1)

        with self.assertLogs("cms.post_publish_actions.executor", level=logging.DEBUG) as logs:
            start_time = time.time()
            executor.executor_stop_and_wait(progress=True)

        self.assertGreater(time.time() - start_time, 0.5)
        self.assertEqual(
            logs.output, ["DEBUG:cms.post_publish_actions.executor:Waiting for 1 threads running post-publish actions"]
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
