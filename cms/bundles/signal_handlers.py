from typing import TYPE_CHECKING, Any

from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.log_actions import log
from wagtail.models import Page, WorkflowState
from wagtail.signals import workflow_cancelled

from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.notifications.email import send_bundle_in_review_email, send_bundle_published_email
from cms.bundles.notifications.slack import notify_slack_of_status_change

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise

    from cms.users.models import User


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
            if bundle_team.team.is_active and not bundle_team.preview_notification_sent
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


@receiver(workflow_cancelled, sender=WorkflowState)
def check_and_unschedule_bundle_on_page_workflow_cancellation(
    instance: WorkflowState, user: "User", **kwargs: Any
) -> None:
    if not isinstance(instance.content_object, Page):
        return

    page = instance.content_object.specific_deferred
    if not page.active_bundle:
        return

    if page.active_bundle.status != BundleStatus.APPROVED:
        return

    bundle: Bundle = page.active_bundle
    bundle.status = BundleStatus.IN_REVIEW
    bundle.save()

    original_status: StrOrPromise = BundleStatus.APPROVED.label
    log_kwargs: dict = {
        "content_changed": False,
        "data": {
            "old": original_status,
            "new": BundleStatus.IN_REVIEW.label,
        },
    }

    context_message = (
        f"The bundle is no longer ready to publish because a bundled page ({page.get_admin_display_title()}) "
        "is no longer ready to publish."
    )
    notify_slack_of_status_change(
        bundle, original_status, user=user, url=bundle.full_inspect_url, context_message=context_message
    )

    # now log the status change
    log(
        action="bundles.update_status",
        instance=bundle,
        **log_kwargs,
    )
