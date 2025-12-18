"""Wagtail hooks for image audit logging."""

from typing import TYPE_CHECKING

from wagtail import hooks
from wagtail.log_actions import log

if TYPE_CHECKING:
    from django.http import HttpRequest

    from cms.images.models import CustomImage


@hooks.register("after_create_image")
def log_image_create(request: "HttpRequest", image: "CustomImage") -> None:
    """Log image creation for audit trail.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#after-create-image
    """
    log(action="wagtail.create", instance=image)


@hooks.register("after_edit_image")
def log_image_edit(request: "HttpRequest", image: "CustomImage") -> None:
    """Log image edits for audit trail.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#after-edit-image
    """
    log(action="wagtail.edit", instance=image)


@hooks.register("after_delete_image")
def log_image_delete(request: "HttpRequest", image: "CustomImage") -> None:
    """Log image deletion for audit trail.

    @see https://docs.wagtail.org/en/stable/reference/hooks.html#after-delete-image
    """
    log(action="wagtail.delete", instance=image)
