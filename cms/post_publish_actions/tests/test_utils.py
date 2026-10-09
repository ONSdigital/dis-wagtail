# pylint: disable=protected-access
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
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
        with patch.dict(
            registry._registry,
            {PostPublishActionType.S3_ACL: registry.RegisteredPostPublishAction(handler=self.handler)},
            clear=True,
        ):
            run_post_publish_actions_for(self.page, None)

        self.handler.assert_called_with(self.page, None)
        self.assertEqual(PostPublishAction.objects.count(), 0)


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
    def test_end_time_derived_from_critical_action_finished_at(self, mock_notify):
        """The end time of the notification should be the latest finished_at of the actions."""
        bundle = BundleFactory()
        pages = StatisticalArticlePageFactory.create_batch(2)
        start_time = timezone.now() - timedelta(minutes=5)
        last_critical_finish = start_time + timedelta(minutes=2)

        PostPublishAction.objects.create(
            bundle=bundle,
            page=pages[0],
            action_type=PostPublishActionType.CACHE_PURGE,
            status=PostPublishActionStatus.SUCCESSFUL,
            finished_at=start_time + timedelta(minutes=1),
        )
        action = PostPublishAction.objects.create(
            bundle=bundle,
            page=pages[1],
            action_type=PostPublishActionType.CACHE_PURGE,
            status=PostPublishActionStatus.SUCCESSFUL,
            finished_at=last_critical_finish,
        )

        post_publish_notify_slack(start_time, bundle)

        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[2], last_critical_finish)

        action.refresh_from_db()
        self.assertEqual(action.status, PostPublishActionStatus.SUCCESSFUL)
        self.assertIsNone(action.timed_out_at)

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_end_time_ignores_non_critical_actions(self, mock_notify):
        bundle = BundleFactory()
        page = HomePage.objects.first()
        start_time = timezone.now() - timedelta(minutes=5)
        critical_finish = start_time + timedelta(minutes=1)

        PostPublishAction.objects.create(
            bundle=bundle,
            page=page,
            action_type=PostPublishActionType.CACHE_PURGE,
            status=PostPublishActionStatus.SUCCESSFUL,
            finished_at=critical_finish,
        )
        for action_type in [PostPublishActionType.SEARCH_UPDATED, PostPublishActionType.S3_ACL]:
            PostPublishAction.objects.create(
                bundle=bundle,
                page=page,
                action_type=action_type,
                status=PostPublishActionStatus.SUCCESSFUL,
                finished_at=start_time + timedelta(minutes=3),
            )

        post_publish_notify_slack(start_time, bundle)

        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[2], critical_finish)

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_end_time_falls_back_to_the_last_action_to_finish_without_critical_actions(self, mock_notify):
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
        PostPublishAction.objects.create(
            bundle=bundle,
            page=page,
            action_type=PostPublishActionType.SEARCH_UPDATED,
            status=PostPublishActionStatus.SUCCESSFUL,
            finished_at=last_finish,
        )

        post_publish_notify_slack(start_time, bundle)

        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[2], last_finish)

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_end_time_falls_back_to_now_without_any_actions(self, mock_notify):
        bundle = BundleFactory()
        start_time = timezone.now() - timedelta(minutes=5)

        before = timezone.now()
        post_publish_notify_slack(start_time, bundle)

        mock_notify.assert_called_once()
        self.assertGreaterEqual(mock_notify.call_args.args[2], before)

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    def test_end_time_ignores_actions_from_a_previous_publish(self, mock_notify):
        bundle = BundleFactory()
        page = HomePage.objects.first()
        start_time = timezone.now()

        PostPublishAction.objects.create(
            bundle=bundle,
            page=page,
            action_type=PostPublishActionType.CACHE_PURGE,
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
            bundle=bundle,
            page=page,
            action_type=PostPublishActionType.CACHE_PURGE,
            status=PostPublishActionStatus.RUNNING,
        )

        post_publish_notify_slack(start_time, bundle)

        action.refresh_from_db()
        self.assertEqual(action.status, PostPublishActionStatus.FAILED)
        self.assertIsNotNone(action.timed_out_at)

        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[2], action.finished_at)


class PostPublishNotifySlackFailureRepliesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory()
        cls.pages = StatisticalArticlePageFactory.create_batch(2)

    def _create_action(self, action_type, status, page=None, **kwargs):
        return PostPublishAction.objects.create(
            bundle=self.bundle,
            page=page or self.pages[0],
            action_type=action_type,
            status=status,
            **kwargs,
        )

    @override_settings(BUNDLE_POST_PUBLISH_TIMEOUT_SECONDS=0)
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_action_failure")
    def test_replies_for_each_action_which_did_not_succeed(self, mock_notify_failure, mock_notify_end):
        start_time = timezone.now() - timedelta(seconds=1)
        self._create_action(
            PostPublishActionType.S3_ACL,
            PostPublishActionStatus.SUCCESSFUL,
            finished_at=timezone.now(),
        )
        timed_out = self._create_action(PostPublishActionType.CACHE_PURGE, PostPublishActionStatus.RUNNING)
        search_failures = [
            self._create_action(
                PostPublishActionType.SEARCH_UPDATED,
                PostPublishActionStatus.FAILED,
                page=page,
                finished_at=timezone.now(),
            )
            for page in reversed(self.pages)
        ]
        manager = MagicMock()
        manager.attach_mock(mock_notify_failure, "failure")
        manager.attach_mock(mock_notify_end, "end")

        post_publish_notify_slack(start_time, self.bundle)

        timed_out.refresh_from_db()
        self.assertIsNotNone(timed_out.timed_out_at)

        self.assertEqual(
            [
                (name, call_args[1].pk, call_args[2].pk) if name == "failure" else (name, *call_args)
                for name, call_args, _kwargs in manager.mock_calls
            ],
            [
                ("failure", self.pages[0].pk, timed_out.pk),
                ("failure", self.pages[0].pk, search_failures[1].pk),
                ("failure", self.pages[1].pk, search_failures[0].pk),
                ("end", self.bundle, start_time, timed_out.finished_at),
            ],
        )

    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_end")
    @patch("cms.post_publish_actions.utils.notify_slack_of_post_publish_action_failure")
    def test_no_failure_replies_when_all_actions_succeed(self, mock_notify_failure, mock_notify_end):
        for action_type in PostPublishActionType:
            self._create_action(action_type, PostPublishActionStatus.SUCCESSFUL, finished_at=timezone.now())

        post_publish_notify_slack(timezone.now(), self.bundle)

        mock_notify_failure.assert_not_called()
        mock_notify_end.assert_called_once()
