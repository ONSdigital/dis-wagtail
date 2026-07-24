# pylint: disable=protected-access
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
from cms.bundles.utils import get_active_bundle_for_page
from cms.home.models import HomePage
from cms.post_publish_actions import registry
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionStatus, PostPublishActionType
from cms.post_publish_actions.utils import post_publish_notify_slack, run_post_publish_actions_for


class RunPostPublishActionsForTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = StatisticalArticlePageFactory()
        cls.handler = MagicMock()

    def test_without_bundle_runs_handlers_synchronously(self):
        """Test that pages published without a bundle publish synchronously for now."""
        with patch.dict(registry._registry, {PostPublishActionType.S3_ACL: self.handler}, clear=True):
            run_post_publish_actions_for(self.page, None)

        self.handler.assert_called_with(self.page, None)
        self.assertEqual(PostPublishAction.objects.count(), 0)


class GetActiveBundleForPageTestCase(TestCase):
    def test_returns_none_for_a_page_that_cannot_be_bundled(self):
        home_page = HomePage.objects.first()

        self.assertIsNone(get_active_bundle_for_page(home_page))


class PostPublishNotifySlackTestCase(TestCase):
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_forwards_publish_failed_to_the_notification(self, mock_notify):
        """The publish outcome has to reach final notification so failures stay red."""
        bundle = BundleFactory()

        post_publish_notify_slack(timezone.now(), bundle, publish_failed=True)

        mock_notify.assert_called_once()
        self.assertTrue(mock_notify.call_args.kwargs["publish_failed"])

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_defaults_to_publish_failed_false(self, mock_notify):
        """A successful publish must not be reported as failed."""
        bundle = BundleFactory()

        post_publish_notify_slack(timezone.now(), bundle)

        mock_notify.assert_called_once()
        self.assertFalse(mock_notify.call_args.kwargs["publish_failed"])

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_end_time_derived_from_action_finished_at(self, mock_notify):
        """The end time of the notification should be the latest finished_at of the actions."""
        bundle = BundleFactory()
        page = HomePage.objects.first()
        start_time = timezone.now() - timedelta(minutes=5)
        last_finish = start_time + timedelta(minutes=2)

        PostPublishAction.objects.create(
            bundle=bundle,
            page=page,
            action_type=PostPublishActionType.S3_ACL,
            status=PostPublishActionStatus.SUCCESSFUL,
            finished_at=start_time + timedelta(minutes=1),
        )
        action = PostPublishAction.objects.create(
            bundle=bundle,
            page=page,
            action_type=PostPublishActionType.SEARCH_UPDATED,
            status=PostPublishActionStatus.SUCCESSFUL,
            finished_at=last_finish,
        )

        post_publish_notify_slack(start_time, bundle)

        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[2], last_finish)

        action.refresh_from_db()
        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertIsNone(action.timed_out_at)

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_end_time_ignores_actions_from_a_previous_publish(self, mock_notify):
        bundle = BundleFactory()
        page = HomePage.objects.first()
        start_time = timezone.now()

        PostPublishAction.objects.create(
            bundle=bundle,
            page=page,
            action_type=PostPublishActionType.SEARCH_UPDATED,
            status=PostPublishActionStatus.SUCCESSFUL,
            finished_at=start_time - timedelta(hours=1),
        )

        post_publish_notify_slack(start_time, bundle)

        mock_notify.assert_called_once()
        self.assertGreaterEqual(mock_notify.call_args.args[2], start_time)

    @override_settings(BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS=0)
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_timed_out_actions_still_produce_an_end_time(self, mock_notify):
        bundle = BundleFactory()
        page = HomePage.objects.first()
        start_time = timezone.now()

        action = PostPublishAction.objects.create(
            bundle=bundle, page=page, action_type=PostPublishActionType.S3_ACL, status=PostPublishActionStatus.RUNNING
        )

        post_publish_notify_slack(start_time, bundle)

        action.refresh_from_db()
        self.assertEqual(action.status, PostPublishActionStatus.FAILED)
        self.assertIsNotNone(action.timed_out_at)

        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[2], action.finished_at)
