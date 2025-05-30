import os
from collections.abc import Iterator
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.checks import CheckMessage, Error, Tags, register
from wagtail.contrib.settings.models import (
    BaseGenericSetting as WagtailBaseGenericSetting,
)
from wagtail.contrib.settings.models import (
    BaseSiteSetting as WagtailBaseSiteSetting,
)
from wagtail.models import get_page_models

from cms.core.blocks.stream_blocks import CoreStoryBlock, SectionStoryBlock
from cms.core.fields import StreamField
from cms.core.forms import PageWithEquationsAdminForm
from cms.core.models.base import BaseGenericSetting, BaseSiteSetting


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


@register()
def check_aws_iam_credentials(*args: Any, **kwargs: Any) -> list[Error]:
    """Check that required IAM credentials are present when running in AWS."""
    errors: list[Error] = []

    env = os.environ.copy()

    if "AWS_REGION" not in env:
        return errors

    aws_credentials_settings = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]

    for setting in aws_credentials_settings:
        value = getattr(settings, setting, None)
        if not value:
            errors.append(
                Error(
                    f"{setting} is missing or empty.",
                )
            )

    return errors
