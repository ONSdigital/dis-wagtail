from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from wagtail.models import ModelLogEntry
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.admin_forms import AddToBundleForm
from cms.bundles.enums import PREVIEWABLE_BUNDLE_STATUSES, BundleStatus
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import (
    create_bundle_manager,
    create_bundle_viewer,
)
from cms.home.models import HomePage
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_to_publish


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
        for status in [BundleStatus.PENDING, BundleStatus.RELEASED]:
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
