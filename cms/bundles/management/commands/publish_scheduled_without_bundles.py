import sched
import time
from collections.abc import Iterable
from datetime import datetime, timedelta
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail.models import DraftStateMixin, Page, Revision

from cms.bundles.mixins import BundledPageMixin
from cms.core.db_router import force_write_db

if TYPE_CHECKING:
    from django.core.management.base import CommandParser


class Command(BaseCommand):
    """A copy of Wagtail's publish_scheduled management command that excludes bundled objects.

    @see https://github.com/wagtail/wagtail/blob/main/wagtail/management/commands/publish_scheduled.py
    """

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry-run",
            default=False,
            help="Dry run -- don't change anything.",
        )
        parser.add_argument(
            "--include-future",
            type=int,
            default=None,
            help=(
                "Number of seconds in the future to include for publishing. "
                "Bundles in the future will be held until their publishing time."
            ),
        )

    @force_write_db()
    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = False
        if options["dry-run"]:
            self.stdout.write("Will do a dry run.")
            dry_run = True

        max_operation_date = timezone.now()
        if include_future := options["include_future"]:
            max_operation_date += timedelta(seconds=include_future)

        # Explicitly use `time.time` so enterabs can be called with absolute timestamps.
        scheduler = sched.scheduler(timefunc=time.time)

        expired_objects = list(self._models_to_unpublish(max_operation_date))
        revisions_for_publish = list(self._models_to_publish(max_operation_date))

        self.stdout.write("\n---------------------------------")
        self.stdout.write("Expired objects to be deactivated:")
        if expired_objects:
            for obj in sorted(expired_objects, key=attrgetter("expire_at")):
                self.stdout.write(f"{obj.expire_at.isoformat()}\t{obj!r}")
        else:
            self.stdout.write("No expired objects to be deactivated found.")
        self.stdout.write("\n---------------------------------")
        self.stdout.write("Revisions to be published:")
        if revisions_for_publish:
            for rp in sorted(revisions_for_publish, key=attrgetter("approved_go_live_at")):
                self.stdout.write(f"{rp.approved_go_live_at.isoformat()}\t{rp.as_object()!r}")
        else:
            self.stdout.write("No objects to go live.")

        if not dry_run:
            for instance in expired_objects:
                expire_ts = instance.expire_at.timestamp()
                scheduler.enterabs(expire_ts, 1, self._unpublish_model_action, argument=(instance,))

            for rp in revisions_for_publish:
                go_live_at_ts = rp.approved_go_live_at.timestamp()
                scheduler.enterabs(go_live_at_ts, 1, self._publish_model_action, argument=(rp,))

        # 3. Run the scheduler to run publish / unpublish content (if any)
        scheduler.run()

    def _unpublish_model_action(self, instance: DraftStateMixin) -> None:
        instance.unpublish(set_expired=True, log_action="wagtail.unpublish.scheduled")

    def _publish_model_action(self, instance: Revision) -> None:
        instance.publish(log_action="wagtail.publish.scheduled")

    def _models_to_unpublish(self, max_expire_at: datetime) -> Iterable[DraftStateMixin]:
        models = [Page]
        models += [
            model for model in apps.get_models() if issubclass(model, DraftStateMixin) and not issubclass(model, Page)
        ]
        for model in models:
            yield from model.objects.filter(live=True, expire_at__lt=max_expire_at)

    def _models_to_publish(self, max_approved_go_live_at: datetime) -> Iterable[Revision]:
        preliminary_revs_for_publishing = Revision.objects.filter(approved_go_live_at__lt=max_approved_go_live_at)
        for rev in preliminary_revs_for_publishing:
            content_object = rev.as_object()
            if not isinstance(content_object, BundledPageMixin) or not content_object.in_active_bundle:
                yield rev
