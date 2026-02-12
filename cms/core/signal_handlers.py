from typing import Any

from django.db.models.signals import pre_save
from wagtail.models import Page, Revision, get_page_models


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


def register_signal_handlers() -> None:
    for model in get_page_models():
        pre_save.connect(remove_go_live_seconds, sender=model)

    pre_save.connect(remove_approved_go_live_seconds, sender=Revision)
