from django.conf import settings
from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.standard_pages.models import CookiesPage
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

    def test_get_welsh_cookies_page(self):
        response = self.client.get("/cy/cookies")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cwcis ar ONS.GOV.UK")
        self.assertContains(response, "Gosodiadau cwcis")

    def test_cookies_page_exists_for_all_supported_language(self):
        language_codes = [lang[0] for lang in settings.LANGUAGES]

        # The english cookies page should be the original
        english_cookies_page = CookiesPage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        language_codes.remove(settings.LANGUAGE_CODE)

        for language_code in language_codes:
            with self.subTest(language_code=language_code):
                # Check that a cookies page exists for each other supported language, with matching translation key
                cookies_page = CookiesPage.objects.get(locale__language_code=language_code)
                self.assertEqual(cookies_page.translation_key, english_cookies_page.translation_key)

    def test_view_cookies_link_is_present(self):
        response = self.client.get("/")
        self.assertContains(response, 'href="/cookies"')

    def test_view_cookies_link_is_localised(self):
        response = self.client.get("/cy")
        self.assertContains(response, 'href="/cy/cookies"')
