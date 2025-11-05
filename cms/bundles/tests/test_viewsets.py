from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from unittest import mock
from unittest.mock import patch

import time_machine
from django.conf import settings
from django.db.models import F, OrderBy
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.panels import get_edit_handler
from wagtail.models import Locale, Page
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import grant_all_bundle_permissions, make_bundle_viewer
from cms.bundles.viewsets.bundle_chooser import bundle_chooser_viewset
from cms.bundles.viewsets.bundle_page_chooser import PagesWithDraftsForBundleChooserWidget, bundle_page_chooser_viewset
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.release_calendar.viewsets import FutureReleaseCalendarChooserWidget
from cms.standard_pages.tests.factories import InformationPageFactory
from cms.teams.models import Team
from cms.topics.models import TopicPage
from cms.topics.tests.factories import TopicPageFactory
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

        cls.dashboard_url = reverse("wagtailadmin_home")
        cls.bundle_index_url = reverse("bundle:index")
        cls.bundle_add_url = reverse("bundle:add")

        cls.published_bundle = BundleFactory(published=True, name="Publish test Bundle")
        cls.published_bundle_edit_url = reverse("bundle:edit", args=[cls.published_bundle.id])

        cls.approved_bundle = BundleFactory(approved=True, name="Approve test Bundle")
        cls.approved_bundle_edit_url = reverse("bundle:edit", args=[cls.approved_bundle.id])

        cls.in_review_bundle = BundleFactory(in_review=True, name="Preview Bundle")
        cls.in_review_bundle_edit_url = reverse("bundle:edit", args=[cls.in_review_bundle.id])

        preview_team = Team.objects.create(identifier="foo", name="Preview team")
        BundleTeam.objects.create(parent=cls.in_review_bundle, team=preview_team)
        BundleTeam.objects.create(parent=cls.published_bundle, team=preview_team)
        cls.bundle_viewer.teams.add(preview_team)

        cls.another_in_review_bundle = BundleFactory(in_review=True, name="Another preview Bundle")

    def setUp(self):
        self.bundle = BundleFactory(name="Original bundle", created_by=self.publishing_officer)
        self.statistical_article_page = StatisticalArticlePageFactory(
            title="The article", parent__title="PSF", live=False
        )

        self.edit_url = reverse("bundle:edit", args=[self.bundle.id])
        self.inspect_url = reverse("bundle:inspect", args=[self.bundle.id])

        self.client.force_login(self.publishing_officer)

    def get_base_form_data(self):
        return nested_form_data(
            {
                "name": "The bundle",
                "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                "bundled_datasets": inline_formset([]),
                "teams": inline_formset([]),
            }
        )


