import logging

from django.conf import settings
from django.core.mail import send_mail

from cms.bundles.models import Bundle, BundleTeam

logger = logging.getLogger(__name__)


def send_team_added_to_bundle_in_review_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a team is assigned to a bundle in review."""
    bundle = bundle_team.parent
    team = bundle_team.team
    active_user_emails = [user.email for user in team.users.all() if user.is_active]
    send_mail(
        subject=f'Your team "{team.name}" was added to a bundle In review',
        message=f"""The preview team {team.name} you are a member of
        was assigned to the bundle {bundle.name} which is now In Review.""",
        from_email=settings.FROM_EMAIL,
        recipient_list=active_user_emails,
    )


def send_bundle_status_changed_to_in_review_email(bundle: Bundle) -> None:
    """Send email notification to the team members when a bundle status changes to In Review."""
    bundle_teams = bundle.teams.get_object_list()

    active_teams = [bundle_team.team for bundle_team in bundle_teams if bundle_team.team.is_active]

    for team in active_teams:
        active_user_emails = [user.email for user in team.users.all() if user.is_active]
        send_mail(
            subject=f'Bundle "{bundle.name}" status changed to In Review',
            message=f'''You are a reviewer in the team "{team.name}"
            Bundle "{bundle.name}" status changed to In Review''',
            from_email=settings.FROM_EMAIL,
            recipient_list=active_user_emails,
        )


def send_bundle_published_email(bundle_team: BundleTeam) -> None:
    """Send email notification to the team members when a bundle is published."""
    bundle = bundle_team.parent
    team = bundle_team.team
    active_user_emails = [user.email for user in bundle_team.team.users.all() if user.is_active]
    send_mail(
        subject=f'Bundle "{bundle.name}" has been published',
        message=f'''You are a reviewer in the team "{team.name}"
        Bundle "{bundle.name}" status changed to Published''',
        from_email=settings.FROM_EMAIL,
        recipient_list=active_user_emails,
    )
