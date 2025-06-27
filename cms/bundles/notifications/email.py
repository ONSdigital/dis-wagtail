import logging

from wagtail.admin.mail import send_mail

from cms.bundles.models import Bundle, BundleTeam
from cms.teams.models import Team

logger = logging.getLogger(__name__)


def _send_bundle_email(bundle: Bundle, team: Team, subject: str, message: str) -> None:
    """Helper to send an email to all active users in the team."""
    email_id_tuples = team.users.filter(is_active=True).values_list("email", "id")
    active_user_emails = []

    for email, user_id in email_id_tuples:
        if not email:
            logger.error(
                "Attempted to send an email to a user without an email address",
                extra={
                    "user_id": user_id,
                    "team_name": team.name,
                    "bundle_name": bundle.name,
                    "email_subject": subject,
                },
            )
        else:
            active_user_emails.append(email)

    try:
        send_mail(
            subject=subject,
            message=message,
            recipient_list=active_user_emails,
        )
        logger.info(
            "Email notification sent",
            extra={
                "team_name": team.name,
                "bundle_name": bundle.name,
                "email_subject": subject,
                "recipients": active_user_emails,
            },
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(
            "Failed to send bundle notification email",
            exc_info=True,
            extra={
                "team_name": team.name,
                "bundle_name": bundle.name,
                "email_subject": subject,
                "recipients": active_user_emails,
                "error_message": str(e),
            },
        )


def send_bundle_in_review_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a bundle is ready for review."""
    bundle: Bundle = bundle_team.parent
    team: Team = bundle_team.team  # type: ignore[assignment]
    subject = f'Bundle "{bundle.name}" is ready for review'
    message = (
        f'You are a reviewer in the team "{team.name}". '
        f'Bundle "{bundle.name}" is now ready for review. URL: {bundle.full_inspect_url}'
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
        f'Bundle "{bundle.name}" status changed to Published. URL: {bundle.full_inspect_url}'
    )
    _send_bundle_email(bundle, team, subject, message)
