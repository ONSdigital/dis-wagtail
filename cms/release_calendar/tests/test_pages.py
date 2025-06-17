from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils import WagtailPageTestCase

from cms.core.custom_date_format import ons_default_datetime
from cms.release_calendar.enums import ReleaseStatus
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


class ReleaseCalendarPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_superuser("admin")
        cls.page = ReleaseCalendarPageFactory()

    def test_date_placeholder(self):
        """Test that the date input field displays date placeholder."""
        self.client.force_login(self.user)

        parent_page = self.page.get_parent()
        add_sibling_url = reverse("wagtailadmin_pages:add_subpage", args=[parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)

        content = response.content.decode(encoding="utf-8")

        datetime_placeholder = "YYYY-MM-DD HH:MM"

        self.assertInHTML(
            (
                '<input type="text" name="next_release_date" autocomplete="off" '
                f'placeholder="{datetime_placeholder}" id="id_next_release_date">'
            ),
            content,
        )

    def test_default_date_on_release_date(self):
        """Test release date shows a default datetime from ons_default_datetime."""
        self.client.force_login(self.user)

        parent_page = self.page.get_parent()
        add_sibling_url = reverse("wagtailadmin_pages:add_subpage", args=[parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)

        content = response.content.decode(encoding="utf-8")
        datetime_placeholder = "YYYY-MM-DD HH:MM"

        default_datetime = ons_default_datetime().strftime("%Y-%m-%d %H:%M")

        self.assertInHTML(
            (
                f'<input type="text" name="release_date" value="{default_datetime}" autocomplete="off" '
                f'placeholder="{datetime_placeholder}" required="" id="id_release_date">'
            ),
            content,
        )

    def test_changes_to_release_dates_provisional_page(self):
        """Test changes to release date cannot be displayed on a published provisional page."""
        self.page.status = ReleaseStatus.PROVISIONAL
        date_change_log = {
            "previous_date": timezone.now(),
            "reason_for_change": "Reason",
        }
        self.page.changes_to_release_date = [("date_change_log", date_change_log)]
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        self.assertNotContains(response, "Changes to this release date")
        self.assertNotContains(response, "Previous date")
        self.assertNotContains(response, "Reason for change")
        self.assertNotContains(response, "Reason")

    def test_changes_to_release_date_non_provisional_page(self):
        """Test a change to release date is visible for published non-provisional status."""
        cases = [ReleaseStatus.CONFIRMED, ReleaseStatus.PUBLISHED, ReleaseStatus.CANCELLED]
        for case in cases:
            self.page.status = case
            date_change_log = {
                "previous_date": timezone.now(),
                "reason_for_change": "Reason",
            }
            self.page.changes_to_release_date = [("date_change_log", date_change_log)]
            self.page.save_revision().publish()

            response = self.client.get(self.page.url)
            self.assertContains(response, "Changes to this release date")
            self.assertContains(response, "Previous date")
            self.assertContains(response, "Reason for change")
            self.assertContains(response, "Reason")

    def test_preview_mode_url(self):
        cases = ["PROVISIONAL", "CANCELLED", "PUBLISHED", "CONFIRMED"]

        for case in cases:
            preview_url = f"/admin/pages/{self.page.id}/edit/preview/?mode={case}"
            response = self.client.get(preview_url, follow=True)
            self.assertEqual(response.status_code, 200)
