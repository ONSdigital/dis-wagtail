from typing import Any

from crum import get_current_user
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.log_actions import log

Image = get_image_model()
Document = get_document_model()


@receiver(post_save, sender=Image)
@receiver(post_save, sender=Document)
def log_image_save(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Log image/document creation and edits for audit trail."""
    user = get_current_user()
    action = "wagtail.create" if created else "wagtail.edit"

    # user will be None if change happens in management commands/shell
    log(instance=instance, action=action, user=user)


@receiver(pre_delete, sender=Image)
@receiver(pre_delete, sender=Document)
def log_image_delete(sender: type, instance: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    """Log image/document deletion for audit trail."""
    user = get_current_user()
    action = "wagtail.delete"

    # user will be None if change happens in management commands/shell
    log(instance=instance, action=action, user=user)
