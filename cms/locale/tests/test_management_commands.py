from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from wagtail.models import Site

from cms.home.models import HomePage


@override_settings(
    CMS_USE_SUBDOMAIN_LOCALES=True,
    CMS_HOSTNAME_LOCALE_MAP={
        "ons.localhost": "en-gb",
        "pub.ons.localhost": "en-gb",
        "cy.ons.localhost": "cy",
        "cy.pub.ons.localhost": "cy",
    },
    CMS_HOSTNAME_ALTERNATIVES={
        "ons.localhost": "pub.ons.localhost",
        "cy.ons.localhost": "cy.pub.ons.localhost",
    },
)
class UpdateSiteEntriesCommandTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = HomePage.objects.first()
        cls.welsh_home = cls.home.aliases.first()

        cls.english_site = Site.objects.get(is_default_site=True)
        cls.welsh_site = Site.objects.get(root_page=cls.welsh_home)

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

        # Reset sites to known state before each test
        self.english_site.hostname = "old.example.com"
        self.english_site.port = 80
        self.english_site.save(update_fields=["hostname", "port"])

        self.welsh_site.hostname = "old.cy.example.com"
        self.welsh_site.port = 80
        self.welsh_site.save(update_fields=["hostname", "port"])

    def call_command(self, *args, **kwargs):
        call_command(
            "update_site_entries",
            *args,
            stdout=self.stdout,
            stderr=self.stderr,
            **kwargs,
        )

    def test_updates_site_hostnames_and_ports(self):
        self.call_command()

        self.english_site.refresh_from_db()
        self.welsh_site.refresh_from_db()

        self.assertEqual(self.english_site.hostname, "ons.localhost")
        self.assertEqual(self.english_site.port, 443)
        self.assertEqual(self.welsh_site.hostname, "cy.ons.localhost")
        self.assertEqual(self.welsh_site.port, 443)

    def test_dry_run_does_not_update_sites(self):
        self.call_command(dry_run=True)

        self.english_site.refresh_from_db()
        self.welsh_site.refresh_from_db()

        self.assertEqual(self.english_site.hostname, "old.example.com")
        self.assertEqual(self.english_site.port, 80)
        self.assertEqual(self.welsh_site.hostname, "old.cy.example.com")
        self.assertEqual(self.welsh_site.port, 80)

    def test_dry_run_outputs_planned_changes(self):
        self.call_command(dry_run=True)

        output = self.stdout.getvalue()
        self.assertIn("Will do a dry run.", output)
        self.assertIn(f"Updating {self.english_site} with hostname=ons.localhost, port=443", output)

    def test_no_updates_needed(self):
        """When sites already have the correct hostname and port, no updates are made."""
        self.english_site.hostname = "ons.localhost"
        self.english_site.port = 443
        self.english_site.save(update_fields=["hostname", "port"])

        self.welsh_site.hostname = "cy.ons.localhost"
        self.welsh_site.port = 443
        self.welsh_site.save(update_fields=["hostname", "port"])

        self.call_command()

        output = self.stdout.getvalue()
        self.assertIn("No updates needed", output)

    @override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
    def test_exits_when_subdomain_locales_disabled(self):
        with self.assertRaises(SystemExit):
            self.call_command()

        output = self.stdout.getvalue()
        self.assertIn("Cannot proceed. Sub-domain locale functionality is disabled.", output)

    def test_handles_missing_site(self):
        """When a Site for a locale doesn't exist, an error is reported."""
        self.welsh_site.delete()

        self.call_command()

        output = self.stdout.getvalue()
        self.assertIn("Could not find a site record for language_code='cy'", output)

        # English site should still be updated
        self.english_site.refresh_from_db()
        self.assertEqual(self.english_site.hostname, "ons.localhost")

    @override_settings(
        CMS_HOSTNAME_LOCALE_MAP={},
        CMS_HOSTNAME_ALTERNATIVES={},
    )
    def test_falls_back_to_default_hostnames(self):
        """When no hostname alternatives are configured, default hostnames are used."""
        self.call_command()

        self.english_site.refresh_from_db()
        self.welsh_site.refresh_from_db()

        self.assertEqual(self.english_site.hostname, "ons.gov.uk")
        self.assertEqual(self.welsh_site.hostname, "cy.ons.gov.uk")

    def test_only_updates_changed_fields(self):
        """When only port needs updating, hostname is not included in update_fields."""
        self.english_site.hostname = "ons.localhost"
        self.english_site.port = 80
        self.english_site.save(update_fields=["hostname", "port"])

        self.call_command()

        self.english_site.refresh_from_db()
        self.assertEqual(self.english_site.hostname, "ons.localhost")
        self.assertEqual(self.english_site.port, 443)

        self.assertIn(f"Updating {self.english_site} with port=443", self.stdout.getvalue())
