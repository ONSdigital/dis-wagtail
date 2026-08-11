from datetime import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory
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
