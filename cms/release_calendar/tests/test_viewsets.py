from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils import WagtailTestUtils

from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.release_calendar.viewsets import release_calendar_chooser_viewset


class TestFutureReleaseCalendarChooserViewSet(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.chooser_url = release_calendar_chooser_viewset.widget_class().get_chooser_modal_url()

        cls.provisional = ReleaseCalendarPageFactory(title="Preliminary", status=ReleaseStatus.PROVISIONAL)
        cls.confirmed = ReleaseCalendarPageFactory(title="Acknowledged", status=ReleaseStatus.CONFIRMED)
        cls.cancelled = ReleaseCalendarPageFactory(title="Cancelled", status=ReleaseStatus.CANCELLED)
        cls.published = ReleaseCalendarPageFactory(title="Published", status=ReleaseStatus.PUBLISHED)

        cls.past = ReleaseCalendarPageFactory(
            title="Preliminary, but in the past",
            status=ReleaseStatus.PROVISIONAL,
            release_date=timezone.now() - timedelta(minutes=1),
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_chooser_viewset(self):
        response = self.client.get(self.chooser_url)

        self.assertContains(response, self.provisional.title)
        self.assertContains(response, ReleaseStatus.PROVISIONAL.label)
        self.assertContains(response, self.confirmed.title)
        self.assertContains(response, ReleaseStatus.CONFIRMED.label)
        self.assertNotContains(response, self.cancelled.title)
        self.assertNotContains(response, self.published.title)
        self.assertNotContains(response, self.past.title)

    def test_chooser_search(self):
        """Tests that the chooser search results work as expected."""
        chooser_results_url = reverse(release_calendar_chooser_viewset.get_url_name("choose_results"))
        response = self.client.get(f"{chooser_results_url}?q=preliminary")

        self.assertContains(response, self.provisional.title)
        self.assertContains(response, ReleaseStatus.PROVISIONAL.label)
        self.assertNotContains(response, self.confirmed.title)
        self.assertNotContains(response, ReleaseStatus.CONFIRMED.label)
        self.assertNotContains(response, self.cancelled.title)
        self.assertNotContains(response, self.published.title)
        self.assertNotContains(response, self.past.title)

    def test_chooser_excludes_release_calendar_pages_already_in_an_active_bundle(self):
        bundle = BundleFactory()
        bundle.release_calendar_page = self.provisional
        bundle.save(update_fields=["release_calendar_page"])

        response = self.client.get(self.chooser_url)

        self.assertContains(response, self.confirmed.title)
        self.assertNotContains(response, self.provisional.title)
        self.assertNotContains(response, self.cancelled.title)
        self.assertNotContains(response, self.published.title)
        self.assertNotContains(response, self.past.title)

    def test_chooser__no_results(self):
        bundle = BundleFactory()
        bundle.release_calendar_page = self.provisional
        bundle.save(update_fields=["release_calendar_page"])

        self.confirmed.status = ReleaseStatus.PUBLISHED
        self.confirmed.save_revision().publish()

        response = self.client.get(self.chooser_url)
        self.assertContains(
            response, "There are no release calendar pages that are pending or not in an active bundle already."
        )
