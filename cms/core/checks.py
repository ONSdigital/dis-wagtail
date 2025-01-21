from collections.abc import Iterator
from typing import Any

from django.apps import apps
from django.core.checks import CheckMessage, Error, register
from wagtail.contrib.settings.models import (
    BaseGenericSetting as WagtailBaseGenericSetting,
)
from wagtail.contrib.settings.models import (
    BaseSiteSetting as WagtailBaseSiteSetting,
)

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
