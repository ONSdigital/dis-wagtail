# pylint: disable=too-many-lines
import textwrap
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import ClassVar
from unittest import mock
from unittest.mock import patch

import time_machine
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F, OrderBy
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.panels import get_edit_handler
from wagtail.models import Locale, Page
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import inline_formset, nested_form_data

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.clients.api import BundleAPIClientError
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import grant_all_bundle_permissions, make_bundle_viewer
from cms.bundles.viewsets.bundle_chooser import bundle_chooser_viewset
from cms.bundles.viewsets.bundle_page_chooser import PagesWithDraftsForBundleChooserWidget, bundle_page_chooser_viewset
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.release_calendar.enums import ReleaseStatus
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
    RELEASE_CALENDAR_PAGE_CASES: ClassVar[list[tuple[str, ReleaseStatus, str]]] = [
        ("Release Calendar Page 1", ReleaseStatus.PROVISIONAL, "Release Calendar Page 1 (Provisional,"),
        ("Release Calendar Page 2", ReleaseStatus.CONFIRMED, "Release Calendar Page 2 (Confirmed,"),
        ("Release Calendar Page 3", ReleaseStatus.CANCELLED, "Release Calendar Page 3 (Cancelled,"),
    ]

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

    def get_base_form_data(self, status: BundleStatus | None = None):
        data = {
            "name": "Original bundle",
            "bundled_datasets": inline_formset([]),
            "teams": inline_formset([]),
        }

        if status in {BundleStatus.APPROVED, BundleStatus.PUBLISHED}:
            # If approved or published, page data must be existing and not considered new
            bundled_pages = BundlePageFactory(parent=self.bundle, page=self.statistical_article_page)
            page_formset = inline_formset(
                [
                    {"id": bundled_pages.id, "page": self.statistical_article_page.id, "ORDER": 1},
                ],
                initial=1,
            )
        else:
            page_formset = inline_formset([{"page": self.statistical_article_page.id}])

        data["bundled_pages"] = page_formset

        return nested_form_data(data)

    @staticmethod
    def chooser_panel_display(page) -> str:
        return f"{page.title} ({page.get_status_display()}, {page.release_date_value})"

    def _create_release_calendar_page(self, title, status):
        """Assigns a release calendar page to the bundle."""
        release_date = timezone.now() + timedelta(days=1)
        release_calendar_page = ReleaseCalendarPageFactory(
            title=title,
            release_date=release_date,
            status=status,
        )
        return release_calendar_page

    def _assign_release_calendar_page_to_bundle(self, release_calendar_page):
        self.bundle.release_calendar_page = release_calendar_page
        self.bundle.save(update_fields=["release_calendar_page"])


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

        data = self.get_base_form_data(status=expected_status)
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

    def test_bundle_edit_view__shows_release_calendar_page_details(self):
        """Release calendar page's title, status and release date are displayed when selected in bundles."""
        for title, status, expected_text in self.RELEASE_CALENDAR_PAGE_CASES:
            with self.subTest(title=title, status=status):
                release_calendar_page = self._create_release_calendar_page(title=title, status=status)
                # when validation of assigning cancelled pages to bundles are improved
                # test for cancelled pages should fail
                self._assign_release_calendar_page_to_bundle(release_calendar_page=release_calendar_page)
                response = self.client.get(self.edit_url)
                expected_display_panel = f"{expected_text} {release_calendar_page.release_date_value})"
                self.assertContains(response, expected_display_panel)

    def test_bundle_edit_view__shows_updated_release_calendar_page_details(self):
        """When release calendar page details are updated, this tests that the updates are reflected on the bundles edit
        page and checks stale values are not present.
        """
        release_calendar_page = self._create_release_calendar_page(
            title="Future Release calendar Page", status=ReleaseStatus.PROVISIONAL
        )
        self._assign_release_calendar_page_to_bundle(release_calendar_page=release_calendar_page)
        original_text = self.chooser_panel_display(release_calendar_page)

        for title, status, expected_text in self.RELEASE_CALENDAR_PAGE_CASES:
            with self.subTest(title=title, status=status):
                release_calendar_page.title = title
                release_calendar_page.status = status
                release_calendar_page.release_date = timezone.now() + timedelta(days=2)
                release_calendar_page.save()
                self.bundle.save()

                response = self.client.get(self.edit_url)
                expected_display_panel = f"{expected_text} {release_calendar_page.release_date_value})"

                self.assertContains(response, expected_display_panel)
                self.assertNotContains(response, original_text)

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
        bundled_page = BundlePageFactory(parent=self.bundle, page=self.statistical_article_page)
        original_status = self.bundle.status

        response = self.client.post(
            self.edit_url,
            nested_form_data(
                {
                    "name": self.bundle.name,
                    "status": BundleStatus.APPROVED,
                    "bundled_pages": inline_formset(
                        [
                            {
                                "id": bundled_page.id,
                                "page": self.statistical_article_page.id,
                                "ORDER": 1,
                            }
                        ],
                        initial=1,
                    ),
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


class BundleViewSetBundleAPIErrorTestCase(BundleViewSetTestCaseBase):
    LONG_TEXT = "Some long description to test truncation. " * 500

    def _build_api_error(self, has_detail_errors: bool) -> BundleAPIClientError:
        if has_detail_errors:
            errors = [
                {"description": "Title already in use"},
                {"description": "Some other error"},
                {"description": self.LONG_TEXT},
                {"no-description-key": ""},
            ]
        else:
            errors = []

        return BundleAPIClientError("API Error", errors=errors)

    # pylint: disable=too-many-locals
    @patch("cms.bundles.forms.BundleAdminForm.save")
    def test_add_and_edit_views_surface_bundle_api_errors(self, mock_save):
        """Both add and edit views should surface Bundle API errors on the form."""
        # Expected banner prefixes for each action
        error_message_for_action = {
            "action-create": "The bundle could not be created due to errors.",
            "action-edit": "The bundle could not be saved due to errors.",
        }

        url_for_action = {
            "action-create": self.bundle_add_url,
            "action-edit": self.edit_url,
        }

        truncated_long_description = textwrap.shorten(self.LONG_TEXT, width=250, placeholder="...")

        error_with_details = [
            "Title already in use",
            "Some other error",
            truncated_long_description,
            "Unknown API Error",
        ]
        error_no_details = ["API Error"]

        cases = [
            ("action-create", True, error_with_details),
            ("action-edit", True, error_with_details),
            ("action-create", False, error_no_details),
            ("action-edit", False, error_no_details),
        ]

        for action, has_detail_errors, expected_errors in cases:
            with self.subTest(action=action, has_detail_errors=has_detail_errors):
                url = url_for_action[action]
                expected_banner_msg = error_message_for_action[action]

                data = self.get_base_form_data(status=BundleStatus.DRAFT)
                data.update(
                    {
                        "name": f"Bundle for {action}",
                        "status": BundleStatus.DRAFT.value,
                        action: action,
                    }
                )

                api_error = self._build_api_error(has_detail_errors)
                validation_error = ValidationError("Failed to sync bundle with Bundle API")
                validation_error.__cause__ = api_error
                mock_save.side_effect = validation_error

                response = self.client.post(url, data, follow=True)
                form = response.context["form"]

                self.assertEqual(response.status_code, 200)

                self.assertContains(response, f"{expected_banner_msg} Failed to sync bundle with Bundle API.")

                self.assertFormError(form=form, field=None, errors=expected_errors)


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

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__displays_message_when_bundle_has_no_dataset_records(self, mock_api_client):
        """Checks that the inspect view displays message when bundle.has_datasets is False."""
        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertContains(response, "No datasets in bundle")
        # API should not be called when has_datasets is False
        mock_api_client.assert_not_called()

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__displays_message_when_no_datasets(self, mock_api_client):
        """Checks that the inspect view displays message when API returns no datasets."""
        self.bundle.bundle_api_bundle_id = "test-bundle-id"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)

        # Mock the Bundle API response with no datasets
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {"items": []}

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertContains(response, "No datasets in bundle")

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__contains_datasets(self, mock_api_client):
        """Checks that the inspect view displays datasets for managers with edit links."""
        # Set API bundle ID
        self.bundle.bundle_api_bundle_id = "test-bundle-id"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)

        dataset_id_a = "dataset-123"
        dataset_id_b = "dataset-456"
        edition_a = "2024"
        edition_b = "2023"
        version_a = "1"
        version_b = "2"

        # Mock the Bundle API response
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": dataset_id_a,
                        "title": "Dataset A",
                        "edition_id": edition_a,
                        "version_id": version_a,
                    },
                    "state": "PUBLISHED",
                    "links": {
                        "edit": f"/data-admin/series/{dataset_id_a}/editions/{edition_a}/versions/{version_a}",
                        "preview": f"/datasets/{dataset_id_a}/editions/{edition_a}/versions/{version_a}",
                    },
                },
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": dataset_id_b,
                        "title": "Dataset B",
                        "edition_id": edition_b,
                        "version_id": version_b,
                    },
                    "state": "APPROVED",
                    "links": {
                        "edit": f"/data-admin/series/{dataset_id_b}/editions/{edition_b}/versions/{version_b}",
                        "preview": f"/datasets/{dataset_id_b}/editions/{edition_b}/versions/{version_b}",
                    },
                },
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertNotContains(response, "No datasets in bundle")

        # Check dataset A (published - should have View Live link)
        self.assertContains(response, "Dataset A")
        self.assertContains(response, version_a)
        self.assertContains(response, edition_a)
        expected_edit_url_a = f"/data-admin/series/{dataset_id_a}/editions/{edition_a}/versions/{version_a}"
        expected_view_url_a = f"/datasets/{dataset_id_a}/editions/{edition_a}/versions/{version_a}"
        self.assertContains(response, f'href="{expected_edit_url_a}"')
        self.assertContains(response, f'href="{expected_view_url_a}"')
        self.assertContains(response, "View Live")

        # Check dataset B (approved - should NOT have View Live link)
        self.assertContains(response, "Dataset B")
        self.assertContains(response, version_b)
        self.assertContains(response, edition_b)
        expected_edit_url_b = f"/data-admin/series/{dataset_id_b}/editions/{edition_b}/versions/{version_b}"
        self.assertContains(response, f'href="{expected_edit_url_b}"')

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

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__datasets_table_display(self, mock_api_client):
        """Test that datasets are displayed in a table format with correct headers and data."""
        self.bundle.bundle_api_bundle_id = "test-bundle-id"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)

        # Mock the Bundle API response
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": "test-dataset-123",
                        "title": "Test Dataset",
                        "edition_id": "2024",
                        "version_id": "1",
                    },
                    "state": "APPROVED",
                    "links": {
                        "edit": "/data-admin/series/test-dataset-123/editions/2024/versions/1",
                    },
                }
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        # Check that the table headers are present
        self.assertContains(response, "<th>Title</th>")
        self.assertContains(response, "<th>Edition</th>")
        self.assertContains(response, "<th>Version</th>")
        self.assertContains(response, "<th>State</th>")
        self.assertContains(response, "<th>Actions</th>")

        # Check that the dataset data is present
        self.assertContains(response, "Test Dataset")
        self.assertContains(response, "2024")
        self.assertContains(response, "1")
        self.assertContains(response, "Approved")
        # Check for data admin URL
        self.assertContains(response, 'href="/data-admin/series/test-dataset-123/editions/2024/versions/1"')
        # APPROVED datasets should not have View Live button
        self.assertNotContains(response, "View Live")

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__datasets_table_with_multiple_datasets(self, mock_api_client):
        """Test that multiple datasets are displayed correctly in the table."""
        self.bundle.bundle_api_bundle_id = "test-bundle-id"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)

        # Mock the Bundle API response with multiple datasets
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": "dataset-one",
                        "title": "Dataset One",
                        "edition_id": "2024",
                        "version_id": "1",
                    },
                    "state": "APPROVED",
                },
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": "dataset-two",
                        "title": "Dataset Two",
                        "edition_id": "2023",
                        "version_id": "2",
                    },
                    "state": "PUBLISHED",
                },
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        # Check that both datasets are present
        self.assertContains(response, "Dataset One")
        self.assertContains(response, "2024")
        self.assertContains(response, "Approved")

        self.assertContains(response, "Dataset Two")
        self.assertContains(response, "2023")
        self.assertContains(response, "Published")
        # Published dataset should have View Live link
        self.assertContains(response, "View Live")
        self.assertContains(response, 'href="/datasets/dataset-two/editions/2023/versions/2"')

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__datasets_table_with_missing_metadata(self, mock_api_client):
        """Test that datasets with missing metadata display N/A."""
        self.bundle.bundle_api_bundle_id = "test-bundle-id"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)

        # Mock the Bundle API response with missing metadata
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {},
                    "links": {},
                }
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        # Check that N/A is displayed for missing data
        self.assertContains(response, "N/A")
        self.assertContains(response, 'href="#"')

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__datasets_for_viewer_without_edit_links(self, mock_api_client):
        """Test that viewers see datasets without edit links."""
        self.in_review_bundle.bundle_api_bundle_id = "test-bundle-id"
        self.in_review_bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.in_review_bundle)

        # Login as bundle viewer (non-manager)
        self.client.force_login(self.bundle_viewer)

        # Mock the Bundle API response
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": "dataset-123",
                        "title": "Test Dataset",
                        "edition_id": "2024",
                        "version_id": "1",
                    },
                    "state": "PUBLISHED",
                }
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        # Dataset title should be present but NOT as a hyperlink
        self.assertContains(response, "Test Dataset")
        self.assertContains(response, "2024")
        self.assertContains(response, "1")
        self.assertContains(response, "Published")

        # Should NOT contain data-admin link
        self.assertNotContains(response, "/data-admin/series/")

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__datasets_for_viewer_approved_no_view_live(self, mock_api_client):
        """Test that viewers see approved datasets without View Live link."""
        self.in_review_bundle.bundle_api_bundle_id = "test-bundle-id"
        self.in_review_bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.in_review_bundle)

        # Login as bundle viewer (non-manager)
        self.client.force_login(self.bundle_viewer)

        # Mock the Bundle API response
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": "dataset-456",
                        "title": "Approved Dataset",
                        "edition_id": "2023",
                        "version_id": "2",
                    },
                    "state": "APPROVED",
                }
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        # Dataset should be present
        self.assertContains(response, "Approved Dataset")
        self.assertContains(response, "2023")
        self.assertContains(response, "2")
        self.assertContains(response, "Approved")

        # Should NOT contain View Live link for non-published datasets
        self.assertNotContains(response, "View Live")

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__displays_message_when_bundle_api_bundle_id_not_set(self, mock_api_client):
        """Test that the inspect view displays an error message when bundle_api_bundle_id is not set."""
        # Explicitly ensure bundle_api_bundle_id is not set
        self.bundle.bundle_api_bundle_id = ""
        self.bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        self.assertContains(response, "Unable to use the Dataset API to display datasets.")
        # API should not be called when bundle_api_bundle_id is not set
        mock_api_client.assert_not_called()

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
    def test_inspect_view__datasets_when_api_disabled(self):
        """Test that the inspect view shows error message when API is disabled."""
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)
        # When API is disabled, bundle_api_bundle_id is typically not set
        self.bundle.bundle_api_bundle_id = ""
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        # Since bundle_api_bundle_id is not set, the error message should appear
        self.assertContains(response, "Unable to use the Dataset API to display datasets.")

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__manager_sees_title_as_hyperlink(self, mock_api_client):
        """Test that managers see dataset titles as hyperlinks to data-admin."""
        self.bundle.bundle_api_bundle_id = "test-bundle-id"
        self.bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.bundle)

        # Mock the Bundle API response
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": "test-123",
                        "title": "Manager Test Dataset",
                        "edition_id": "2024",
                        "version_id": "1",
                    },
                    "state": "APPROVED",
                    "links": {
                        "edit": "/data-admin/series/test-123/editions/2024/versions/1",
                    },
                }
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.bundle.pk]))

        # Check that the title is hyperlinked to data-admin
        expected_url = "/data-admin/series/test-123/editions/2024/versions/1"
        self.assertContains(response, f'<a href="{expected_url}">Manager Test Dataset</a>')

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.viewsets.bundle.BundleAPIClient")
    def test_inspect_view__viewer_sees_title_as_plain_text(self, mock_api_client):
        """Test that viewers see dataset titles as plain text (not hyperlinked)."""
        self.in_review_bundle.bundle_api_bundle_id = "test-bundle-id"
        self.in_review_bundle.save(update_fields=["bundle_api_bundle_id"])
        # Create a bundled_datasets record so has_datasets returns True
        BundleDatasetFactory(parent=self.in_review_bundle)

        # Login as bundle viewer (non-manager)
        self.client.force_login(self.bundle_viewer)

        # Mock the Bundle API response
        mock_client_instance = mock_api_client.return_value
        mock_client_instance.get_bundle_contents.return_value = {
            "items": [
                {
                    "content_type": "DATASET",
                    "metadata": {
                        "dataset_id": "test-456",
                        "title": "Viewer Test Dataset",
                        "edition_id": "2023",
                        "version_id": "2",
                    },
                    "state": "APPROVED",
                }
            ]
        }

        response = self.client.get(reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        # Check that the title is plain text (wrapped in <strong> but no <a> tag)
        self.assertContains(response, "<strong>Viewer Test Dataset</strong>")
        # Make sure there's NO hyperlink to data-admin with this title
        self.assertNotContains(response, '<a href="/data-admin/series/test-456')


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
