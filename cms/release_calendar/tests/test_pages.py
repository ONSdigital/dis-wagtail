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

    def test_default_date(self):
        """Test release date shows a default datetime from ons_default_datetime."""
        self.client.force_login(self.user)

        parent_page = self.page.get_parent()
        add_sibling_url = reverse("wagtailadmin_pages:add_subpage", args=[parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)

        content = response.content.decode(encoding="utf-8")

        default_datetime = ons_default_datetime().strftime("%Y-%m-%d %H:%M")

        self.assertInHTML(
            (
                f'<input type="text" name="release_date" value="{default_datetime}" autocomplete="off" '
                'required="" id="id_release_date">'
            ),
            content,
        )

    def test_unpublished_changes_to_release_dates(self):
        """Test changes to release date can not be published to an unpublished release page."""
        # Add date_change_log to an un published page
        date_change_log = {
            "previous_date": timezone.now(),
            "reason_for_change": "Reason",
        }
        self.page.changes_to_release_date = [("date_change_log", date_change_log)]
        self.page.save_revision().publish()
        response = self.client.get(self.page.url)

        # check change log not added
        self.assertNotContains(response, "Reason")

    def test_published_changes_to_release_date(self):
        """Test a change to release date can be published for a published page."""
        # First publish
        self.page.status = ReleaseStatus.PUBLISHED
        self.page.save_revision().publish()

        # Add date change log
        date_change_log = {
            "previous_date": timezone.now(),
            "reason_for_change": "Reason",
            "frozen": True,
            "version_id": 1,
        }
        self.page.changes_to_release_date = [("date_change_log", date_change_log)]
        # Publish with change log
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        # contains change log
        self.assertContains(response, "Reason")

    def test_multiple_date_change_logs(self):
        """Test for multiple changes to release date change."""
        # First publish
        self.page.status = ReleaseStatus.PUBLISHED
        self.page.save_revision().publish()
        logs = self.page.changes_to_release_date

        # Add date change log
        date_change_log = {
            "previous_date": "2025-05-01",
            "reason_for_change": "Reason 1",
            "frozen": True,
            "version_id": 1,
        }
        logs.append(("date_change_log", date_change_log))

        # Second Publish with change log
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        # contains this...
        self.assertContains(response, "Reason 1")

        # Add next date change log
        date_change_log_2 = {
            "previous_date": "2025-05-02",
            "reason_for_change": "Reason 2",
            "frozen": True,
            "version_id": 2,
        }
        logs.append(("date_change_log", date_change_log_2))

        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        self.assertContains(response, "Reason 1")
        self.assertContains(response, "Reason 2")

        # Add next date change log
        date_change_log_3 = {
            "previous_date": "2025-05-03",
            "reason_for_change": "Reason 3",
            "frozen": True,
            "version_id": 3,
        }
        logs.append(("date_change_log", date_change_log_3))
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        self.assertContains(response, "Reason 1")
        self.assertContains(response, "Reason 2")
        self.assertContains(response, "Reason 3")

    def test_preview_modes(self):
        """Test preview modes."""
        cases = ["PROVISIONAL", "CONFIRMED", "CANCELLED", "PUBLISHED"]
        post_data = {
            "title": self.page.title,
            "summary": self.page.summary,
            "release_date": self.page.release_date,
        }
        for case in cases:
            self.assertPageIsPreviewable(
                self.page,
                mode=case,
                post_data=post_data,
            )
