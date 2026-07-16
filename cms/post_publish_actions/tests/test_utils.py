# pylint: disable=protected-access
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
from cms.bundles.utils import get_active_bundle_for_page
from cms.home.models import HomePage
from cms.post_publish_actions import registry
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionType
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
