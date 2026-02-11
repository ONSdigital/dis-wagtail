from collections.abc import Iterator
from typing import Any

from django.core.checks import CheckMessage, Tags, register

from cms.core.checks import check_page_models_for_story_block
from cms.standard_pages.blocks import CoreStoryBlock


@register(Tags.models)
def check_wagtail_pages(*args: Any, **kwargs: Any) -> Iterator[CheckMessage]:
    """Check that page models using CoreStoryBlock have the correct form class."""
    yield from check_page_models_for_story_block(CoreStoryBlock)
