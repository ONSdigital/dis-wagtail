import logging

from wagtail.admin.mail import send_mail

from cms.bundles.models import Bundle, BundleTeam
from cms.teams.models import Team

logger = logging.getLogger(__name__)


def _send_bundle_email(bundle: Bundle, team: Team, subject: str, message: str) -> None:
    """Helper to send an email to all active users in the team."""
    active_user_emails = team.users.filter(is_active=True).values_list("email", flat=True)
    send_mail(
        subject=subject,
        message=message,
        recipient_list=active_user_emails,
    )
    logger.info(
        "Email notification sent",
        extra={
            "bundle_name": bundle.name,
            "team_name": team.name,
            "email_subject": subject,
        },
    )


def send_bundle_in_review_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a bundle is ready for review."""
    bundle: Bundle = bundle_team.parent
    team: Team = bundle_team.team  # type: ignore[assignment]
    subject = f'Bundle "{bundle.name}" is ready for review'
    message = (
        f'You are a reviewer in the team "{team.name}". '
        f'Bundle "{bundle.name}" is now ready for review. URL: {bundle.inspect_url}'
    )
    _send_bundle_email(bundle, team, subject, message)
    bundle_team.preview_notification_sent = True
    bundle_team.save(update_fields=["preview_notification_sent"])


def send_bundle_published_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a bundle is published."""
    bundle: Bundle = bundle_team.parent
    team: Team = bundle_team.team  # type: ignore[assignment]
    subject = f'Bundle "{bundle.name}" has been published'
    message = (
        f'You are a reviewer in the team "{team.name}".'
        f'Bundle "{bundle.name}" status changed to Published. URL: {bundle.inspect_url}'
    )
    _send_bundle_email(bundle, team, subject, message)
