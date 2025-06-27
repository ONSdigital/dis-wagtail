from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

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

    def test_preview_mode_url(self):
        """Tests preview pages with preview mode loads."""
        self.client.force_login(self.user)

        cases = {
            ReleaseStatus.PROVISIONAL: "This release is not yet",
            ReleaseStatus.CONFIRMED: "This release is not yet",
            ReleaseStatus.PUBLISHED: "The publication link",
            ReleaseStatus.CANCELLED: "Cancelled for reasons",
        }

        post_data = nested_form_data(
            {
                "title": self.page.title,
                "slug": self.page.slug,
                "status": self.page.status,
                "release_date": self.page.release_date,
                "summary": rich_text(self.page.summary),
                "notice": rich_text("Cancelled for reasons"),
                "content": streamfield(
                    [
                        (
                            "release_content",
                            {
                                "title": "Publications",
                                "links": streamfield(
                                    [
                                        (
                                            "item",
                                            {"external_url": "https://ons.gov.uk", "title": "The publication link"},
                                        )
                                    ]
                                ),
                            },
                        )
                    ]
                ),
                "changes_to_release_date": streamfield([]),
                "pre_release_access": streamfield([]),
                "related_links": streamfield([]),
                "datasets": streamfield([]),
            }
        )

        preview_url_base = reverse("wagtailadmin_pages:preview_on_edit", args=[self.page.pk])
        for mode, lookup in cases.items():
            with self.subTest(mode=mode):
                preview_url = f"{preview_url_base}?mode={mode}"
                response = self.client.post(preview_url, post_data)
                self.assertEqual(response.status_code, 200)
                self.assertJSONEqual(
                    response.content.decode(),
                    {"is_valid": True, "is_available": True},
                )

                response = self.client.get(preview_url)
                self.assertContains(response, lookup)
