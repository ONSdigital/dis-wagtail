from datetime import timedelta
from http import HTTPStatus
from io import StringIO
from unittest.mock import Mock

import time_machine
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from wagtail.models import Locale
from wagtail.signals import page_published

from cms.core.tests.utils import TranslationResetMixin
from cms.standard_pages.models import InformationPage
from cms.standard_pages.tests.factories import InformationPageFactory


@override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
class ScheduledPageAliasesTestCase(TranslationResetMixin, TestCase):
    """Tests that aliases of a page that is scheduled to be published in the future isn't immediately published."""

    def setUp(self):
        page = InformationPageFactory(live=False, title="Original title")
        self.page_pk = page.pk
        self.alias = page.copy_for_translation(Locale.objects.get(language_code="cy"), copy_parents=True, alias=True)
        self.go_live_at = timezone.now() + timedelta(days=1)

    def get_page(self) -> InformationPage:
        page: InformationPage = InformationPage.objects.get(pk=self.page_pk).get_latest_revision_as_object()
        return page

    def publish(self) -> None:
        page = self.get_page()
        page.title = "Published title"
        page.save_revision().publish()

    def schedule(self) -> None:
        page = self.get_page()
        page.title = "Scheduled title"
        page.go_live_at = self.go_live_at
        page.save_revision().publish()

    def publish_scheduled(self) -> None:
        with time_machine.travel(self.go_live_at + timedelta(seconds=1)):
            call_command("publish_scheduled_without_bundles", stdout=StringIO())

    def assertAlias(self, *, live: bool, title: str) -> None:  # pylint: disable=invalid-name
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.live, live)
        self.assertEqual(self.alias.title, title)

    def test_publishing_a_page_publishes_its_alias(self):
        self.publish()
        self.assertAlias(live=True, title="Published title")

    def test_scheduling_a_page_does_not_publish_its_alias(self):
        self.schedule()
        self.assertFalse(InformationPage.objects.get(pk=self.page_pk).live)
        self.assertAlias(live=False, title="Original title")

    def test_alias_of_scheduled_page_is_not_served_until_the_page_goes_live(self):
        self.schedule()

        response = self.client.get(self.alias.get_url())
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.publish_scheduled()

        response = self.client.get(self.alias.get_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Scheduled title")

    def test_scheduling_a_page_does_not_send_page_published_for_its_aliases(self):
        receiver = Mock()
        page_published.connect(receiver, weak=False)
        self.addCleanup(page_published.disconnect, receiver)

        self.schedule()

        self.assertEqual([c for c in receiver.call_args_list if c.kwargs.get("alias")], [])

        self.publish_scheduled()

        alias_calls = [c for c in receiver.call_args_list if c.kwargs.get("alias")]
        self.assertEqual(len(alias_calls), 1)

        self.assertEqual(alias_calls[0].kwargs["instance"].pk, self.alias.pk)

    def test_scheduling_a_new_revision_of_a_live_page_does_not_update_its_aliases(self):
        self.publish()
        self.assertEqual(self.alias.title, "Published title")

        self.schedule()
        self.assertAlias(live=True, title="Published title")

        self.publish_scheduled()
        self.assertAlias(live=True, title="Scheduled title")

    def test_rescheduling_an_unpublished_page_does_not_publish_its_alias(self):
        self.publish()
        InformationPage.objects.get(pk=self.page_pk).unpublish()
        self.assertAlias(live=False, title="Published title")

        self.schedule()
        self.assertAlias(live=False, title="Published title")

        self.publish_scheduled()
        self.assertAlias(live=True, title="Scheduled title")

    def test_publishing_a_page_publishes_aliases_of_its_aliases(self):
        alias_of_alias = self.alias.create_alias(update_slug="alias-of-alias")
        self.assertFalse(alias_of_alias.live)

        self.publish()

        alias_of_alias.refresh_from_db()

        self.assertTrue(alias_of_alias.live)
        self.assertEqual(alias_of_alias.title, "Published title")
