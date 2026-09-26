import logging
from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.admin.signal_handlers import workflow_approval_email_notifier
from wagtail.models import WorkflowState
from wagtail.signals import workflow_approved

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.notifications.email import send_bundle_in_review_email, send_bundle_published_email
from cms.post_publish_actions.signal_handlers import is_publishing_bundle

logger = logging.getLogger(__name__)

# See: https://github.com/wagtail/wagtail/blob/a69ebb39a780b470e7b0c01f0949035d8e02377c/wagtail/admin/signal_handlers.py#L41
WORKFLOW_APPROVED_DISPATCH_UID = "workflow_state_approved_email_notification"


@receiver(post_save, sender=BundleTeam)
def handle_bundle_team_post_save(instance: BundleTeam, created: bool, **kwargs: Any) -> None:
    """Handle when a preview team is assigned to a bundle in review."""
    if created and instance.parent.status == BundleStatus.IN_REVIEW:
        send_bundle_in_review_email(bundle_team=instance)


@receiver(post_save, sender=Bundle)
def handle_bundle_in_preview(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is set to In Preview."""
    if instance.status == BundleStatus.IN_REVIEW:
        active_unnotified_bundle_teams = [
            bundle_team
            for bundle_team in instance.teams.get_object_list()  # type: ignore[attr-defined]
            if bundle_team.pk is not None and bundle_team.team.is_active and not bundle_team.preview_notification_sent
        ]
        for bundle_team in active_unnotified_bundle_teams:
            send_bundle_in_review_email(bundle_team=bundle_team)


@receiver(post_save, sender=Bundle)
def handle_bundle_publication(instance: Bundle, **kwargs: Any) -> None:
    """Handle when a bundle is published."""
    if instance.status == BundleStatus.PUBLISHED:
        active_bundle_teams = [
            bundle_team
            for bundle_team in instance.teams.get_object_list()  # type: ignore[attr-defined]
            if bundle_team.team.is_active
        ]
        for bundle_team in active_bundle_teams:
            send_bundle_published_email(bundle_team=bundle_team)

        # @TODO: Publish the datasets when endpoint available?


def workflow_approval_email_handler(**kwargs: Any) -> None:
    """Suppress Wagtail's page approved email when the approval is a side effect of publishing a bundle.

    Preview teams get the bundle published notification instead, so the misleading page approved email
    would otherwise be redundant.
    """
    if is_publishing_bundle():
        return

    workflow_approval_email_notifier(**kwargs)


def register_signal_handlers() -> None:
    # Disconnect first using Wagtail's workflow approved dispatch UID to ensure our
    # handler replaces the default one. Without disconnecting, our handler might
    # get silently ignored.
    workflow_approved.disconnect(sender=WorkflowState, dispatch_uid=WORKFLOW_APPROVED_DISPATCH_UID)
    workflow_approved.connect(
        workflow_approval_email_handler,
        sender=WorkflowState,
        dispatch_uid=WORKFLOW_APPROVED_DISPATCH_UID,
    )
