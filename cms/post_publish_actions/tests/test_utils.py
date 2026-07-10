# pylint: disable=protected-access
from unittest.mock import MagicMock, patch

from django.test import TestCase

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.utils import get_active_bundle_for_page
from cms.home.models import HomePage
from cms.post_publish_actions import registry
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionType
from cms.post_publish_actions.utils import run_post_publish_actions_for


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
