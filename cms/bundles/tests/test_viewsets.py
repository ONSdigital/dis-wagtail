from http import HTTPStatus
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from wagtail.admin.panels import get_edit_handler
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import grant_all_bundle_permissions, make_bundle_viewer
from cms.bundles.viewsets import bundle_chooser_viewset
from cms.release_calendar.viewsets import FutureReleaseCalendarChooserWidget
from cms.teams.models import Team
from cms.users.tests.factories import GroupFactory, UserFactory
from cms.workflows.tests.utils import (
    mark_page_as_ready_for_review,
    mark_page_as_ready_to_publish,
    progress_page_workflow,
)


class BundleViewSetTestCaseBase(WagtailTestUtils, TestCase):
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

        cls.in_review_bundle = BundleFactory(in_review=True, name="Preview Bundle")

        preview_team = Team.objects.create(identifier="foo", name="Preview team")
        BundleTeam.objects.create(parent=cls.in_review_bundle, team=preview_team)
        BundleTeam.objects.create(parent=cls.released_bundle, team=preview_team)
        cls.bundle_viewer.teams.add(preview_team)

        cls.another_in_review_bundle = BundleFactory(in_review=True, name="Another preview Bundle")

    def setUp(self):
        self.bundle = BundleFactory(name="Original bundle", created_by=self.publishing_officer)
        self.statistical_article_page = StatisticalArticlePageFactory(title="PSF")

        self.edit_url = reverse("bundle:edit", args=[self.bundle.id])

        self.client.force_login(self.publishing_officer)


class BundleViewSetTestCase(BundleViewSetTestCaseBase):
    """Test Bundle viewset functionality."""

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

    def test_bundle_edit_view__page_chooser_contain_workflow_state_information(self):
        BundlePageFactory(parent=self.bundle, page=self.statistical_article_page)
        page_title = self.statistical_article_page.get_admin_display_title()

        response = self.client.get(self.edit_url)
        self.assertContains(response, f"{page_title} (not in a workflow)")

        workflow_state = mark_page_as_ready_for_review(self.statistical_article_page, self.publishing_officer)
        response = self.client.get(self.edit_url)
        self.assertContains(response, f"{page_title} (In Preview)")

        progress_page_workflow(workflow_state)
        response = self.client.get(self.edit_url)
        self.assertContains(response, f"{page_title} (Ready to publish)")

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

    def test_inspect_view__previewers__access(self):
        self.client.force_login(self.bundle_viewer)

        scenarios = [
            # bundle id, HTTP status code, message if not allowed
            (self.in_review_bundle.pk, HTTPStatus.OK, False),
            (self.another_in_review_bundle.pk, HTTPStatus.FOUND, True),
            (self.approved_bundle.pk, HTTPStatus.FOUND, True),
            (self.released_bundle.pk, HTTPStatus.FOUND, True),
        ]
        for bundle_id, status_code, check_message in scenarios:
            with self.subTest():
                response = self.client.get(reverse("bundle:inspect", args=[bundle_id]))
                self.assertEqual(response.status_code, status_code)
                if check_message:
                    self.assertEqual(
                        response.context["message"], "Sorry, you do not have permission to access this area."
                    )

    def test_inspect_view__managers__contains_all_fiewls(self):
        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        self.assertContains(response, "Name")
        self.assertContains(response, "Pages")
        self.assertContains(response, "Created at")
        self.assertContains(response, "Created by")
        self.assertContains(response, "Scheduled publication")
        self.assertContains(response, "Approval status")
        self.assertContains(response, "Status")

    def test_inspect_view__previewers__contains_only_relevant_fields(self):
        self.client.force_login(self.bundle_viewer)
        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        self.assertContains(response, "Name")
        self.assertContains(response, "Pages")
        self.assertContains(response, "Created at")
        self.assertContains(response, "Created by")
        self.assertContains(response, "Scheduled publication")
        self.assertNotContains(response, "Approval status")
        self.assertNotContains(response, "Status")


class BundleIndexViewTestCase(BundleViewSetTestCaseBase):
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

    def test_index_view(self):
        """Checks the content of the index page."""
        response = self.client.get(self.bundle_index_url)
        self.assertContains(response, self.edit_url)
        self.assertContains(response, self.approved_bundle_edit_url)
        self.assertNotContains(response, self.released_bundle_edit_url)

        self.assertContains(response, BundleStatus.PENDING.label, 2)  # status + status filter
        self.assertContains(response, BundleStatus.RELEASED.label, 2)  # status + status filter
        self.assertContains(response, BundleStatus.APPROVED.label, 2)  # status + status filter

        self.assertContains(response, self.released_bundle.name)
        self.assertContains(response, self.approved_bundle.name)

    def test_index_view_search(self):
        response = self.client.get(f"{self.bundle_index_url}?q=release")
        self.assertContains(response, self.released_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)

    def test_index_view__previewers__contains_only_relevant_bundles(self):
        self.client.force_login(self.bundle_viewer)

        response = self.client.get(self.bundle_index_url)
        self.assertContains(response, self.in_review_bundle.name)
        self.assertNotContains(response, self.released_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)
        self.assertNotContains(response, self.another_in_review_bundle.name)


class BundleChooserViewsetTestCase(BundleViewSetTestCaseBase):
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
