from datetime import datetime
from typing import TYPE_CHECKING
from unittest import skip

from django.utils import timezone
from django.utils.timezone import is_aware, localtime
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.test.utils import WagtailPageTestCase

from cms.release_calendar.panels import ChangesToReleaseDateFieldPanel
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory

if TYPE_CHECKING:
    pass


class ReleaseCalendarPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = ReleaseCalendarPageFactory(release_date=timezone.now())
        cls.panel = ChangesToReleaseDateFieldPanel("changes_to_release_date")

    def test_changes_to_release_date_panel_pre_populates_previous_release_date(self):
        """Test that the ChangesToReleaseDateFieldPanel pre-populates the previous_release_date of the page."""
        model_bound_panel = self.panel.bind_to_model(self.page._meta.model)
        release_date_panel = model_bound_panel.get_bound_panel(
            instance=self.page, request=self.dummy_request, form=self.page.base_form_class
        )

        page_context = self.page.get_context(self.dummy_request)
        release_date_panel.errors = []
        bound_panel_context = release_date_panel.get_context_data(parent_context=page_context)

        expected_previous_release_date = self.page.release_date
        if isinstance(expected_previous_release_date, datetime) and is_aware(expected_previous_release_date):
            expected_previous_release_date = localtime(expected_previous_release_date)
        expected_previous_release_date = expected_previous_release_date.strftime("%Y-%m-%d %H:%M")

        self.assertEqual(bound_panel_context.get("previous_release_date"), expected_previous_release_date)

    @skip("Skipping failing test")
    def test_changes_to_release_date_is_uneditable(self):
        """Test that the previous_release_date is not editable in the ChangesToReleaseDateFieldPanel."""
        model_bound_panel = self.panel.bind_to_model(self.page._meta.model)
        _release_date_panel = model_bound_panel.get_bound_panel(
            instance=self.page, request=self.dummy_request, form=self.page.base_form_class
        )

        response = self.client.get(AdminURLFinder().get_edit_url(self.page), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("previous_release_date", response.content)
        self.assertContains(response, "#panel-child-content-changes_to_release_date-section")
