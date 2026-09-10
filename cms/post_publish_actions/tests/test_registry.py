from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from cms.post_publish_actions import registry
from cms.post_publish_actions.models import PostPublishActionType
from cms.post_publish_actions.registry import (
    PostPublishActionPriority,
    get_post_publish_action_for_type,
    get_post_publish_actions,
    register_post_publish_action,
)


def _noop_handler(page, bundle):  # pylint: disable=unused-argument
    pass


class RegistryTestCase(SimpleTestCase):
    def test_every_action_type_has_a_handler(self):
        """Test each type has a handler registered to avoid key errors."""
        self.assertEqual(set(get_post_publish_actions()), set(PostPublishActionType))

    def test_get_post_publish_action_for_type(self):
        """Smoketest for action fetching capability."""
        handler = get_post_publish_action_for_type(PostPublishActionType.SEARCH_UPDATED)

        self.assertEqual(handler.__name__, "update_index_post_publish_action")

    def test_cannot_register_two_of_an_action_type(self):
        """Smoketest for action registration failure."""
        with self.assertRaises(ImproperlyConfigured):
            register_post_publish_action(PostPublishActionType.SEARCH_UPDATED, _noop_handler)

        self.assertIsNot(get_post_publish_action_for_type(PostPublishActionType.SEARCH_UPDATED), _noop_handler)


class RegistryPriorityTestCase(SimpleTestCase):
    def setUp(self):
        patcher = patch.dict(registry._registry, {}, clear=True)  # pylint: disable=protected-access
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_actions_are_returned_highest_priority_first(self):
        """Test that actions are returned in order of priority."""
        register_post_publish_action(
            PostPublishActionType.SEARCH_UPDATED, _noop_handler, priority=PostPublishActionPriority.LOW
        )
        register_post_publish_action(
            PostPublishActionType.S3_ACL, _noop_handler, priority=PostPublishActionPriority.HIGH
        )
        register_post_publish_action(
            PostPublishActionType.CACHE_PURGE, _noop_handler, priority=PostPublishActionPriority.MEDIUM
        )

        actions = get_post_publish_actions()

        self.assertEqual(
            list(actions.keys()),
            [
                PostPublishActionType.S3_ACL,
                PostPublishActionType.CACHE_PURGE,
                PostPublishActionType.SEARCH_UPDATED,
            ],
        )

    def test_equal_priorities_keep_their_registration_order(self):
        register_post_publish_action(
            PostPublishActionType.SEARCH_UPDATED, _noop_handler, priority=PostPublishActionPriority.MEDIUM
        )
        register_post_publish_action(
            PostPublishActionType.S3_ACL, _noop_handler, priority=PostPublishActionPriority.MEDIUM
        )

        self.assertEqual(
            list(get_post_publish_actions().keys()),
            [PostPublishActionType.SEARCH_UPDATED, PostPublishActionType.S3_ACL],
        )

    def test_registration_defaults_to_medium_priority(self):
        register_post_publish_action(PostPublishActionType.SEARCH_UPDATED, _noop_handler)

        self.assertEqual(
            registry._registry[PostPublishActionType.SEARCH_UPDATED],  # pylint: disable=protected-access
            registry.RegisteredPostPublishAction(handler=_noop_handler, priority=PostPublishActionPriority.MEDIUM),
        )

    def test_decorator_passes_priority_to_registration(self):
        @registry.post_publish_action(PostPublishActionType.SEARCH_UPDATED, priority=PostPublishActionPriority.HIGH)
        def handler(page, bundle):  # pylint: disable=unused-argument
            pass

        self.assertEqual(
            registry._registry[PostPublishActionType.SEARCH_UPDATED],  # pylint: disable=protected-access
            registry.RegisteredPostPublishAction(handler=handler, priority=PostPublishActionPriority.HIGH),
        )
