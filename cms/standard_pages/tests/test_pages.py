from unittest import expectedFailure

from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.standard_pages.tests.factories import InformationPageFactory


class DatePlaceholderTestCase(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory()
        cls.user = cls.create_superuser("admin")

    def test_date_placeholder(self):
        """Test that the date input field displays date placeholder."""
        self.client.force_login(self.user)

        parent_page = self.page.get_parent()

        add_sibling_url = reverse("wagtailadmin_pages:add", args=["standard_pages", "informationpage", parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)

        content = response.content.decode(encoding="utf-8")

        date_placeholder = "YYYY-MM-DD"

        self.assertInHTML(
            (
                '<input type="text" name="last_updated" autocomplete="off"'
                f'placeholder="{date_placeholder}" id="id_last_updated">'
            ),
            content,
        )


class CookiesPageTest(WagtailPageTestCase):
    def test_get_cookies_page(self):
        response = self.client.get("/cookies")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cookies on ONS.GOV.UK")
        self.assertContains(response, "Cookie settings")

    # TODO: Expected to fail until the welsh alias is created under the welsh homepage in the migration
    @expectedFailure
    def test_get_welsh_cookies_page(self):
        response = self.client.get("/cy/cookies")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cwcis ar ONS.GOV.UK")
        self.assertContains(response, "Gosodiadau cwcis")
