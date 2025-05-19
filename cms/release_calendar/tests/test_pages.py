from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.core.custom_date_format import ons_default_datetime
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
