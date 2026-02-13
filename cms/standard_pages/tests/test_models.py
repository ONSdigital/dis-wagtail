from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils import WagtailTestUtils

from cms.core.permission_testers import BasePagePermissionTester
from cms.home.models import HomePage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from cms.users.tests.factories import UserFactory


class IndexPageTestCase(WagtailTestUtils, TestCase):
    """Test IndexPage model properties and methods."""

    @classmethod
    def setUpTestData(cls):
        cls.index_page = IndexPageFactory(
            title="Test Index Page",
            summary="This is an example",
        )

        cls.page_url = cls.index_page.get_url(request=get_dummy_request())

    def setUp(self):
        self.dummy_request = get_dummy_request()

    def test_permission_tester_inherits_from_basepagepermissiontester(self):
        self.assertIsInstance(self.index_page.permissions_for_user(UserFactory()), BasePagePermissionTester)

    def test_no_featured_items_displayed_when_no_children_and_no_custom_featured_items_selected(self):
        """Test that the Featured Items block isn't displayed when the Index Page has no child pages
        and no custom Featured Items are specified.
        """
        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "ons-document-list")

    def test_children_displayed_as_featured_items_when_no_custom_featured_items_selected(self):
        """Test that the children pages of the Index Page are displayed
        when no custom Featured Items are specified.
        """
        child_page = InformationPageFactory(parent=self.index_page)

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, child_page.title)
        self.assertContains(response, child_page.get_url(request=self.dummy_request))
        self.assertContains(response, child_page.summary)

    def test_children_displayed_as_featured_items_with_listing_info_when_no_custom_featured_items_selected(self):
        """Test that the children pages of the Index page are displayed
        when no custom Featured Items are specified
        and that the child pages is displayed with its listing title and listing summary.
        """
        child_page_listing_info = InformationPageFactory(
            title="Title of the child page",
            summary="Summary of the child page",
            parent=self.index_page,
            listing_title="Listing title of the child page",
            listing_summary="Listing summary of the child page",
        )

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, child_page_listing_info.listing_title)
        self.assertContains(response, child_page_listing_info.get_url(request=self.dummy_request))
        self.assertContains(response, child_page_listing_info.listing_summary)

        self.assertNotContains(response, child_page_listing_info.title)
        self.assertNotContains(response, child_page_listing_info.summary)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_load_in_external_env(self):
        """Test the page loads in external env."""
        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)


class InformationPageTestCase(WagtailTestUtils, TestCase):
    """Test InformationPage model properties and methods."""

    @classmethod
    def setUpTestData(cls):
        cls.page = InformationPageFactory(title="Test Information Page")

        cls.page_url = cls.page.get_url(request=get_dummy_request())

    def test_permission_tester_inherits_from_basepagepermissiontester(self):
        self.assertIsInstance(self.page.permissions_for_user(UserFactory()), BasePagePermissionTester)

    def test_page_loads(self):
        """Test that the Information Page loads correctly."""
        response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.content)


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

    def test_information_page_cannot_be_added_under_home(self):
        """Home -> Information Page should be forbidden."""
        home_page = HomePage.objects.first()

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", home_page.pk)),
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

    def test_information_page_can_be_added_under_index_page(self):
        """Home -> Index Page -> Information Page should be allowed."""
        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=("standard_pages", "informationpage", self.index_page.pk)),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.permission_denied_message)
