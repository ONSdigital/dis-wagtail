import logging

from wagtail.admin.mail import send_mail

from cms.bundles.models import BundleTeam

logger = logging.getLogger(__name__)


def _send_bundle_email(bundle_team: BundleTeam, subject: str, message: str) -> None:
    """Helper to send an email to all active users in the team."""
    team = bundle_team.team
    active_user_emails = team.users.filter(is_active=True).values_list("email", flat=True)  # type: ignore[attr-defined]
    send_mail(
        subject=subject,
        message=message,
        recipient_list=active_user_emails,
    )
    logger.info(
        "Email notification sent",
        extra={
            "bundle_name": bundle_team.parent.name,
            "team_name": team.name,  # type: ignore[attr-defined]
            "email_subject": subject,
        },
    )


def send_team_added_to_bundle_in_review_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a team is assigned to a bundle in review."""
    bundle = bundle_team.parent
    team = bundle_team.team
    subject = f'Your team "{team.name}" was added to a bundle In review'  # type: ignore[attr-defined]
    message = (
        f"The preview team {team.name} you are a member of "  # type: ignore[attr-defined]
        f"was assigned to the bundle {bundle.name} which is In Review. URL: {bundle.inspect_url}"
    )
    _send_bundle_email(bundle_team, subject, message)


def send_bundle_status_changed_to_in_review_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a bundle status changes to In Review."""
    bundle = bundle_team.parent
    team = bundle_team.team
    subject = f'Bundle "{bundle.name}" status changed to In Review'
    message = (
        f'You are a reviewer in the team "{team.name}" '  # type: ignore[attr-defined]
        f'Bundle "{bundle.name}" status changed to In Review URL: {bundle.inspect_url}'
    )
    _send_bundle_email(bundle_team, subject, message)


def send_bundle_published_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a bundle is published."""
    bundle = bundle_team.parent
    team = bundle_team.team
    subject = f'Bundle "{bundle.name}" has been published'
    message = (
        f'You are a reviewer in the team "{team.name}" '  # type: ignore[attr-defined]
        f'Bundle "{bundle.name}" status changed to Published URL: {bundle.inspect_url}'
    )
    _send_bundle_email(bundle_team, subject, message)
