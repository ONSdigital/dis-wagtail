from http import HTTPStatus

import responses
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.models import ModelLogEntry
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.admin_forms import AddToBundleForm
from cms.bundles.enums import PREVIEWABLE_BUNDLE_STATUSES, BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.tests.factories import BundleDatasetFactory, BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import (
    create_bundle_manager,
    create_bundle_viewer,
    grant_all_bundle_permissions,
)
from cms.home.models import HomePage
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import GroupFactory, UserFactory
from cms.workflows.tests.utils import (
    mark_page_as_ready_for_review,
    mark_page_as_ready_to_publish,
    progress_page_workflow,
)


class AddToBundleViewTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.publishing_officer = create_bundle_manager()
        cls.bundle_viewer = create_bundle_viewer()

    def setUp(self):
        self.bundle = BundleFactory(name="First Bundle", created_by=self.publishing_officer)
        self.statistical_article_page = StatisticalArticlePageFactory(title="November 2024", parent__title="PSF")
        self.add_url = reverse("bundles:add_to_bundle", args=[self.statistical_article_page.id])
        self.bundle_index_url = reverse("bundle:index")

        self.client.force_login(self.publishing_officer)

    def test_dispatch__happy_path(self):
        """Dispatch should not complain about anything."""
        response = self.client.get(f"{self.add_url}?next={self.bundle_index_url}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "bundles/wagtailadmin/add_to_bundle.html")

        self.assertEqual(response.context["page_to_add"], self.statistical_article_page)
        self.assertEqual(response.context["next"], self.bundle_index_url)
        self.assertIsInstance(response.context["form"], AddToBundleForm)
        self.assertEqual(response.context["form"].page_to_add, self.statistical_article_page)

    def test_dispatch__returns_404_for_wrong_page_id(self):
        """The page must exist in the first place."""
        url = reverse("bundles:add_to_bundle", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_dispatch__returns_404_for_non_bundleable_page(self):
        """Only pages with BundledPageMixin can be added to a bundle."""
        url = reverse("bundles:add_to_bundle", args=[self.statistical_article_page.get_parent().id])
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
        BundlePageFactory(parent=another_bundle, page=self.statistical_article_page)
        response = self.client.get(self.add_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "Page &#x27;PSF: November 2024&#x27; is already in a bundle")

    def test_post__successful(self):
        """Checks that on successful post, the page is added to the bundle and
        we get redirected to the valid next URL.
        """
        response = self.client.post(
            f"{self.add_url}?next={self.bundle_index_url}", data={"bundle": self.bundle.id}, follow=True
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Page &#x27;PSF: November 2024&#x27; added to bundle &#x27;First Bundle&#x27;")
        self.assertQuerySetEqual(self.statistical_article_page.bundles, Bundle.objects.all())


class PreviewBundleViewTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.publishing_officer = create_bundle_manager()
        cls.previewer = create_bundle_viewer()

        cls.user_with_only_admin_access = UserFactory(access_admin=True)

        cls.bundle = BundleFactory(name="First Bundle", in_review=True, created_by=cls.publishing_officer)

        cls.page_ready_for_publishing = StatisticalArticlePageFactory(title="March 2025", parent__title="PSF")
        mark_page_as_ready_to_publish(cls.page_ready_for_publishing, cls.publishing_officer)

        cls.page_not_ready_for_publishing = StatisticalArticlePageFactory(title="January 2025", parent__title="PSF")

        BundlePageFactory(parent=cls.bundle, page=cls.page_ready_for_publishing)
        BundlePageFactory(parent=cls.bundle, page=cls.page_not_ready_for_publishing)

        cls.preview_team = Team.objects.create(identifier="psf", name="PSF preview")
        cls.team = Team.objects.create(identifier="foo", name="Not a preview team")
        cls.inactive_team = Team.objects.create(identifier="inactive", name="Retired", is_active=False)

        BundleTeam.objects.create(parent=cls.bundle, team=cls.preview_team)
        BundleTeam.objects.create(parent=cls.bundle, team=cls.inactive_team)

        cls.url_preview_ready = reverse("bundles:preview", args=[cls.bundle.pk, cls.page_ready_for_publishing.pk])
        cls.url_not_preview_ready = reverse(
            "bundles:preview", args=[cls.bundle.pk, cls.page_not_ready_for_publishing.pk]
        )

    def test_view_requires_access_to_admin(self):
        response = self.client.get(self.url_preview_ready, follow=True)
        self.assertRedirects(response, f"/admin/login/?next={self.url_preview_ready}")

        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.url_preview_ready)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_view_checks__bundle_and_page_exists(self):
        self.client.force_login(self.superuser)
        scenarios = [
            # bundle id, page id, success
            (self.bundle.pk, self.page_ready_for_publishing.pk, HTTPStatus.OK),
            (self.bundle.pk, 99999, HTTPStatus.NOT_FOUND),
            (99999, self.page_ready_for_publishing.pk, HTTPStatus.NOT_FOUND),
        ]

        for bundle_id, page_id, status_code in scenarios:
            with self.subTest(f"Bundle {bundle_id}, Page {page_id}, HTTP Status: {status_code}"):
                response = self.client.get(reverse("bundles:preview", args=[bundle_id, page_id]))
                self.assertEqual(response.status_code, status_code)

    def test_view_checks__page_in_bundle(self):
        # log in with the superuser as the check is whether the page is in the bundle or not
        self.client.force_login(self.superuser)

        page = HomePage.objects.first()
        response = self.client.get(reverse("bundles:preview", args=[self.bundle.pk, page.pk]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_view_checks__user_can_preview(self):
        scenarios = [
            (self.superuser, HTTPStatus.OK, None),
            (self.publishing_officer, HTTPStatus.OK, None),
            # while they are previewer, they are not in the right team
            (self.previewer, HTTPStatus.FOUND, "Sorry, you do not have permission to access this area."),
            (
                self.user_with_only_admin_access,
                HTTPStatus.FOUND,
                "Sorry, you do not have permission to access this area.",
            ),
        ]

        for user, status_code, message in scenarios:
            with self.subTest(f"User: {user}, HTTP status: {status_code}"):
                self.client.force_login(user)
                response = self.client.get(self.url_preview_ready)
                self.assertEqual(response.status_code, status_code)

                if message:
                    self.assertEqual(response.context["message"], message)

    def test_view__previewer_can_preview_only_when_in_the_correct_preview_team(self):
        self.client.force_login(self.previewer)

        # while the team is in the bundle, it is inactive, so no access
        self.previewer.teams.add(self.inactive_team)
        response = self.client.get(self.url_preview_ready, follow=True)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

        self.previewer.teams.add(self.preview_team)
        response = self.client.get(self.url_preview_ready)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, self.url_preview_ready)
        self.assertContains(response, self.page_ready_for_publishing.display_title)
        self.assertNotContains(response, self.url_not_preview_ready)

    def test_view__previewer_can_preview_only_when_bundle_in_review_or_ready_to_be_published(self):
        self.client.force_login(self.previewer)

        self.previewer.teams.add(self.preview_team)
        for status in [BundleStatus.DRAFT, BundleStatus.PUBLISHED]:
            self.bundle.status = status
            self.bundle.save(update_fields=["status"])
            response = self.client.get(self.url_preview_ready, follow=True)
            self.assertContains(response, "Sorry, you do not have permission to access this area.")

        for status in PREVIEWABLE_BUNDLE_STATUSES:
            with self.subTest(f"Status: {status}"):
                self.bundle.status = status
                self.bundle.save(update_fields=["status"])
                response = self.client.get(self.url_preview_ready)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertContains(response, self.page_ready_for_publishing.title)

    def test_view_checks__page_ready_to_be_published(self):
        # previewers can only access pages that are ready to publish
        self.client.force_login(self.previewer)
        self.previewer.teams.add(self.preview_team)

        response = self.client.get(self.url_not_preview_ready)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # bundle managers can use the preview even if the page is not ready
        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.url_not_preview_ready)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_preview_logs_action(self):
        self.client.force_login(self.publishing_officer)

        self.assertEqual(ModelLogEntry.objects.filter(action="bundles.preview").count(), 0)

        self.client.get(self.url_preview_ready)

        log_entries = ModelLogEntry.objects.filter(action="bundles.preview")
        self.assertEqual(len(log_entries), 1)

        entry = log_entries[0]
        self.assertEqual(entry.user, self.publishing_officer)
        self.assertDictEqual(
            entry.data,
            {
                "type": "page",
                "id": self.page_ready_for_publishing.pk,
                "title": self.page_ready_for_publishing.display_title,
            },
        )

    def test_preview_without_access_logs_action(self):
        self.client.force_login(self.user_with_only_admin_access)

        self.client.get(self.url_preview_ready)

        log_entries = ModelLogEntry.objects.filter(action="bundles.preview.attempt")
        self.assertEqual(len(log_entries), 1)

        entry = log_entries[0]
        self.assertEqual(entry.user, self.user_with_only_admin_access)
        self.assertDictEqual(
            entry.data,
            {
                "type": "page",
                "id": self.page_ready_for_publishing.pk,
                "title": self.page_ready_for_publishing.display_title,
            },
        )

        self.assertEqual(ModelLogEntry.objects.filter(action="bundles.preview").count(), 0)


@override_settings(
    DIS_DATASETS_BUNDLE_API_ENABLED=True,
    DIS_DATASETS_BUNDLE_API_BASE_URL="https://test-api.example.com",
)
class DeleteBundleViewTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publishing_group = GroupFactory(name="Publishing Officers", access_admin=True)
        grant_all_bundle_permissions(cls.publishing_group)
        cls.publishing_officer = UserFactory(username="publishing_officer")
        cls.publishing_officer.groups.add(cls.publishing_group)

    def setUp(self):
        self.bundle = BundleFactory(name="A Bundle", created_by=self.publishing_officer)
        self.client.force_login(self.publishing_officer)
        self.base_url = settings.DIS_DATASETS_BUNDLE_API_BASE_URL
        self.client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = "the-access-token"

    def _set_api_id(self, value: str | None):
        self.bundle.refresh_from_db()
        self.bundle.bundle_api_bundle_id = value or ""
        self.bundle.save(update_fields=["bundle_api_bundle_id"])

    def _delete_url(self) -> str:
        return reverse("bundle:delete", args=[self.bundle.pk])

    def _post_delete(self):
        return self.client.post(self._delete_url(), follow=True, data={"action-delete": "delete"})

    def _api_url(self, api_id: str) -> str:
        return f"{self.base_url}/bundles/{api_id}"

    def _assert_deleted(self, pk: int):
        with self.assertRaises(Bundle.DoesNotExist):
            Bundle.objects.get(pk=pk)

    @responses.activate
    def test_sync_bundle_deletion_with_bundle_api__successful_deletion(self):
        """Bundle is deleted in CMS and remote when API call is successful."""
        # Given
        self._set_api_id("bundle-content-id-123")
        bundle_api_mock = responses.delete(
            self._api_url(self.bundle.bundle_api_bundle_id), status=HTTPStatus.NO_CONTENT
        )

        # When
        response = self._post_delete()

        # Then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self._assert_deleted(self.bundle.pk)

        # API called exactly once with token header
        self.assertEqual(bundle_api_mock.call_count, 1)
        call = bundle_api_mock.calls[0]
        self.assertEqual(call.request.headers["Authorization"], "the-access-token")

    @responses.activate
    def test_sync_bundle_deletion_with_bundle_api__handles_404_error(self):
        """404 error from remote API should not prevent CMS delete."""
        # Given
        self._set_api_id("bundle-api-id-789")
        bundle_api_mock = responses.delete(
            self._api_url(self.bundle.bundle_api_bundle_id),
            status=HTTPStatus.NOT_FOUND,
            json={"message": "Bundle not found"},
        )

        # When
        response = self._post_delete()

        # Then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self._assert_deleted(self.bundle.pk)
        self.assertEqual(bundle_api_mock.call_count, 1)

    @responses.activate
    def test_sync_bundle_deletion_with_bundle_api__non_404_error_prevents_deletion(self):
        """Non-404 error from remote API prevents CMS delete."""
        # Given
        self._set_api_id("bundle-api-id-500")
        bundle_api_mock = responses.delete(
            self._api_url(self.bundle.bundle_api_bundle_id),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            json={"message": "Internal server error"},
        )

        # When
        response = self._post_delete()

        # Then
        self.assertRedirects(response, reverse("bundle:index"))
        self.assertContains(response, "The bundle could not be deleted due to errors")
        self.assertContains(response, "Failed to delete bundle from Bundle API")

        bundle = Bundle.objects.get(pk=self.bundle.pk)
        self.assertEqual(bundle.name, "A Bundle")
        self.assertEqual(bundle.bundle_api_bundle_id, "bundle-api-id-500")
        self.assertEqual(bundle_api_mock.call_count, 1)

    @responses.activate
    def test_sync_bundle_deletion_with_bundle_api__skips_when_no_bundle_api_id(self):
        """When no API ID, delete locally and make no HTTP calls."""
        # Given
        self._set_api_id(None)

        # When
        response = self._post_delete()

        # Then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self._assert_deleted(self.bundle.pk)
        # No HTTP calls at all
        self.assertEqual(len(responses.calls), 0)

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
    @responses.activate
    def test_sync_bundle_deletion_with_bundle_api__skips_when_api_disabled(self):
        """When API integration is disabled, delete locally and make no HTTP calls."""
        # Given
        self._set_api_id("bundle-api-id-disabled")

        # When
        response = self._post_delete()

        # Then
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self._assert_deleted(self.bundle.pk)
        self.assertEqual(len(responses.calls), 0)


class PreviewBundleReleaseCalendarViewTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")
        cls.publishing_officer = create_bundle_manager()

        cls.release_calendar_page = ReleaseCalendarPageFactory()
        cls.bundle = BundleFactory(
            name="First Bundle", created_by=cls.publishing_officer, release_calendar_page=cls.release_calendar_page
        )

        cls.preview_url = reverse("bundles:preview_release_calendar", args=[cls.bundle.pk])

    def test_view_requires_access_to_admin(self):
        response = self.client.get(self.preview_url, follow=True)
        self.assertRedirects(response, f"/admin/login/?next={self.preview_url}")

        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_preview_release_calendar_page(self):
        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.release_calendar_page.title)

    def test_preview_release_calendar_page_when_bundle_does_not_exit(self):
        self.client.force_login(self.publishing_officer)
        response = self.client.get(reverse("bundles:preview_release_calendar", args=[99999]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @override_settings(  # Address race condition in tests caused when calling delete() on a page
        WAGTAILSEARCH_BACKENDS={
            "default": {
                "BACKEND": "wagtail.search.backends.base.SearchBackend",
                "AUTO_UPDATE": False,
            }
        }
    )
    def test_preview_release_calendar_page_when_no_release_calendar_page(self):
        self.client.force_login(self.publishing_officer)
        self.release_calendar_page.delete()

        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_unauthorized_access_to_preview_release_calendar_page(self):
        # Test that a user without the right permissions cannot access the preview page
        unauthorized_user = UserFactory(access_admin=True)
        self.client.force_login(unauthorized_user)

        response = self.client.get(self.preview_url, follow=True)
        self.assertRedirects(response, "/admin/")
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_preview_release_calendar_page_with_pages_and_datasets(self):
        self.client.force_login(self.publishing_officer)
        statistical_article = StatisticalArticlePageFactory()
        methodology_article = StatisticalArticlePageFactory()
        BundlePageFactory(parent=self.bundle, page=statistical_article)
        BundlePageFactory(parent=self.bundle, page=methodology_article)
        bundle_dataset_a = BundleDatasetFactory(parent=self.bundle)
        bundle_dataset_b = BundleDatasetFactory(parent=self.bundle)
        bundle_dataset_c = BundleDatasetFactory(parent=self.bundle)

        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, statistical_article.title)
        self.assertContains(response, methodology_article.title)
        self.assertContains(response, bundle_dataset_a.dataset.title)
        self.assertContains(response, bundle_dataset_b.dataset.title)
        self.assertContains(response, bundle_dataset_c.dataset.title)

    def test_preview_release_calendar_page_shows_status(self):
        self.client.force_login(self.publishing_officer)
        statistical_article = StatisticalArticlePageFactory()

        BundlePageFactory(parent=self.bundle, page=statistical_article)

        response = self.client.get(self.preview_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f"{statistical_article.title} (Draft)")

        workflow_state = mark_page_as_ready_for_review(statistical_article, self.publishing_officer)

        response = self.client.get(self.preview_url)

        self.assertContains(response, f"{statistical_article.title} (In Preview)")

        progress_page_workflow(workflow_state)

        response = self.client.get(self.preview_url)

        self.assertContains(response, f"{statistical_article.title} (Ready to publish)")

    def test_preview_release_calendar_page_has_preview_bar(self):
        self.client.force_login(self.publishing_officer)
        statistical_article = StatisticalArticlePageFactory()

        BundlePageFactory(parent=self.bundle, page=statistical_article)

        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.content.decode("utf-8")
        release_calendar_url = reverse("bundles:preview_release_calendar", args=[self.bundle.pk])
        self.assertInHTML(
            f'<option value="{release_calendar_url}">{self.release_calendar_page.title}</option>',
            content,
        )

        statistical_article_url = reverse("bundles:preview", args=[self.bundle.pk, statistical_article.pk])
        self.assertInHTML(
            f'<option value="{statistical_article_url}">{statistical_article.display_title}</option>', content
        )

    def test_preview_release_calendar_page_uses_correct_page_preview_url(self):
        self.client.force_login(self.publishing_officer)
        statistical_article = StatisticalArticlePageFactory()
        methodology_article = StatisticalArticlePageFactory()

        BundlePageFactory(parent=self.bundle, page=statistical_article)
        BundlePageFactory(parent=self.bundle, page=methodology_article)

        response = self.client.get(self.preview_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, reverse("bundles:preview", args=[self.bundle.pk, statistical_article.pk]))
        self.assertContains(response, reverse("bundles:preview", args=[self.bundle.pk, methodology_article.pk]))

    def test_preview_release_calendar_page_shows_preview_bar(self):
        self.client.force_login(self.publishing_officer)
        statistical_article = StatisticalArticlePageFactory()
        methodology_article = StatisticalArticlePageFactory()

        BundlePageFactory(parent=self.bundle, page=statistical_article)
        BundlePageFactory(parent=self.bundle, page=methodology_article)

        response = self.client.get(self.preview_url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Check for presence of bundle_inspect_url
        self.assertContains(response, reverse("bundle:inspect", args=[self.bundle.pk]))

        content = response.content.decode("utf-8")

        # Check if preview bar is present and contains the correct options
        self.assertInHTML(
            '<label class="ons-label" for="preview-items">Preview items</label>',
            content,
        )
        self.assertInHTML(
            f'<option value="{reverse("bundles:preview_release_calendar", args=[self.bundle.pk])}">'
            f"{self.release_calendar_page.title}</option>",
            content,
        )
        self.assertInHTML(
            f'<option value="{reverse("bundles:preview", args=[self.bundle.pk, statistical_article.pk])}">'
            f"{statistical_article.display_title}</option>",
            content,
        )
        self.assertInHTML(
            f'<option value="{reverse("bundles:preview", args=[self.bundle.pk, methodology_article.pk])}">'
            f"{methodology_article.display_title}</option>",
            content,
        )
