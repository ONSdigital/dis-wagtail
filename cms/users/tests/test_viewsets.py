from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.users.tests.factories import UserFactory
from cms.users.viewsets import user_chooser_viewset


class TestUserChooserViewSet(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.chooser_url = user_chooser_viewset.widget_class().get_chooser_modal_url()
        cls.chooser_results_url = reverse(user_chooser_viewset.get_url_name("choose_results"))

        cls.user_without_name = UserFactory(username="noname", first_name="", last_name="", is_active=False)
        cls.user_with_first_name = UserFactory(username="first_name_user", first_name="Data", last_name="")
        cls.user_with_last_name = UserFactory(username="last_name_user", first_name="", last_name="La Forge ")
        cls.user_with_full_name = UserFactory(
            username="full_name_user", first_name="Jean-Luc", last_name="Picard", is_superuser=True
        )

    def setUp(self):
        self.login(user=self.user_with_full_name)

    def test_chooser_viewset(self):
        response = self.client.get(self.chooser_url)

        self.assertContains(response, self.user_without_name.username, 2)  # Name and username
        self.assertContains(response, self.user_with_first_name.username)
        self.assertContains(response, self.user_with_last_name.username)
        self.assertContains(response, self.user_with_full_name.username)

        self.assertContains(response, "Data")
        self.assertContains(response, "La Forge")
        self.assertContains(response, "Jean-Luc Picard")

        self.assertContains(response, "Active", 3)
        self.assertContains(response, "Inactive", 1)

    def test_chooser_search(self):
        """Tests that the chooser search results work as expected."""
        response = self.client.get(f"{self.chooser_results_url}?q={self.user_with_first_name.first_name}")
        self.assertContains(response, self.user_with_first_name.username)
        self.assertNotContains(response, self.user_without_name.username)
        self.assertNotContains(response, self.user_with_last_name.username)
        self.assertNotContains(response, self.user_with_full_name.username)

        response = self.client.get(f"{self.chooser_results_url}?q={self.user_with_full_name.email}")
        self.assertContains(response, self.user_with_full_name.username)
        self.assertNotContains(response, self.user_without_name.username)
        self.assertNotContains(response, self.user_with_first_name.username)
        self.assertNotContains(response, self.user_with_last_name.username)

        response = self.client.get(f"{self.chooser_results_url}?q={self.user_with_last_name.last_name}")
        self.assertContains(response, self.user_with_last_name.username)
        self.assertNotContains(response, self.user_without_name.username)
        self.assertNotContains(response, self.user_with_first_name.username)
        self.assertNotContains(response, self.user_with_full_name.username)
