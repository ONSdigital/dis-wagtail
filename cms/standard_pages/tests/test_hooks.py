from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data

from cms.home.models import HomePage
from cms.standard_pages.models import CookiesPage


class StandardPagesHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permission_denied_message = "Sorry, you do not have permission to access this area."

    def setUp(self):
        self.login()

    def test_user_cannot_edit_cookies_page(self):
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
        self.assertContains(response, self.permission_denied_message)
        cookies_page.refresh_from_db()
        self.assertEqual(cookies_page.draft_title, original_page_title, "Expected draft title to be unchanged")

    def test_user_cannot_publish_cookies_page(self):
        data = nested_form_data(
            {
                "title": "New title",
                "slug": "new-slug",
                "action-publish": "publish",
            }
        )
        cookies_page = CookiesPage.objects.first()
        original_page_title = cookies_page.title

        response = self.client.post(reverse("wagtailadmin_pages:edit", args=(cookies_page.id,)), data, follow=True)

        self.assertEqual(response.status_code, 200)

        # Editing a cookies page should be forbidden
        self.assertContains(response, self.permission_denied_message)
        cookies_page.refresh_from_db()
        self.assertEqual(cookies_page.title, original_page_title, "Expected title to be unchanged")
        self.assertEqual(cookies_page.draft_title, original_page_title, "Expected draft title to be unchanged")

    def test_user_cannot_delete_cookies_page_post(self):
        data = nested_form_data({})
        cookies_page = CookiesPage.objects.first()

        response = self.client.post(reverse("wagtailadmin_pages:delete", args=(cookies_page.id,)), data, follow=True)

        self.assertEqual(response.status_code, 200)

        # Editing a cookies page should be forbidden
        self.assertContains(response, self.permission_denied_message)

        cookies_page.refresh_from_db()

    def test_user_cannot_delete_cookies_page_get(self):
        cookies_page = CookiesPage.objects.first()

        response = self.client.get(reverse("wagtailadmin_pages:delete", args=(cookies_page.id,)), follow=True)

        self.assertEqual(response.status_code, 200)

        # Editing a cookies page should be forbidden
        self.assertContains(response, self.permission_denied_message)

    def test_user_cannot_create_cookies_page(self):
        # Cookies pages are restricted to one per parent, so create a new home page
        home_page_pk = HomePage.objects.first().pk
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "cookiespage", home_page_pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        # Creating a cookies page should be forbidden
        self.assertContains(response, self.permission_denied_message)

    def test_user_cannot_convert_alias_of_cookies_page(self):
        # The Welsh cookies page is an alias of the English cookies page
        cookies_page = CookiesPage.objects.get(locale__language_code="en-gb")
        alias_cookies_page = CookiesPage.objects.get(locale__language_code="cy")

        response = self.client.post(
            reverse("wagtailadmin_pages:convert_alias", args=(alias_cookies_page.id,)), follow=True
        )

        self.assertEqual(response.status_code, 200)

        # Converting an alias of a cookies page should be forbidden
        self.assertContains(response, self.permission_denied_message)

        alias_cookies_page.refresh_from_db()
        self.assertEqual(alias_cookies_page.alias_of.pk, cookies_page.pk, "Expected alias_of to be unchanged")

    def test_user_cannot_unpublish_cookies_page(self):
        cookies_page = CookiesPage.objects.first()

        response = self.client.post(reverse("wagtailadmin_pages:unpublish", args=(cookies_page.id,)), follow=True)

        self.assertEqual(response.status_code, 200)

        # Unpublishing a cookies page should be forbidden
        self.assertContains(response, self.permission_denied_message)

        cookies_page.refresh_from_db()
        self.assertTrue(cookies_page.live, "Expected cookies page to remain live")

    def test_user_cannot_move_cookies_page(self):
        welsh_home_page = HomePage.objects.get(locale__language_code="cy")
        cookies_page = CookiesPage.objects.get(locale__language_code="en-gb")

        # Delete the existing Welsh cookies page to allow the move to be attempted
        welsh_cookies_page = CookiesPage.objects.get(locale__language_code="cy")
        welsh_cookies_page.delete()

        response = self.client.post(
            f"/admin/pages/{cookies_page.pk}/move/",
            data={"new_parent_page": welsh_home_page.pk, "action-move": "move"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        # Moving a cookies page should be forbidden
        self.assertContains(response, self.permission_denied_message)

        cookies_page.refresh_from_db()
        self.assertTrue(cookies_page.get_parent().pk != welsh_home_page.pk, "Expected parent page to be unchanged")

    def test_user_cannot_see_cookies_page_in_explorer(self):
        cookies_page = CookiesPage.objects.first()

        # "Cookies page" can still appear in the explorer page search filters, so use a unique title for checking
        # that the page itself is not visible.
        cookies_page.title = "A temporary unique title for testing"
        cookies_page.save_revision().publish()

        response = self.client.get(reverse("wagtailadmin_explore", args=(cookies_page.get_parent().pk,)), follow=True)

        self.assertEqual(response.status_code, 200)

        # The cookies page should not be visible in the explorer
        self.assertNotContains(response, cookies_page.title)
        self.assertNotContains(response, f"/{cookies_page.slug}")
