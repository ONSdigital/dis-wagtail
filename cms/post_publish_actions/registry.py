from collections.abc import Callable
from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured
from wagtail.models import Page

from .models import PostPublishActionType

if TYPE_CHECKING:
    from cms.bundles.models import Bundle


ActionHandler = Callable[[Page, "Bundle | None"], None]

_registry: dict[PostPublishActionType, ActionHandler] = {}


def register_post_publish_action(action_type: PostPublishActionType, action_handler: ActionHandler) -> None:
    if action_type in _registry:
        raise ImproperlyConfigured(f"{action_type} is already configured: {_registry[action_type]}")

    _registry[action_type] = action_handler


def post_publish_action(action_type: PostPublishActionType) -> Callable[[ActionHandler], ActionHandler]:
    def decorator(action_handler: ActionHandler) -> ActionHandler:
        register_post_publish_action(action_type, action_handler)
        return action_handler

    return decorator


def get_post_publish_actions() -> dict[PostPublishActionType, ActionHandler]:
    return _registry
