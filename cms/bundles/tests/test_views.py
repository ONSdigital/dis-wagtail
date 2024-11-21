from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.analysis.tests.factories import AnalysisPageFactory
from cms.bundles.admin_forms import AddToBundleForm
from cms.bundles.models import Bundle
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import grant_all_bundle_permissions, grant_all_page_permissions, make_bundle_viewer
from cms.users.tests.factories import GroupFactory, UserFactory


class AddToBundleViewTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.publishing_group = GroupFactory(name="Publishing Officers", access_admin=True)
        grant_all_bundle_permissions(cls.publishing_group)
        grant_all_page_permissions(cls.publishing_group)
        cls.publishing_officer = UserFactory(username="publishing_officer")
        cls.publishing_officer.groups.add(cls.publishing_group)

        cls.bundle_viewer = UserFactory(username="bundle.viewer", access_admin=True)
        make_bundle_viewer(cls.bundle_viewer)

    def setUp(self):
        self.bundle = BundleFactory(name="First Bundle", created_by=self.publishing_officer)
        self.analysis_page = AnalysisPageFactory(title="November 2024", parent__title="PSF")
        self.add_url = reverse("bundles:add_to_bundle", args=[self.analysis_page.id])
        self.bundle_index_url = reverse("bundle:index")

        self.client.force_login(self.publishing_officer)

    def test_dispatch__happy_path(self):
        """Dispatch should not complain about anything."""
        response = self.client.get(f"{self.add_url}?next={self.bundle_index_url}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "bundles/wagtailadmin/add_to_bundle.html")

        self.assertEqual(response.context["page_to_add"], self.analysis_page)
        self.assertEqual(response.context["next"], self.bundle_index_url)
        self.assertIsInstance(response.context["form"], AddToBundleForm)
        self.assertEqual(response.context["form"].page_to_add, self.analysis_page)

    def test_dispatch__returns_404_for_wrong_page_id(self):
        """The page must exist in the first place."""
        url = reverse("bundles:add_to_bundle", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_dispatch__returns_404_for_non_bundleable_page(self):
        """Only pages with BundledPageMixin can be added to a bundle."""
        url = reverse("bundles:add_to_bundle", args=[self.analysis_page.get_parent().id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_dispatch__returns_404_if_user_doesnt_have_access(self):
        """Only users that can edit see the page are allowed to add it to the bundle."""
        self.client.force_login(self.bundle_viewer)
        response = self.client.get(self.add_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_dispatch__doesnt_allow_adding_page_already_in_active_bundle(self):
        """Tests that we get redirected away with a corresponding message when the page we try to add to the bundle is
        already in a different bundle.
        """
        another_bundle = BundleFactory(name="Another Bundle")
        BundlePageFactory(parent=another_bundle, page=self.analysis_page)
        response = self.client.get(self.add_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "PSF: November 2024 is already in a bundle")

    def test_post__successful(self):
        """Checks that on successful post, the page is added to the bundle and
        we get redirected to the valid next URL.
        """
        response = self.client.post(
            f"{self.add_url}?next={self.bundle_index_url}", data={"bundle": self.bundle.id}, follow=True
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Page &#x27;PSF: November 2024&#x27; added to bundle &#x27;First Bundle&#x27;")
        self.assertQuerySetEqual(self.analysis_page.bundles, Bundle.objects.all())