class BundleViewSetAddTestCase(BundleViewSetTestCaseBase):
    def test_bundle_add_view(self):
        """Test bundle creation."""
        self.assertFalse(Bundle.objects.filter(name="A New Bundle").exists())
        response = self.client.post(
            self.bundle_add_url,
            nested_form_data(
                {
                    "name": "A New Bundle",
                    "status": BundleStatus.DRAFT,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                    "bundled_datasets": inline_formset([]),
                }
            ),
        )

        bundle = Bundle.objects.get(name="A New Bundle")
        self.assertRedirects(response, reverse("bundle:edit", args=[bundle.id]))
        self.assertEqual(response.context["message"], "Bundle successfully created.")

    def test_bundle_add_view__with_page_already_in_a_bundle(self):
        """Test bundle creation."""
        response = self.client.post(
            self.bundle_add_url,
            nested_form_data(
                {
                    "name": "A New Bundle",
                    "status": BundleStatus.DRAFT,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                    "bundled_datasets": inline_formset([]),
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

    def test_date_placeholder(self):
        """Test that the date input field displays date placeholder."""
        response = self.client.get(self.bundle_add_url, follow=True)

        content = response.content.decode(encoding="utf-8")
        datetime_placeholder = "YYYY-MM-DD HH:MM"
        self.assertInHTML(
            '<input type="text" name="publication_date" autocomplete="off"'
            f'placeholder="{datetime_placeholder}" id="id_publication_date">',
            content,
        )

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

    def test_add_view_passes_access_token_to_form(self):
        response = self.client.get(self.bundle_add_url)
        self.assertIsNone(response.context["form"].datasets_bundle_api_user_access_token)

        self.client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = "the-access-token"
        response = self.client.get(self.bundle_add_url)
        self.assertEqual(response.context["form"].datasets_bundle_api_user_access_token, "the-access-token")


class BundleViewSetEditTestCase(BundleViewSetTestCaseBase):
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
                    "bundled_datasets": inline_formset([]),
                    "action-edit": "action-edit",
                }
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.name, "Updated Bundle")

    def test_bundle_edit_view__redirects_to_index_for_published_bundles(self):
        """Released bundles should no longer be editable."""
        response = self.client.get(self.published_bundle_edit_url)
        self.assertRedirects(response, self.bundle_index_url)

    def post_with_action_and_test(self, action: str, expected_status: BundleStatus, redirects_to: str):
        self.client.force_login(self.superuser)
        mark_page_as_ready_to_publish(self.statistical_article_page, self.superuser)

        data = self.get_base_form_data()
        data[action] = action
        data["status"] = BundleStatus.PUBLISHED.value  # attempting to force it

        response = self.client.post(self.edit_url, data)
        self.assertRedirects(response, redirects_to)

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, expected_status)

        return response

    def test_bundle_edit_view__generic_save_preserves_the_status(self):
        original_status = self.bundle.status
        self.post_with_action_and_test("action-edit", original_status, self.edit_url)

    def test_bundle_edit_view__save_to_preview(self):
        self.post_with_action_and_test("action-save-to-preview", BundleStatus.IN_REVIEW, self.inspect_url)

    def test_bundle_edit_view__approve__from_invalid_status(self):
        self.post_with_action_and_test("action-approve", BundleStatus.DRAFT, self.dashboard_url)

    @mock.patch("cms.bundles.viewsets.bundle.notify_slack_of_status_change")
    def test_bundle_edit_view__approve__happy_path(self, mock_notify_slack):
        self.bundle.status = BundleStatus.IN_REVIEW
        self.bundle.save(update_fields=["status"])

        self.post_with_action_and_test("action-approve", BundleStatus.APPROVED, self.inspect_url)

        self.assertIsNotNone(self.bundle.approved_at)
        self.assertEqual(self.bundle.approved_by, self.superuser)

        self.assertTrue(mock_notify_slack.called)

    def test_bundle_edit_view__return_to_preview__from_invalid_status(self):
        self.post_with_action_and_test("action-return-to-preview", BundleStatus.DRAFT, self.dashboard_url)

    def test_bundle_edit_view__return_to_preview__happy_path(self):
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])
        self.post_with_action_and_test("action-return-to-preview", BundleStatus.IN_REVIEW, self.inspect_url)

    def test_bundle_edit_view__return_to_draft_from_in_preview(self):
        self.bundle.status = BundleStatus.IN_REVIEW
        self.bundle.save(update_fields=["status"])
        self.post_with_action_and_test("action-return-to-draft", BundleStatus.DRAFT, self.edit_url)

    def test_bundle_edit_view__return_to_draft_from_approved(self):
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])
        self.post_with_action_and_test("action-return-to-draft", BundleStatus.DRAFT, self.edit_url)

    def test_bundle_edit_view__publish__from_invalid_status__draft(self):
        self.bundle.status = BundleStatus.DRAFT
        self.bundle.save(update_fields=["status"])
        response = self.post_with_action_and_test("action-publish", BundleStatus.DRAFT, self.dashboard_url)
        self.assertEqual(response.context["message"], "Sorry, you do not have permission to access this area.")

    def test_bundle_edit_view__publish__from_invalid_status__preview(self):
        self.bundle.status = BundleStatus.IN_REVIEW
        self.bundle.save(update_fields=["status"])
        response = self.post_with_action_and_test("action-publish", BundleStatus.IN_REVIEW, self.dashboard_url)
        self.assertEqual(response.context["message"], "Sorry, you do not have permission to access this area.")

    def test_bundle_edit_view__manual_publish__disallowed_when_scheduled_and_date_in_future(self):
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.publication_date = timezone.now() + timedelta(days=1)
        self.bundle.save(update_fields=["status", "publication_date"])
        self.post_with_action_and_test("action-publish", BundleStatus.APPROVED, self.dashboard_url)

    def test_bundle_edit_view__manual_publish__happy_path__when_scheduled_and_date_in_past(self):
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.publication_date = timezone.now()
        self.bundle.save(update_fields=["status", "publication_date"])
        self.post_with_action_and_test("action-publish", BundleStatus.PUBLISHED, self.bundle_index_url)

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.example.com")
    @patch("cms.bundles.notifications.slack.notify_slack_of_publication_start")
    @patch("cms.bundles.notifications.slack.notify_slack_of_publish_end")
    def test_bundle_edit_view__manual_publish__happy_path__when_linked_with_past_release_calendar_entry(
        self, mock_notify_end, mock_notify_start
    ):
        self.assertFalse(self.statistical_article_page.live)

        BundlePageFactory(parent=self.bundle, page=self.statistical_article_page)
        release_calendar_page = ReleaseCalendarPageFactory(title="Past Release Calendar Page")
        self.bundle.release_calendar_page = release_calendar_page
        self.bundle.publication_date = None
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["release_calendar_page", "publication_date", "status"])

        self.post_with_action_and_test("action-publish", BundleStatus.PUBLISHED, self.bundle_index_url)

        self.assertTrue(mock_notify_start.called)
        self.assertTrue(mock_notify_end.called)

        response = self.client.get(release_calendar_page.url)
        self.assertContains(response, self.statistical_article_page.display_title)

        self.statistical_article_page.refresh_from_db()
        self.assertTrue(self.statistical_article_page.live)
        self.assertIsNone(self.statistical_article_page.current_workflow_state)

    def test_bundle_edit_view__manual_publish__happy_path(self):
        self.bundle.status = BundleStatus.APPROVED
        self.bundle.save(update_fields=["status"])
        self.post_with_action_and_test("action-publish", BundleStatus.PUBLISHED, self.bundle_index_url)

    def test_bundle_edit_view__page_chooser_contain_workflow_state_information(self):
        BundlePageFactory(parent=self.bundle, page=self.statistical_article_page)
        page_title = self.statistical_article_page.get_admin_display_title()

        response = self.client.get(self.edit_url)
        self.assertContains(response, f"{page_title} (Draft)")

        workflow_state = mark_page_as_ready_for_review(self.statistical_article_page, self.publishing_officer)
        response = self.client.get(self.edit_url)
        self.assertContains(response, f"{page_title} (In Preview)")

        progress_page_workflow(workflow_state)
        response = self.client.get(self.edit_url)
        self.assertContains(response, f"{page_title} (Ready to publish)")

    @mock.patch("cms.bundles.viewsets.bundle.notify_slack_of_status_change")
    def test_bundle_approval__cannot__approve_if_pages_are_not_ready_to_publish(self, mock_notify_slack):
        """Test bundle approval workflow."""
        self.client.force_login(self.publishing_officer)
        self.bundle.status = BundleStatus.IN_REVIEW
        self.bundle.save(update_fields=["status"])
        original_status = self.bundle.status

        response = self.client.post(
            self.edit_url,
            nested_form_data(
                {
                    "name": self.bundle.name,
                    "status": BundleStatus.APPROVED,
                    "bundled_pages": inline_formset([{"page": self.statistical_article_page.id}]),
                    "teams": inline_formset([]),
                    "action-approve": "action-approve",
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

    def test_bundle_edit_view__non_readonly(self):
        response = self.client.get(self.edit_url)
        self.assertContains(response, "Choose Release Calendar page")
        self.assertContains(response, "Add page")
        self.assertContains(response, "Add dataset")
        self.assertContains(response, "Add preview team")

    def test_bundle_edit_view__readonly_when_bundle_approved(self):
        self.bundle.status = BundleStatus.IN_REVIEW
        self.bundle.save(update_fields=["status"])
        self.post_with_action_and_test("action-approve", BundleStatus.APPROVED, self.inspect_url)

        response = self.client.get(self.edit_url)
        self.assertNotContains(response, "Choose Release Calendar page")
        self.assertNotContains(response, "Add page")
        self.assertNotContains(response, "Add dataset")
        self.assertNotContains(response, "Add preview team")

        self.assertContains(response, "Statistical article page")
        self.assertContains(response, self.statistical_article_page.get_admin_display_title())

    def test_view_passes_access_token_to_form(self):
        response = self.client.get(self.edit_url)
        self.assertIsNone(response.context["form"].datasets_bundle_api_user_access_token)

        self.client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = "the-access-token"
        response = self.client.get(self.edit_url)
        self.assertEqual(response.context["form"].datasets_bundle_api_user_access_token, "the-access-token")


class BundleViewSetInspectTestCase(BundleViewSetTestCaseBase):
    def test_inspect_view__previewers__access(self):
        self.client.force_login(self.bundle_viewer)

        scenarios = [
            # bundle id, HTTP status code, message if not allowed
            (self.in_review_bundle.pk, HTTPStatus.OK, False),
            (self.another_in_review_bundle.pk, HTTPStatus.FOUND, True),
            (self.approved_bundle.pk, HTTPStatus.FOUND, True),
            (self.published_bundle.pk, HTTPStatus.FOUND, True),
        ]
        for bundle_id, status_code, check_message in scenarios:
            with self.subTest():
                response = self.client.get(reverse("bundle:inspect", args=[bundle_id]))
                self.assertEqual(response.status_code, status_code)
                if check_message:
                    self.assertEqual(
                        response.context["message"], "Sorry, you do not have permission to access this area."
                    )

    def test_inspect_view__managers__contains_all_fields(self):
        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        self.assertContains(response, "Name")
        self.assertContains(response, "Pages")
        self.assertContains(response, "Created at")
        self.assertContains(response, "Created by")
        self.assertContains(response, "Scheduled publication")
        self.assertContains(response, "Associated release calendar")
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
        self.assertContains(response, "Associated release calendar")
        self.assertNotContains(response, "Approval status")
        self.assertNotContains(response, "Status")

    def test_inspect_view__previewers__contains_only_relevant_pages(self):
        methodology_article = MethodologyPageFactory(title="The Test Methodology Article", live=False)
        statistical_article = StatisticalArticlePageFactory(title="The Test Statistical Article", live=False)
        topic_page = TopicPageFactory(title="The Test Topic Page", live=False)

        BundlePageFactory(parent=self.in_review_bundle, page=methodology_article)
        BundlePageFactory(parent=self.in_review_bundle, page=topic_page)
        BundlePageFactory(parent=self.in_review_bundle, page=statistical_article)

        mark_page_as_ready_for_review(methodology_article, self.publishing_officer)
        mark_page_as_ready_for_review(topic_page, self.publishing_officer)
        mark_page_as_ready_for_review(statistical_article, self.publishing_officer)

        # bundle viewer should only see the methodology article
        self.client.force_login(self.bundle_viewer)
        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        self.assertContains(response, "The Test Methodology Article")
        self.assertContains(response, "The Test Statistical Article")
        self.assertNotContains(response, "The Test Topic Page")

        # superuser should see all pages
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))
        self.assertContains(response, "The Test Methodology Article")
        self.assertContains(response, "The Test Statistical Article")
        self.assertContains(response, "The Test Topic Page")

    def test_inspect_view__displays_message_when_no_datasets(self):
        """Checks that the inspect view displays datasets."""
        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertContains(response, "No datasets in bundle")

    def test_inspect_view__contains_datasets(self):
        """Checks that the inspect view displays datasets."""
        bundle_dataset_a = BundleDatasetFactory(parent=self.bundle)
        bundle_dataset_b = BundleDatasetFactory(parent=self.bundle)

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertNotContains(response, "No datasets in bundle")

        self.assertContains(response, bundle_dataset_a.dataset.title)
        self.assertContains(response, bundle_dataset_a.dataset.version)
        self.assertContains(response, bundle_dataset_a.dataset.edition)
        self.assertContains(response, f'href="{bundle_dataset_a.dataset.website_url}"')
        self.assertContains(response, bundle_dataset_b.dataset.title)
        self.assertContains(response, bundle_dataset_b.dataset.version)
        self.assertContains(response, bundle_dataset_b.dataset.edition)
        self.assertContains(response, f'href="{bundle_dataset_b.dataset.website_url}"')

    @override_settings(  # Address race condition in tests caused when calling delete() on a page
        WAGTAILSEARCH_BACKENDS={
            "default": {
                "BACKEND": "wagtail.search.backends.base.SearchBackend",
                "AUTO_UPDATE": False,
            }
        }
    )
    def test_inspect_view__contains_release_calendar_page(self):
        """Checks that the inspect view displays the release calendar page."""
        release_calendar_page = ReleaseCalendarPageFactory(title="Foobar Release Calendar Page")
        self.bundle.release_calendar_page = release_calendar_page
        self.bundle.save(update_fields=["release_calendar_page"])

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertContains(response, "Foobar Release Calendar Page")
        self.assertContains(response, reverse("bundles:preview_release_calendar", args=[self.bundle.id]))

        release_calendar_page.delete()

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        content = response.content.decode("utf-8")
        self.assertInHTML("<dt>Associated release calendar page</dt><dd>N/A</dd>", content)

    def test_inspect_view__links_to_live_pages_after_publication(self):
        release_calendar_page = ReleaseCalendarPageFactory(title="Foobar Release Calendar Page")
        self.bundle.release_calendar_page = release_calendar_page
        self.bundle.status = BundleStatus.PUBLISHED
        self.bundle.save(update_fields=["status", "release_calendar_page"])

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertContains(response, "Foobar Release Calendar Page")
        self.assertContains(response, release_calendar_page.url)
        self.assertNotContains(response, reverse("bundles:preview_release_calendar", args=[self.bundle.id]))

    @time_machine.travel(datetime(2025, 7, 1, 12, 37), tick=False)
    def test_inspect_view__datetime_use_configured_timezone(self):
        bundle = BundleFactory(
            status=BundleStatus.APPROVED,
            approved_by=self.superuser,
            approved_at=datetime(2025, 7, 1, 12, 45, tzinfo=UTC),
            publication_date=datetime(2025, 7, 1, 13, 00, tzinfo=UTC),
        )
        response = self.client.get(reverse("bundle:inspect", args=[bundle.pk]))

        self.assertContains(response, "1 July 2025 1:37pm")
        self.assertContains(response, "1 July 2025 1:45pm")
        self.assertContains(response, "1 July 2025 2:00pm")

    def test_inspect_view__shows_bundle_api_bundle_id_when_exists(self):
        # Ensure the bundle has "bundle_api_bundle_id" set
        self.bundle.bundle_api_bundle_id = "bundle-api-id-123"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        # Label and value are shown
        self.assertContains(response, "Dataset Bundle API ID")
        self.assertContains(response, "bundle-api-id-123")

    def test_inspect_view__hides_bundle_api_bundle_id_when_not_exists(self):
        # Ensure the bundle does not have "bundle_api_bundle_id" set
        self.bundle.bundle_api_bundle_id = ""
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        # Label not shown
        self.assertNotContains(response, "Dataset Bundle API ID")

    def test_inspect_view__previewers__never_shown_bundle_api_bundle_id(self):
        """Previewers should not see the API ID, even if it exists."""
        # Give the in-review bundle datasets and an API ID
        self.in_review_bundle.bundle_api_bundle_id = "bundle-api-id-123"
        self.in_review_bundle.save(update_fields=["bundle_api_bundle_id"])

        # Login as viewer (previewer flow)
        self.client.force_login(self.bundle_viewer)
        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        # Label and value are not shown
        self.assertNotContains(response, "Dataset Bundle API ID")
        self.assertNotContains(response, "bundle-api-id-123")


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
        self.assertNotContains(response, self.published_bundle_edit_url)

        self.assertContains(response, BundleStatus.DRAFT.label, 2)  # status + status filter
        self.assertContains(response, BundleStatus.APPROVED.label, 3)  # status + status filter + shortcut button
        self.assertContains(response, BundleStatus.PUBLISHED.label, 1)  # status filter

        self.assertContains(response, self.approved_bundle.name)
        self.assertContains(response, self.bundle.name)
        self.assertNotContains(response, self.published_bundle.name)

        self.assertContains(response, "View &quot;Ready to publish&quot;")
        self.assertContains(response, f"{self.bundle_index_url}?status={BundleStatus.APPROVED}")

    def test_index_view_contains_published_bundle_when_status_filter_applied(self):
        response = self.client.get(self.bundle_index_url, query_params={"status": BundleStatus.PUBLISHED})
        self.assertContains(response, self.published_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)
        self.assertNotContains(response, self.bundle.name)

    def test_index_view_search(self):
        response = self.client.get(self.bundle_index_url, query_params={"q": "test"})
        self.assertContains(response, self.approved_bundle.name)
        self.assertNotContains(response, self.published_bundle.name)

    def test_index_view__previewers__contains_only_relevant_bundles(self):
        self.client.force_login(self.bundle_viewer)

        another_preview_team = Team.objects.create(identifier="bar", name="Another preview team")
        BundleTeam.objects.create(parent=self.in_review_bundle, team=another_preview_team)
        self.bundle_viewer.teams.add(another_preview_team)

        response = self.client.get(self.bundle_index_url)
        # the title + label for inspect link
        self.assertContains(response, self.in_review_bundle.name, 2)
        self.assertNotContains(response, self.published_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)
        self.assertNotContains(response, self.another_in_review_bundle.name)
        self.assertNotContains(response, "View &quot;Ready to publish&quot;")

    def test_index_view__previewers__search(self):
        self.client.force_login(self.bundle_viewer)

        another_preview_team = Team.objects.create(identifier="bar", name="Another preview team")
        self.bundle_viewer.teams.add(another_preview_team)
        BundleTeam.objects.create(parent=self.in_review_bundle, team=another_preview_team)
        BundleTeam.objects.create(parent=self.approved_bundle, team=another_preview_team)

        response = self.client.get(self.bundle_index_url, query_params={"q": "Bundle"})
        self.assertContains(response, self.in_review_bundle.name, 2)
        self.assertContains(response, self.approved_bundle.name, 2)
        self.assertNotContains(response, self.published_bundle.name)
        self.assertNotContains(response, self.another_in_review_bundle.name)

        response = self.client.get(self.bundle_index_url, query_params={"q": "Preview"})
        self.assertContains(response, self.in_review_bundle.name, 2)
        self.assertNotContains(response, self.approved_bundle.name)
        self.assertNotContains(response, self.published_bundle.name)
        self.assertNotContains(response, self.another_in_review_bundle.name)

    def test_ordering(self):
        """Checks that the correct ordering is applied."""
        cases = {
            "": ("name",),
            "name": ("name",),
            "-name": ("-name",),
            "scheduled_publication_date": (OrderBy(F("release_date"), descending=False, nulls_last=True),),
            "-scheduled_publication_date": (OrderBy(F("release_date"), descending=True, nulls_last=True),),
            "status": (OrderBy(F("status_label"), descending=False),),
            "-status": (OrderBy(F("status_label"), descending=True),),
            "invalid_ordering": ("name",),
        }
        for param, order_by in cases.items():
            with self.subTest(param=param):
                response = self.client.get(self.bundle_index_url, query_params={"ordering": param})
                self.assertEqual(
                    response.context_data["object_list"].query.order_by,
                    order_by,
                )


class BundleChooserViewsetTestCase(BundleViewSetTestCaseBase):
    def test_chooser_viewset(self):
        draft_bundle = BundleFactory(name="Draft")
        response = self.client.get(bundle_chooser_viewset.widget_class().get_chooser_modal_url())

        self.assertContains(response, draft_bundle.name)
        self.assertNotContains(response, self.published_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)

    def test_chooser_search(self):
        draft_bundle = BundleFactory(name="Draft")
        chooser_results_url = reverse(bundle_chooser_viewset.get_url_name("choose_results"))

        response = self.client.get(f"{chooser_results_url}?q=approve")

        self.assertNotContains(response, draft_bundle.name)
        self.assertNotContains(response, self.published_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)

        response = self.client.get(f"{chooser_results_url}?q=draft")

        self.assertContains(response, draft_bundle.name)
        self.assertNotContains(response, self.published_bundle.name)
        self.assertNotContains(response, self.approved_bundle.name)


class BundlePageChooserViewsetTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.bundle = BundleFactory()

        cls.page_draft = StatisticalArticlePageFactory(
            live=False, title="Article draft", parent__title="Article series"
        )
        cls.page_draft.save_revision()
        cls.page_live = StatisticalArticlePageFactory(live=True, title="Live page")
        cls.page_live_plus_draft = StatisticalArticlePageFactory(live=True, title="Live page with draft")
        cls.page_live_plus_draft.save_revision()

        cls.page_draft_in_bundle = StatisticalArticlePageFactory(live=False, title="Draft page in a bundle")
        cls.page_draft_in_bundle.save_revision()
        BundlePageFactory(parent=cls.bundle, page=cls.page_draft_in_bundle)

        cls.chooser_url = bundle_page_chooser_viewset.widget_class().get_chooser_modal_url()
        cls.chooser_results_url = reverse(bundle_page_chooser_viewset.get_url_name("choose_results"))

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_bundle_form_uses_bundle_page_chooser_widget(self):
        form_class = get_edit_handler(Bundle).get_form_class()
        form = form_class(instance=self.bundle).formsets["bundled_pages"].forms[0]

        self.assertIn("page", form.fields)
        chooser_widget = form.fields["page"].widget
        self.assertIsInstance(chooser_widget, PagesWithDraftsForBundleChooserWidget)

        self.assertEqual(
            chooser_widget.get_chooser_modal_url(),
            # the admin path + the chooser namespace
            reverse("wagtailadmin_home") + "bundle_page_chooser/",
        )

    def test_choose_view(self):
        welsh_page_draft = self.page_draft.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), copy_parents=True
        )
        welsh_page_draft.save_revision()
        information_page = InformationPageFactory(title="An information page")
        information_page.save_revision()

        response = self.client.get(self.chooser_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/chooser.html")

        self.assertContains(response, self.page_draft.get_admin_display_title(), 2)  # en + cy
        self.assertContains(response, self.page_live_plus_draft.get_admin_display_title(), 1)
        self.assertContains(response, self.page_live_plus_draft.get_parent().title, 1)  # as part of the article
        self.assertContains(response, TopicPage.objects.ancestor_of(self.page_live_plus_draft).first().title, 1)
        self.assertContains(response, information_page.title, 1)
        self.assertContains(response, information_page.get_parent(), 1)
        self.assertNotContains(response, self.page_live.get_admin_display_title())
        self.assertNotContains(response, self.page_draft_in_bundle.get_admin_display_title())

        # Test that the chooser includes the correct columns
        self.assertContains(response, "Locale")
        self.assertContains(response, "English")
        self.assertContains(response, "Welsh")
        self.assertContains(response, "Parent")
        self.assertContains(response, self.page_draft.get_parent().get_admin_display_title())

    def test_choose_view__includes_page_in_inactive_bundle(self):
        self.bundle.status = BundleStatus.PUBLISHED
        self.bundle.save(update_fields=["status"])

        response = self.client.get(self.chooser_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "wagtailadmin/generic/chooser/chooser.html")

        self.assertContains(response, self.page_draft_in_bundle.get_admin_display_title())

    def test_choose_view__excludes_aliases(self):
        # create an alias for one of the pages
        self.page_draft.copy_for_translation(
            locale=Locale.objects.get(language_code="cy"), alias=True, copy_parents=True
        )

        response = self.client.get(self.chooser_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.page_draft.get_admin_display_title(), 1)

    def test_choose_view__no_results(self):
        self.page_draft.save_revision().publish()
        self.page_live_plus_draft.save_revision().publish()

        response = self.client.get(f"{self.chooser_url}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "There are no draft pages that are not in an active bundle.")

    def test_chooser_search(self):
        response = self.client.get(f"{self.chooser_results_url}?q=Article")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bundles/bundle_page_chooser_results.html")

        self.assertContains(response, self.page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_live.get_admin_display_title())
        self.assertNotContains(response, self.page_draft_in_bundle.get_admin_display_title())

    def test_chooser_filter(self):  # pylint: disable=too-many-statements # noqa
        methodology_page_draft = MethodologyPageFactory(live=False, title="Bundle test methodology page")
        methodology_page_draft.save_revision()
        information_page_draft = InformationPageFactory(live=False, title="Bundle test information page")
        information_page_draft.save_revision()
        topic_page_draft = TopicPageFactory(live=False, title="Bundle test topic page")
        topic_page_draft.save_revision()

        # Test different page type permutations
        response = self.client.get(f"{self.chooser_results_url}?page_type=MethodologyPage")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bundles/bundle_page_chooser_results.html")

        self.assertContains(response, methodology_page_draft.get_admin_display_title())
        self.assertNotContains(response, information_page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_draft_in_bundle.get_admin_display_title())
        self.assertNotContains(response, information_page_draft.get_admin_display_title())
        self.assertNotContains(response, topic_page_draft.get_admin_display_title())

        response = self.client.get(f"{self.chooser_results_url}?page_type=InformationPage")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, information_page_draft.get_admin_display_title())
        self.assertNotContains(response, methodology_page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_draft_in_bundle.get_admin_display_title())
        self.assertNotContains(response, topic_page_draft.get_admin_display_title())

        response = self.client.get(f"{self.chooser_results_url}?page_type=StatisticalArticlePage")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_live.get_admin_display_title())
        self.assertNotContains(response, self.page_draft_in_bundle.get_admin_display_title())
        self.assertNotContains(response, methodology_page_draft.get_admin_display_title())
        self.assertNotContains(response, information_page_draft.get_admin_display_title())
        self.assertNotContains(response, topic_page_draft.get_admin_display_title())

        response = self.client.get(f"{self.chooser_results_url}?page_type=TopicPage")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, topic_page_draft.get_admin_display_title())
        self.assertNotContains(response, methodology_page_draft.get_admin_display_title())
        self.assertNotContains(response, information_page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_draft_in_bundle.get_admin_display_title())
        self.assertNotContains(response, self.page_live.get_admin_display_title())

        response = self.client.get(f"{self.chooser_results_url}?page_type=")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.page_draft.get_admin_display_title())
        self.assertContains(response, self.page_live_plus_draft.get_admin_display_title())
        self.assertContains(response, methodology_page_draft.get_admin_display_title())
        self.assertContains(response, information_page_draft.get_admin_display_title())
        self.assertContains(response, topic_page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_live.get_admin_display_title())

        # "foo" (or any unknown type) will be forced to "" in the filter form
        response = self.client.get(f"{self.chooser_results_url}?page_type=foo")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.page_draft.get_admin_display_title())
        self.assertContains(response, self.page_live_plus_draft.get_admin_display_title())
        self.assertContains(response, methodology_page_draft.get_admin_display_title())
        self.assertContains(response, information_page_draft.get_admin_display_title())
        self.assertContains(response, topic_page_draft.get_admin_display_title())
        self.assertNotContains(response, self.page_live.get_admin_display_title())

    def test_chooser_viewset_configuration(self):
        self.assertFalse(bundle_page_chooser_viewset.register_widget)
        self.assertEqual(bundle_page_chooser_viewset.model, Page)
        self.assertEqual(bundle_page_chooser_viewset.choose_one_text, "Choose a page")
        self.assertEqual(bundle_page_chooser_viewset.choose_another_text, "Choose another page")
        self.assertEqual(bundle_page_chooser_viewset.edit_item_text, "Edit this page")

    def test_chosen(self):
        response = self.client.get(
            reverse(
                bundle_page_chooser_viewset.get_url_name("chosen"),
                args=[self.page_draft.pk],
            )
        )
        response_json = response.json()

        self.assertEqual(response_json["result"]["id"], str(self.page_draft.pk))
        self.assertEqual(response_json["result"]["title"], f"{self.page_draft.get_admin_display_title()} (Draft)")

    def test_chosen_multiple(self):
        mark_page_as_ready_for_review(self.page_draft)
        response = self.client.get(
            reverse(
                bundle_page_chooser_viewset.get_url_name("chosen"),
                args=[self.page_draft.pk],
                query={"multiple": True},
            )
        )
        response_json = response.json()

        self.assertEqual(response_json["result"][0]["id"], str(self.page_draft.pk))
        self.assertEqual(
            response_json["result"][0]["title"], f"{self.page_draft.get_admin_display_title()} (In Preview)"
        )
