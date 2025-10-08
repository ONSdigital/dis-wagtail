from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data

from cms.standard_pages.models import CookiesPage


class StandardPagesHooksTestCase(WagtailTestUtils, TestCase):
    def test_user_cannot_edit_cookies_page(self):
        self.login()
        data = nested_form_data(
            {
                "title": "New title",
                "slug": "new-slug",
            }
        )
        cookies_page = CookiesPage.objects.first()
        original_page_title = cookies_page.title

        response = self.client.post(reverse("wagtailadmin_pages:edit", args=(cookies_page.id,)), data, follow=True)

        self.assertEqual(response.status_code, 200)
        # Editing a cookies page should be forbidden
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

        cookies_page.refresh_from_db()
        self.assertEqual(cookies_page.draft_title, original_page_title, "Expected draft title to be unchanged")
