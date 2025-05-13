import logging
from abc import ABC, abstractmethod

from cms.bundles.models import Bundle
from cms.teams.models import Team

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    @abstractmethod
    def send_notification(bundle: Bundle, teams: Team, message: str) -> None:
        """Each child class defines how to actually send
        the message (e.g., Email, logging, etc.).
        """

    def send_notification_to_all_teams(self, bundle: Bundle, message: str) -> None:
        """Helper method to send a notification to all teams associated with the bundle."""
        return self.send_notification(
            bundle=bundle,
            teams=bundle.teams.all(),
            message=message,
        )


class LogNotifier(BaseNotifier):
    def send_notification(self, preview_teams: Team, bundle: Bundle, message: str) -> None:
        for team in preview_teams:
            for user in team.users.all():
                if user.is_active:
                    logger.info(
                        "Bundle status changed to 'in review'",
                        extra={
                            "bundle_id": bundle.id,
                            "event": "bundle_status_changed_to_in_review",
                            "team_id": team,
                            "user_id": user.id,
                        },
                    )


class AWS_SES_Notifier(BaseNotifier): ...
