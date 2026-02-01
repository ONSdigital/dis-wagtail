from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.home.models import HomePage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory


class StandardPagesAddViewTests(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permission_denied_message = "Sorry, you do not have permission to access this area."
        cls.index_page = IndexPageFactory()

    def setUp(self):
        self.login()

    def test_index_page_cannot_have_index_page_child(self):
        """Home -> Index Page -> Index Page should be forbidden."""
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "indexpage", self.index_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.permission_denied_message)

    def test_information_page_cannot_have_information_page_child(self):
        """Home -> Index Page -> Information Page -> Information Page should be forbidden."""
        information_page = InformationPageFactory(parent=self.index_page)

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", information_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.permission_denied_message)

    def test_index_page_can_be_added_under_home(self):
        """Home -> Index Page should be allowed."""
        home_page = HomePage.objects.first()

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "indexpage", home_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)

    def test_information_page_can_be_added_under_home(self):
        """Home -> Information Page should be allowed."""
        home_page = HomePage.objects.first()

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", home_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)

    def test_information_page_can_be_added_under_index_page(self):
        """Home -> Index Page -> Information Page should be allowed."""
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", self.index_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)
