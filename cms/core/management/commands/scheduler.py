import atexit
import signal
from functools import partial
from typing import Any

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """APSchedule management command."""

    def handle(self, *args: Any, **options: Any) -> None:
        """Defines the scheduler and its cleanup."""
        self.scheduler = BlockingScheduler(executors={"default": ThreadPoolExecutor()})  # pylint: disable=W0201

        self.setup_signals()

        self.configure_scheduler()

        self.scheduler.start()

    def setup_signals(self) -> None:
        """Sets up the shutdown handlers for termination signals."""
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        atexit.register(self.shutdown)

    def shutdown(self, _signum: int | None = None, _frame: Any | None = None) -> None:
        """Shutdown handler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def add_management_command(self, command_name: str, trigger: CronTrigger, **kwargs: Any) -> None:
        """Adds the given management command to the list of scheduled jobs."""
        func = partial(call_command, command_name, **kwargs)
        self.scheduler.add_job(func, name=command_name, trigger=trigger)

    def configure_scheduler(self) -> None:
        """Configures the scheduler and triggers."""
        # "second=0" run the task every minute, on the minute (ie when the seconds = 0)
        self.add_management_command("publish_bundles", CronTrigger(second=0))

        # Run every 5 minutes.
        # See https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html#expression-types
        self.add_management_command("publish_scheduled_without_bundles", CronTrigger(minute="*/5"))

        # Sync teams
        if settings.AWS_COGNITO_TEAM_SYNC_ENABLED:
            self.add_management_command(
                "sync_teams", CronTrigger(minute=f"*/{settings.AWS_COGNITO_TEAM_SYNC_FREQUENCY}")
            )
