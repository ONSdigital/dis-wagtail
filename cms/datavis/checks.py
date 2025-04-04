from collections.abc import Iterator
from typing import Any

from django.apps import apps
from django.core.checks import CheckMessage, Error, register
from wagtail import blocks
from wagtail.models import Page

from cms.core.fields import StreamField
from cms.datavis.blocks.base import BaseVisualisationBlock
from cms.datavis.models.mixins import VisualisationsPageMixin


@register()
def check_visualisation_blocks_mixin(*args: Any, **kwargs: Any) -> Iterator[CheckMessage]:
    """Check that any page using BaseVisualisationBlock in its StreamFields
    inherits from VisualisationsPageMixin.
    """
    # Get all page models
    for model in apps.get_models():
        if not issubclass(model, Page):
            continue

        # Find any StreamField instances
        for field in model._meta.fields:
            if not isinstance(field, StreamField):
                continue

            if _contains_visualisation_block(field.stream_block) and not issubclass(model, VisualisationsPageMixin):
                yield Error(
                    f"Page model {model.__name__} has a '{field.name}' StreamField that can contain "
                    "BaseVisualisationBlock, but it does not subclass VisualisationsPageMixin",
                    hint="Add VisualisationsPageMixin to the page model's parent classes",
                    obj=model,
                    id="datavis.E001",
                )


def _contains_visualisation_block(block: blocks.Block) -> bool:
    """Recursively check whether a block, or any descendant block, is an instance
    of BaseVisualisationBlock.
    """
    # Check this block
    if isinstance(block, BaseVisualisationBlock):
        return True

    # Check within child blocks
    if hasattr(block, "child_blocks"):
        return any(_contains_visualisation_block(child) for child in block.child_blocks.values())

    return False
