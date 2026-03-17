from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.checks import Error, register

if TYPE_CHECKING:
    from django.apps import AppConfig


@register()
def check_florence_groups_url(app_configs: Iterable[AppConfig] | None, **kwargs: Any) -> list[Error]:  # pylint: disable=unused-argument
    errors: list[Error] = []

    if getattr(settings, "ALLOW_TEAM_MANAGEMENT", True):
        return errors

    if not getattr(settings, "AWS_COGNITO_TEAM_SYNC_ENABLED", False):
        return errors

    if not getattr(settings, "FLORENCE_GROUPS_URL", ""):
        errors.append(
            Error(
                "FLORENCE_GROUPS_URL is required when ALLOW_TEAM_MANAGEMENT is False "
                "and AWS_COGNITO_TEAM_SYNC_ENABLED is True.",
                hint="Set FLORENCE_GROUPS_URL to the Florence groups URL.",
                id="teams.E001",
            )
        )

    return errors
