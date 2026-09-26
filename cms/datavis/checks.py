from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.checks import Error, register

if TYPE_CHECKING:
    from django.apps import AppConfig


@register()
def check_chart_exporter_api(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    errors: list[Error] = []

    if not getattr(settings, "CMS_CHART_EXPORTER_API_ENABLED", False):
        return errors

    if not getattr(settings, "CMS_CHART_EXPORTER_API_BASE_URL", None):
        errors.append(
            Error(
                "CMS_CHART_EXPORTER_API_BASE_URL is required when CMS_CHART_EXPORTER_API_ENABLED is True.",
                hint="Set CMS_CHART_EXPORTER_API_BASE_URL to the chart exporter API endpoint.",
                id="datavis.E001",
            )
        )

    return errors
