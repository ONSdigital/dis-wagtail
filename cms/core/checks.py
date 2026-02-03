from collections.abc import Iterator
from typing import Any

from django.apps import apps
from django.core.checks import CheckMessage, Error, Tags, register
from wagtail.contrib.settings.models import (
    BaseGenericSetting as WagtailBaseGenericSetting,
)
from wagtail.contrib.settings.models import (
    BaseSiteSetting as WagtailBaseSiteSetting,
)
from wagtail.models import get_page_models

from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.fields import StreamField
from cms.core.forms import PageWithEquationsAdminForm
from cms.core.models.base import BaseGenericSetting, BaseSiteSetting
from cms.standard_pages.blocks.stream_blocks import CoreStoryBlock


@register
def check_wagtail_settings(*args: Any, **kwargs: Any) -> Iterator[CheckMessage]:
    for model in apps.get_models():
        if issubclass(model, WagtailBaseSiteSetting) and not issubclass(model, BaseSiteSetting):
            yield Error(
                "Site setting does not extend project base.",
                hint=f"Ensure site setting extends {BaseSiteSetting!r}.",
                obj=model,
            )

        elif issubclass(model, WagtailBaseGenericSetting) and not issubclass(model, BaseGenericSetting):
            yield Error(
                "Generic setting does not extend project base.",
                hint=f"Ensure generic setting extends {BaseGenericSetting!r}",
                obj=model,
            )


@register(Tags.models)
def check_wagtail_pages(*args: Any, **kwargs: Any) -> Iterator[CheckMessage]:
    for model in get_page_models():
        for field in model._meta.get_fields():
            if (
                isinstance(field, StreamField)
                and isinstance(field.block_types_arg, SectionStoryBlock | CoreStoryBlock)
                and not issubclass(model.base_form_class, PageWithEquationsAdminForm)
            ):
                yield Error(
                    f"Page model {model.__name__} does not use the correct base form class.",
                    hint=f"Set the model's base_form_class to {PageWithEquationsAdminForm!r}"
                    " or a subclass of that class.",
                    obj=model,
                )
