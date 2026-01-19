"""Audit logging infrastructure for protective monitoring.

This module provides signal handlers that mirror all Wagtail log entries to stdout
in JSON format for protective monitoring and SIEM integration.
"""

import logging
from typing import TYPE_CHECKING, Any

from django.db.models.signals import post_save
from django.dispatch import receiver

if TYPE_CHECKING:
    from wagtail.models import ModelLogEntry, PageLogEntry

audit_logger = logging.getLogger("cms.audit")


@receiver(post_save, sender="wagtailcore.PageLogEntry")
@receiver(post_save, sender="wagtailcore.ModelLogEntry")
def mirror_log_entry_to_stdout(
    sender: type,  # pylint: disable=unused-argument
    instance: PageLogEntry | ModelLogEntry,
    created: bool,
    **kwargs: Any,
) -> None:
    """Mirror all Wagtail log entries to stdout for protective monitoring.

    This signal handler intercepts all log entries created by Wagtail (both PageLogEntry
    and ModelLogEntry) and outputs them to stdout as JSON-formatted logs.

    Args:
        sender: The model class that sent the signal
        instance: The log entry instance that was created
        created: Whether this is a new instance (only process new instances)
        **kwargs: Additional keyword arguments from the signal
    """
    if not created:
        return

    audit_logger.info(
        instance.action,
        extra={
            "event": instance.action,
            "object_type": instance.content_type.model if instance.content_type else None,
            "object_id": instance.object_id,
            "object_label": instance.label,
            "user_id": instance.user_id,
            "email": instance.user.email if instance.user else None,
            "data": instance.data or {},
            "timestamp": instance.timestamp.isoformat(),
        },
    )
