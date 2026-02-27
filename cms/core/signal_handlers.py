from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.signals import setting_changed
from django.db.models.signals import pre_save
from django.utils.log import configure_logging
from wagtail.models import DraftStateMixin, Page, Revision


def remove_go_live_seconds(
    sender: Any,  # pylint: disable=unused-argument
    instance: Page,
    raw: bool,  # pylint: disable=unused-argument
    using: str,  # pylint: disable=unused-argument
    update_fields: list[str] | None,
    **kwargs: Any,
) -> None:
    if (not update_fields or "go_live_at" in update_fields) and instance.go_live_at:
        instance.go_live_at = instance.go_live_at.replace(second=0)


def remove_approved_go_live_seconds(
    sender: Any,  # pylint: disable=unused-argument
    instance: Revision,
    raw: bool,  # pylint: disable=unused-argument
    using: str,  # pylint: disable=unused-argument
    update_fields: list[str] | None,
    **kwargs: Any,
) -> None:
    if (not update_fields or "approved_go_live_at" in update_fields) and instance.approved_go_live_at:
        instance.approved_go_live_at = instance.approved_go_live_at.replace(second=0)

def reload_logging_config(*, setting: str, **kwargs: Any) -> None:
    """Reload logging config when the relevant settings change.

    @see https://code.djangoproject.com/ticket/36958#ticket
    """
    if setting in {"LOGGING", "LOGGING_CONFIG"}:
        configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)


def register_signal_handlers() -> None:
    for model in apps.get_models():
        if issubclass(model, DraftStateMixin):
            pre_save.connect(remove_go_live_seconds, sender=model)

    pre_save.connect(remove_approved_go_live_seconds, sender=Revision)

    setting_changed.connect(reload_logging_config)
