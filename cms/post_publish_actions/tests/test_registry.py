from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from cms.post_publish_actions.models import PostPublishActionType
from cms.post_publish_actions.registry import (
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
