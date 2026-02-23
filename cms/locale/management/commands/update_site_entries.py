import logging
import sys
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.management.base import BaseCommand
from wagtail.models import Site

from cms.core.db_router import force_write_db

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.core.management.base import CommandParser


class Command(BaseCommand):
    """A management command to update Site entries based on CMS_HOSTNAME_LOCALE_MAP."""

    dry_run: bool

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run -- don't change anything.",
        )

    def update_site(self, site: Site, hostname: str) -> None:
        update_fields = {}
        if site.hostname != hostname:
            site.hostname = hostname
            update_fields["hostname"] = hostname

        if site.port != 443:  # noqa: PLR2004
            site.port = 443
            update_fields["port"] = "443"

        if not update_fields:
            self.stdout.write(self.style.WARNING(f"No updates needed for {site}"))
            return

        update_info = ", ".join([f"{k}={v}" for k, v in update_fields.items()])
        self.stdout.write(self.style.SUCCESS(f"Updating {site} with {update_info}"))

        if not self.dry_run:
            site.save(update_fields=list(update_fields.keys()))

    @force_write_db()
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.CMS_USE_SUBDOMAIN_LOCALES:
            self.stdout.write(self.style.ERROR("Cannot proceed. Sub-domain locale functionality is disabled."))
            sys.exit()

        self.dry_run = options["dry_run"]
        if self.dry_run:
            self.stdout.write("Will do a dry run.")

        hostnames = {settings.CMS_HOSTNAME_LOCALE_MAP[host]: host for host in settings.CMS_HOSTNAME_ALTERNATIVES}
        mapping = [
            (settings.LANGUAGE_CODE, "ons.gov.uk"),
            ("cy", "cy.ons.gov.uk"),
        ]

        for language_code, default_hostname in mapping:
            try:
                site = Site.objects.get(root_page__locale__language_code=language_code)
                hostname = hostnames.get(language_code, default_hostname)
                self.update_site(site, hostname)
            except Site.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Could not find a site record for {language_code=}"))
