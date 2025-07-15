import sys
from io import StringIO
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.utils import OperationalError
from postgres_lock.lock import PostgresLock


class Command(BaseCommand):
    help = "Lock database migrations from being run concurrently"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--timeout",
            type=int,
            help="How many seconds to wait for the lock before timing out (default: %(default)r)",
            default=600,
        )
        parser.add_argument(
            "--skip-unapplied-check",
            action="store_true",
            help=(
                "Skip the unapplied migrations check. "
                "This will always attempt to acquire the lock, even if there are no migrations to run."
            ),
        )

    def _has_unapplied_migrations(self) -> bool:
        """Determine whether there are migrations to apply.

        This is done by running `migrate --plan --check` and checking the output / return code
        """
        output = StringIO()
        try:
            call_command("migrate", check_unapplied=True, plan=True, interactive=False, stdout=output)
        except SystemExit as e:
            if e.code == 1:
                return "No planned migration operations" not in output.getvalue()
        return False

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["skip_unapplied_check"] and not self._has_unapplied_migrations():
            # If there are no migrations to run, don't touch the lock to
            # let the process stop sooner
            self.stdout.write("No migrations to run.", self.style.SUCCESS)
            return

        with connections[DEFAULT_DB_ALIAS].cursor() as cursor:
            # Set a statement timeout to terminate if the lock is held for too long
            cursor.execute("SET statement_timeout = %s;", [options["timeout"] * 1000])

        self.stdout.write("Acquiring lock...", self.style.MIGRATE_HEADING)

        try:
            # Attempt to acquire the lock. The context manager will block until the lock is acquired.
            with PostgresLock(name="locked_migrate", using=DEFAULT_DB_ALIAS):
                self.stdout.write("Lock acquired - running migrations.", self.style.SUCCESS)

                with connections[DEFAULT_DB_ALIAS].cursor() as cursor:
                    # Reset statement timeout before running migrations
                    cursor.execute("SET statement_timeout = DEFAULT;")

                call_command("migrate", interactive=False)

        except OperationalError as e:
            if "statement timeout" in str(e):
                # Show a nicer error message on timeout
                self.stdout.write("Lock took too long to acquire - aborting", self.style.ERROR)
                sys.exit(1)
            else:
                raise
