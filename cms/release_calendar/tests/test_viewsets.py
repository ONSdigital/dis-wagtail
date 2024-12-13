from django.test import TestCase
from wagtail.test.utils import WagtailTestUtils

from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.release_calendar.viewsets import release_calendar_chooser_viewset


class TestFutureReleaseCalendarChooserViewSet(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.chooser_url = release_calendar_chooser_viewset.widget_class().get_chooser_modal_url()

        cls.provisional = ReleaseCalendarPageFactory(title="Preliminary", status=ReleaseStatus.PROVISIONAL)
        cls.confirmed = ReleaseCalendarPageFactory(title="Acknowledged", status=ReleaseStatus.CONFIRMED)
        cls.cancelled = ReleaseCalendarPageFactory(title="Cancelled", status=ReleaseStatus.CANCELLED)
        cls.published = ReleaseCalendarPageFactory(title="Published", status=ReleaseStatus.PUBLISHED)

    def setUp(self):
        self.login()

    def test_chooser_viewset(self):
        response = self.client.get(self.chooser_url)

        self.assertContains(response, self.provisional.title)
        self.assertContains(response, ReleaseStatus.PROVISIONAL.label)
        self.assertContains(response, self.confirmed.title)
        self.assertContains(response, ReleaseStatus.CONFIRMED.label)
        self.assertNotContains(response, self.cancelled.title)
        self.assertNotContains(response, self.published.title)
