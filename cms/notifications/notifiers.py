import logging
from abc import ABC, abstractmethod

from cms.bundles.models import Bundle
from cms.teams.models import Team

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    @abstractmethod
    def send_notification(self, bundle: Bundle, teams: Team, message: str) -> None:
        """Each child class defines how to actually send
        the message (e.g., Email, logging, etc.).
        """

    def send_notification_to_all_teams(self, bundle: Bundle, message: str) -> None:
        """Helper method to send a notification to all teams associated with the bundle."""
        return self.send_notification(
            bundle=bundle,
            teams=Team.objects.filter(pk__in=bundle.active_team_ids),
            message=message,
        )


class LogNotifier(BaseNotifier):
    def send_notification(self, bundle: Bundle, teams: list[Team], message: str) -> None:
        for team in teams:
            for user in team.users.all():
                if user.is_active:
                    logger.info(
                        message,
                        extra={
                            "bundle_id": bundle.id,
                            "event": "bundle_status_changed_to_in_review",
                            "team_id": team,
                            "user_id": user.id,
                        },
                    )


class AWS_SES_Notifier(BaseNotifier):  # pylint: disable=invalid-name
    def send_notification(self, bundle: Bundle, teams: Team, message: str) -> None: ...
