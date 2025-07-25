from typing import TYPE_CHECKING

from django.utils import timezone
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils import WagtailPageTestCase

from cms.release_calendar.panels import ChangesToReleaseDateFieldPanel
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory

if TYPE_CHECKING:
    pass


class ReleaseCalendarPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = ReleaseCalendarPageFactory(release_date=timezone.now())
        cls.request = get_dummy_request()

    def test_changes_to_release_date_panel_pre_populates_previous_release_date(self):
        panel = ChangesToReleaseDateFieldPanel("changes_to_release_date")

        # Create a clone(!) of this panel definition with a model attribute pointing to the linked Page class.
        bound_change_log_panel = panel.bind_to_model(self.page._meta.model)
        bound_panel = bound_change_log_panel.get_bound_panel(instance=self.page, request=self.request)

        # Pass the page context to the panel
        self.assertIsNotNone(bound_panel)
        page_context = self.page.get_context(self.request)
        bound_panel_context = bound_panel.get_context_data(parent_context=page_context)  # this line fails

        # Assert that the previous release date within the Panel is set to the current release date
        self.assertEqual(bound_panel_context.get("previous_release_date"), self.page.release_date)
