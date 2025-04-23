from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import (
    create_bundle_manager,
    create_bundle_viewer,
)
from cms.bundles.wagtail_hooks import BundlesInReviewPanel, LatestBundlesPanel
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.teams.models import Team
from cms.users.tests.factories import UserFactory


class WagtailHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.publishing_officer = create_bundle_manager()
        cls.bundle_viewer = create_bundle_viewer()

        # a regular generic_user that can only access the Wagtail admin
        cls.generic_user = UserFactory(username="generic.generic_user", access_admin=True)

        cls.bundle_index_url = reverse("bundle:index")
        cls.bundle_add_url = reverse("bundle:add")
        cls.dashboard_url = reverse("wagtailadmin_home")

        cls.draft_bundle = BundleFactory(name="Draft Bundle", created_by=cls.bundle_viewer)
        cls.in_review_bundle = BundleFactory(in_review=True, name="Bundle In review", created_by=cls.superuser)
        cls.approved_bundle = BundleFactory(name="Approved Bundle", approved=True, created_by=cls.publishing_officer)
        cls.published_bundle = BundleFactory(published=True, name="Published Bundle")

        cls.statistical_article_page = StatisticalArticlePageFactory(title="November 2024", parent__title="PSF")
        cls.article_edit_url = reverse("wagtailadmin_pages:edit", args=[cls.statistical_article_page.id])
        cls.article_parent_url = reverse("wagtailadmin_explore", args=[cls.statistical_article_page.get_parent().id])
        cls.add_to_bundle_url = reverse("bundles:add_to_bundle", args=[cls.statistical_article_page.id])

        cls.preview_team = Team.objects.create(identifier="foo", name="Preview team")
        BundleTeam.objects.create(parent=cls.in_review_bundle, team=cls.preview_team)

    def test_latest_bundles_panel_is_shown(self):
        """Checks that the latest bundles dashboard panel is shown to relevant users."""
        cases = [
            (self.generic_user, 0),
            (self.bundle_viewer, 0),
            (self.publishing_officer, 1),
            (self.superuser, 1),
        ]
        for user, shown in cases:
            with self.subTest(user=user.username, shown=shown):
                self.client.force_login(user)
                response = self.client.get(self.dashboard_url)
                self.assertContains(response, "Latest active bundles", count=shown)

    def test_latest_bundles_panel_content(self):
        """Checks that the latest bundles dashboard panel content only shows active bundles."""
        self.client.force_login(self.publishing_officer)
        response = self.client.get(self.dashboard_url)

        panels = response.context["panels"]
        self.assertIsInstance(panels[0], LatestBundlesPanel)
        self.assertTrue(panels[0].is_shown)
        self.assertIs(panels[0].permission_policy.model, Bundle)

        self.assertContains(response, self.bundle_add_url)
        self.assertContains(response, self.bundle_index_url)
        self.assertContains(response, "View all bundles")

        for bundle in [self.draft_bundle, self.in_review_bundle, self.approved_bundle]:
            self.assertContains(response, bundle.name)
            self.assertContains(response, bundle.created_by.get_full_name())
            self.assertContains(response, bundle.status.label)
        self.assertNotContains(response, self.published_bundle.status.label)

    def test_bundle_to_preview_panel_is_shown(self):
        cases = [
            (self.generic_user, 0),
            (self.bundle_viewer, 1),
            (self.publishing_officer, 0),
            (self.superuser, 1),
        ]
        for user, shown in cases:
            with self.subTest(user=user.username, shown=shown):
                self.client.force_login(user)
                response = self.client.get(self.dashboard_url)
                self.assertContains(response, "Bundles ready for preview", count=shown)

    def test_bundles_to_preview_panel_content(self):
        self.client.force_login(self.bundle_viewer)
        response = self.client.get(self.dashboard_url)

        panels = response.context["panels"]
        self.assertIsInstance(panels[0], LatestBundlesPanel)
        self.assertFalse(panels[0].is_shown)

        self.assertIsInstance(panels[1], BundlesInReviewPanel)
        self.assertTrue(panels[1].is_shown)
        self.assertIs(panels[1].permission_policy.model, Bundle)

        self.assertContains(response, "There are currently no bundles for preview.")

        self.bundle_viewer.teams.add(self.preview_team)
        BundleTeam.objects.create(parent=self.approved_bundle, team=self.preview_team)

        response = self.client.get(self.dashboard_url)
        self.assertNotContains(response, "There are currently no bundles for preview.")
        self.assertNotContains(response, self.bundle_add_url)
        self.assertContains(response, reverse("bundle:inspect", args=[self.in_review_bundle.pk]))

        self.assertContains(response, self.in_review_bundle.name)
        self.assertContains(response, self.in_review_bundle.created_by.get_full_name())
        self.assertNotContains(response, self.in_review_bundle.status.label)

        self.assertContains(response, self.approved_bundle.name)
        self.assertNotContains(response, self.approved_bundle.status.label)

        self.assertNotContains(response, self.draft_bundle.name)
        self.assertNotContains(response, self.published_bundle.name)

    def test_add_to_bundle_buttons(self):
        """Tests that the 'Add to Bundle' button appears in appropriate contexts."""
        # Test both header and listing contexts
        contexts = [(self.article_edit_url, "header"), (self.article_parent_url, "listing")]

        for user in [self.generic_user, self.bundle_viewer]:
            for url, context in contexts:
                with self.subTest(user=user.username, context=context):
                    self.client.force_login(user)
                    response = self.client.get(url, follow=True)
                    self.assertEqual(response.context["request"].path, reverse("wagtailadmin_home"))
                    self.assertContains(response, "Sorry, you do not have permission to access this area.")

        cases_with_access = [
            (self.publishing_officer, 1),  # Has all permissions, should see button
            (self.superuser, 1),  # Has all permissions, should see button
        ]
        for user, expected_count in cases_with_access:
            for url, context in contexts:
                with self.subTest(user=user.username, context=context, expected=expected_count):
                    self.client.force_login(user)
                    response = self.client.get(url)

                    # Check if button appears in response
                    self.assertContains(response, "Add to Bundle", count=expected_count)
                    self.assertContains(response, "boxes-stacked")  # icon name
                    self.assertContains(response, self.add_to_bundle_url)

    def test_add_to_bundle_buttons__doesnt_show_for_pages_in_bundle(self):
        """Checks that the button doesn't appear for pages already in a bundle."""
        release_calendar_page = ReleaseCalendarPageFactory()
        contexts = [
            (reverse("wagtailadmin_pages:edit", args=[release_calendar_page.id]), "header"),
            (reverse("wagtailadmin_explore", args=[release_calendar_page.get_parent().id]), "listing"),
        ]
        BundlePageFactory(parent=self.draft_bundle, page=self.statistical_article_page)

        self.client.force_login(self.publishing_officer)

        for url, context in contexts:
            with self.subTest(msg=f"Non-bundleable page - {context}"):
                response = self.client.get(url)
                self.assertNotContains(response, "Add to Bundle")
                self.assertNotContains(response, self.add_to_bundle_url)
