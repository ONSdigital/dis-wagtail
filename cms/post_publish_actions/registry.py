from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured
from wagtail.models import Page

from .models import PostPublishActionType

if TYPE_CHECKING:
    from cms.bundles.models import Bundle


ActionHandler = Callable[[Page, "Bundle | None"], None]


class PostPublishActionPriority(IntEnum):
    """Defines the priority of a post-publish action. Lower numbers are higher priority."""

    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass(frozen=True)
class RegisteredPostPublishAction:
    handler: ActionHandler
    priority: int = PostPublishActionPriority.MEDIUM


_registry: dict[PostPublishActionType, RegisteredPostPublishAction] = {}


def register_post_publish_action(
    action_type: PostPublishActionType, action_handler: ActionHandler, priority: int = PostPublishActionPriority.MEDIUM
) -> None:
    if action_type in _registry:
        raise ImproperlyConfigured(f"{action_type} is already configured: {_registry[action_type].handler}")

    _registry[action_type] = RegisteredPostPublishAction(handler=action_handler, priority=priority)


def post_publish_action(
    action_type: PostPublishActionType, priority: int = PostPublishActionPriority.MEDIUM
) -> Callable[[ActionHandler], ActionHandler]:
    def decorator(action_handler: ActionHandler) -> ActionHandler:
        register_post_publish_action(action_type, action_handler, priority=priority)
        return action_handler

    return decorator


def get_post_publish_actions() -> dict[PostPublishActionType, ActionHandler]:
    return {
        action_type: registered.handler
        for action_type, registered in sorted(_registry.items(), key=lambda item: item[1].priority)
    }


def get_post_publish_action_for_type(action_type: PostPublishActionType) -> ActionHandler:
    return _registry[action_type].handler
