from http import HTTPStatus
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle
from cms.bundles.tests.factories import BundleFactory
from cms.bundles.tests.utils import grant_all_bundle_permissions, make_bundle_viewer, mark_page_as_ready_to_publish
from cms.bundles.viewsets import bundle_chooser_viewset
from cms.release_calendar.viewsets import FutureReleaseCalendarChooserWidget
from cms.users.tests.factories import GroupFactory, UserFactory


class BundleViewSetTestCase(WagtailTestUtils, TestCase):
    """Test Bundle viewset functionality."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.publishing_group = GroupFactory(name="Publishing Officers", access_admin=True)
        grant_all_bundle_permissions(cls.publishing_group)
        cls.publishing_officer = UserFactory(username="publishing_officer")
        cls.publishing_officer.groups.add(cls.publishing_group)

        cls.bundle_viewer = UserFactory(username="bundle.viewer", access_admin=True)
        make_bundle_viewer(cls.bundle_viewer)

        # a regular generic_user that can only access the Wagtail admin
        cls.generic_user = UserFactory(username="generic.generic_user", access_admin=True)

        cls.bundle_index_url = reverse("bundle:index")
        cls.bundle_add_url = reverse("bundle:add")

        cls.released_bundle = BundleFactory(released=True, name="Release Bundle")
        cls.released_bundle_edit_url = reverse("bundle:edit", args=[cls.released_bundle.id])

        cls.approved_bundle = BundleFactory(approved=True, name="Approve Bundle")
        cls.approved_bundle_edit_url = reverse("bundle:edit", args=[cls.approved_bundle.id])

    def setUp(self):
        self.bundle = BundleFactory(name="Original bundle", created_by=self.publishing_officer)
        self.statistical_article_page = StatisticalArticlePageFactory(title="PSF")

        self.edit_url = reverse("bundle:edit", args=[self.bundle.id])

        self.client.force_login(self.publishing_officer)

    def test_bundle_index__unhappy_paths(self):
        """Test bundle list view permissions."""
        self.client.logout()
        response = self.client.get(self.bundle_index_url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, f"/admin/login/?next={self.bundle_index_url}")

        self.client.force_login(self.generic_user)
        response = self.client.get(self.bundle_index_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_bundle_index__happy_path(self):
        """Users with bundle permissions can see the index."""
        for user in [self.bundle_viewer, self.publishing_officer, self.superuser]:
            with self.subTest(user=user):
                self.client.force_login(user)
                response = self.client.get(self.bundle_index_url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_bundle_add_view(self):
        """Test bundle creation."""
        response = self.client.post(
            self.bundle_add_url,
            nested_form_data(
                {
                    "name": "A New Bundle",
                    "status": BundleStatus.PENDING,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                }
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Bundle.objects.filter(name="A New Bundle").exists())

    def test_bundle_add_view__with_page_already_in_a_bundle(self):
        """Test bundle creation."""
        response = self.client.post(
            self.bundle_add_url,
            nested_form_data(
                {
                    "name": "A New Bundle",
                    "status": BundleStatus.PENDING,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                }
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Bundle.objects.filter(name="A New Bundle").exists())

    def test_bundle_add_view__without_permissions(self):
        """Checks that users without permission cannot access the add bundle page."""
        for user in [self.generic_user, self.bundle_viewer]:
            with self.subTest(user=user):
                self.client.force_login(user)
                response = self.client.get(self.bundle_add_url, follow=True)
                self.assertRedirects(response, "/admin/")
                self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_bundle_edit_view(self):
        """Test bundle editing."""
        response = self.client.post(
            self.edit_url,
            nested_form_data(
                {
                    "name": "Updated Bundle",
                    "status": self.bundle.status,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                }
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.name, "Updated Bundle")

    def test_bundle_edit_view__redirects_to_index_for_released_bundles(self):
        """Released bundles should no longer be editable."""
        response = self.client.get(self.released_bundle_edit_url)
        self.assertRedirects(response, self.bundle_index_url)

    def test_bundle_edit_view__updates_approved_fields_on_save_and_approve(self):
        """Checks the fields are populated if the user clicks the 'Save and approve' button."""
        self.client.force_login(self.superuser)
        self.client.post(
            self.edit_url,
            nested_form_data(
                {
                    "name": "Updated Bundle",
                    "status": self.bundle.status,  # correct. "save and approve" should update the status directly
                    "bundled_pages": inline_formset([]),
                    "teams": inline_formset([]),
                    "action-save-and-approve": "save-and-approve",
                }
            ),
        )
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.APPROVED)
        self.assertIsNotNone(self.bundle.approved_at)
        self.assertEqual(self.bundle.approved_by, self.superuser)

    @mock.patch("cms.bundles.viewsets.notify_slack_of_status_change")
    def test_bundle_approval__happy_path(self, mock_notify_slack):
        """Test bundle approval workflow."""
        self.client.force_login(self.superuser)

        mark_page_as_ready_to_publish(self.statistical_article_page, self.superuser)

        response = self.client.post(
            self.edit_url,
            nested_form_data(
                {
                    "name": self.bundle.name,
                    "status": BundleStatus.APPROVED,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                }
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, BundleStatus.APPROVED)
        self.assertIsNotNone(self.bundle.approved_at)
        self.assertEqual(self.bundle.approved_by, self.superuser)

        self.assertTrue(mock_notify_slack.called)

    @mock.patch("cms.bundles.viewsets.notify_slack_of_status_change")
    def test_bundle_approval__cannot__self_approve(self, mock_notify_slack):
        """Test bundle approval workflow."""
        self.client.force_login(self.publishing_officer)
        original_status = self.bundle.status

        mark_page_as_ready_to_publish(self.statistical_article_page, self.publishing_officer)

        response = self.client.post(
            self.edit_url,
            nested_form_data(
                {
                    "name": self.bundle.name,
                    "status": BundleStatus.APPROVED,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                }
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["request"].path, self.edit_url)
        self.assertContains(response, "You cannot self-approve your own bundle!")

        form = response.context["form"]
        self.assertIsNone(form.cleaned_data["approved_by"])
        self.assertIsNone(form.cleaned_data["approved_at"])
        self.assertIsNone(form.fields["approved_by"].initial)
        self.assertIsNone(form.fields["approved_at"].initial)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, original_status)
        self.assertIsNone(self.bundle.approved_at)
        self.assertIsNone(self.bundle.approved_by)

        self.assertFalse(mock_notify_slack.called)

    @mock.patch("cms.bundles.viewsets.notify_slack_of_status_change")
    def test_bundle_approval__cannot__approve_if_pages_are_not_ready_to_publish(self, mock_notify_slack):
        """Test bundle approval workflow."""
        self.client.force_login(self.publishing_officer)
        original_status = self.bundle.status

        response = self.client.post(
            self.edit_url,
            nested_form_data(
                {
                    "name": self.bundle.name,
                    "status": BundleStatus.APPROVED,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                }
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["request"].path, self.edit_url)
        self.assertContains(response, "Cannot approve the bundle with 1 page not ready to be published.")

        form = response.context["form"]
        self.assertIsNone(form.cleaned_data["approved_by"])
        self.assertIsNone(form.cleaned_data["approved_at"])
        self.assertIsNone(form.fields["approved_by"].initial)
        self.assertIsNone(form.fields["approved_at"].initial)

        self.assertFormSetError(form.formsets["bundled_pages"], 0, "page", "This page is not ready to be published")

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, original_status)
        self.assertIsNone(self.bundle.approved_at)
        self.assertIsNone(self.bundle.approved_by)

        self.assertFalse(mock_notify_slack.called)

    def test_index_view(self):
        """Checks the content of the index page."""
        response = self.client.get(self.bundle_index_url)
        self.assertContains(response, self.edit_url)
        self.assertContains(response, self.approved_bundle_edit_url)
        self.assertNotContains(response, self.released_bundle_edit_url)

        self.assertContains(response, "Pending", 2)  # status + status filter
        self.assertContains(response, "Released", 2)  # status + status filter
        self.assertContains(response, "Approved", 5)  # status + status filter, approved at/by

        self.assertContains(response, self.released_bundle.name)
        self.assertContains(response, self.approved_bundle.name)

    def test_index_view_search(self):
        response = self.client.get(f"{self.bundle_index_url}?q=release")
        self.assertContains(response, self.released_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)

    def test_bundle_form_uses_release_calendar_chooser_widget(self):
        form_class = get_edit_handler(Bundle).get_form_class()
        form = form_class(instance=self.bundle)

        self.assertIn("release_calendar_page", form.fields)
        chooser_widget = form.fields["release_calendar_page"].widget
        self.assertIsInstance(chooser_widget, FutureReleaseCalendarChooserWidget)

        self.assertEqual(
            chooser_widget.get_chooser_modal_url(),
            # the admin path + the chooser namespace
            reverse("wagtailadmin_home") + "release_calendar_chooser/",
        )

        response = self.client.get(
            self.bundle_add_url,
        )
        self.assertContains(response, "Choose Release Calendar page")

    def test_chooser_viewset(self):
        pending_bundle = BundleFactory(name="Pending")
        response = self.client.get(bundle_chooser_viewset.widget_class().get_chooser_modal_url())

        self.assertContains(response, pending_bundle.name)
        self.assertNotContains(response, self.released_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)

    def test_chooser_search(self):
        pending_bundle = BundleFactory(name="Pending")
        chooser_results_url = reverse(bundle_chooser_viewset.get_url_name("choose_results"))

        response = self.client.get(f"{chooser_results_url}?q=approve")

        self.assertNotContains(response, pending_bundle.name)
        self.assertNotContains(response, self.released_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)

        response = self.client.get(f"{chooser_results_url}?q=pending")

        self.assertContains(response, pending_bundle.name)
        self.assertNotContains(response, self.released_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)
