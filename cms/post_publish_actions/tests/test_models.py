from datetime import datetime
from unittest.mock import patch

from django.db.utils import IntegrityError
from django.test import TestCase

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
from cms.post_publish_actions import registry
from cms.post_publish_actions.models import PostPublishAction, PostPublishActionStatus, PostPublishActionType


class PostPublishActionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory()
        cls.page = StatisticalArticlePageFactory()

    def test_mark_timed_out(self):
        action = PostPublishAction.objects.create(
            bundle=self.bundle, page=self.page, action_type=PostPublishActionType.S3_ACL
        )

        PostPublishAction.objects.all().mark_timed_out()

        action.refresh_from_db()

        self.assertEqual(action.status, PostPublishActionStatus.FAILED)
        self.assertEqual(action.failed_reason, "Timeout")
        self.assertIsNone(action.duration)
        self.assertIsInstance(action.finished_at, datetime)
        self.assertIsInstance(action.timed_out_at, datetime)

    def test_constraint_with_bundle(self):
        PostPublishAction.objects.create(bundle=self.bundle, page=self.page, action_type=PostPublishActionType.S3_ACL)

        # Exact duplicate
        with self.assertRaises(IntegrityError):
            PostPublishAction.objects.create(
                bundle=self.bundle, page=self.page, action_type=PostPublishActionType.S3_ACL
            )

    def test_constraint_without_bundle(self):
        PostPublishAction.objects.create(bundle=None, page=self.page, action_type=PostPublishActionType.S3_ACL)
        with self.assertRaises(IntegrityError):
            PostPublishAction.objects.create(bundle=None, page=self.page, action_type=PostPublishActionType.S3_ACL)

    def test_active(self):
        action = PostPublishAction.objects.create(
            bundle=self.bundle, page=self.page, action_type=PostPublishActionType.S3_ACL
        )

        invalid_action = PostPublishAction.objects.create(
            bundle=self.bundle, page=self.page, action_type="DOES_NOT_EXIST"
        )

        self.assertIn(action, PostPublishAction.objects.active())
        self.assertNotIn(invalid_action, PostPublishAction.objects.active())

    def test_active_excludes_action_types_without_a_registered_handler(self):
        action = PostPublishAction.objects.create(
            bundle=self.bundle, page=self.page, action_type=PostPublishActionType.CACHE_PURGE
        )

        with patch.dict(registry._registry) as patched_registry:  # pylint: disable=protected-access
            del patched_registry[PostPublishActionType.CACHE_PURGE]
            self.assertNotIn(action, PostPublishAction.objects.active())

        self.assertIn(action, PostPublishAction.objects.active())

    def test_critical_only_includes_critical_action_types(self):
        cache_purge = PostPublishAction.objects.create(
            bundle=self.bundle, page=self.page, action_type=PostPublishActionType.CACHE_PURGE
        )
        search_updated = PostPublishAction.objects.create(
            bundle=self.bundle, page=self.page, action_type=PostPublishActionType.SEARCH_UPDATED
        )

        self.assertQuerySetEqual(PostPublishAction.objects.critical(), [cache_purge])

        with patch.dict(
            registry._registry,  # pylint: disable=protected-access
            {
                PostPublishActionType.SEARCH_UPDATED: registry.RegisteredPostPublishAction(
                    handler=registry.get_post_publish_action_for_type(PostPublishActionType.SEARCH_UPDATED),
                    critical=True,
                )
            },
        ):
            self.assertQuerySetEqual(PostPublishAction.objects.critical(), [cache_purge, search_updated], ordered=False)
