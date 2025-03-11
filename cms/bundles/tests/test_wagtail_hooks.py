from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.models import Bundle
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import grant_all_bundle_permissions, grant_all_page_permissions, make_bundle_viewer
from cms.bundles.wagtail_hooks import LatestBundlesPanel
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.users.tests.factories import GroupFactory, UserFactory


class WagtailHooksTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.publishing_group = GroupFactory(name="Publishing Officers", access_admin=True)
        grant_all_page_permissions(cls.publishing_group)
        grant_all_bundle_permissions(cls.publishing_group)
        cls.publishing_officer = UserFactory(username="publishing_officer")
        cls.publishing_officer.groups.add(cls.publishing_group)

        cls.bundle_viewer = UserFactory(username="bundle.viewer", access_admin=True)
        make_bundle_viewer(cls.bundle_viewer)

        # a regular generic_user that can only access the Wagtail admin
        cls.generic_user = UserFactory(username="generic.generic_user", access_admin=True)

        cls.bundle_index_url = reverse("bundle:index")
        cls.bundle_add_url = reverse("bundle:add")
        cls.dashboard_url = reverse("wagtailadmin_home")

        cls.pending_bundle = BundleFactory(name="Pending Bundle", created_by=cls.bundle_viewer)
        cls.in_review_bundle = BundleFactory(in_review=True, name="Bundle In review", created_by=cls.superuser)
        cls.approved_bundle = BundleFactory(name="Approved Bundle", approved=True, created_by=cls.publishing_officer)
        cls.released_bundle = BundleFactory(released=True, name="Released Bundle")

        cls.statistical_article_page = StatisticalArticlePageFactory(title="November 2024", parent__title="PSF")
        cls.article_edit_url = reverse("wagtailadmin_pages:edit", args=[cls.statistical_article_page.id])
        cls.article_parent_url = reverse("wagtailadmin_explore", args=[cls.statistical_article_page.get_parent().id])
        cls.add_to_bundle_url = reverse("bundles:add_to_bundle", args=[cls.statistical_article_page.id])

    def test_latest_bundles_panel_is_shown(self):
        """Checks that the latest bundles dashboard panel is shown to relevant users."""
        cases = [
            (self.generic_user, 0),
            (self.bundle_viewer, 1),
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
        self.assertIs(panels[0].permission_policy.model, Bundle)

        self.assertContains(response, self.bundle_add_url)
        self.assertContains(response, self.bundle_index_url)
        self.assertContains(response, "View all bundles")

        for bundle in [self.pending_bundle, self.in_review_bundle, self.approved_bundle]:
            self.assertContains(response, bundle.name)
            self.assertContains(response, bundle.created_by.get_full_name())
            self.assertContains(response, bundle.status.label)
        self.assertNotContains(response, self.released_bundle.status.label)

    def test_preset_golive_date__happy_path(self):
        """Checks we update the page go live at on page edit , if in the future and doesn't match the bundle date."""
        self.client.force_login(self.publishing_officer)

        BundlePageFactory(parent=self.pending_bundle, page=self.statistical_article_page)

        # set to +15 minutes as the check is on now() < scheduled_publication_date & page.go_live_at != scheduled
        nowish = timezone.now() + timedelta(minutes=15)
        bundle_date = nowish + timedelta(hours=1)

        cases = [
            # bundle publication date, page go_live_at, expected change, case description
            (nowish - timedelta(hours=1), nowish, nowish, "Go live unchanged as bundle date in the past"),
            (bundle_date, bundle_date, bundle_date, "Go live unchanged as it matches bundle"),
            (bundle_date, nowish + timedelta(days=1), bundle_date, "Go live updated to match bundle"),
        ]
        for bundle_publication_date, go_live_at, expected, case in cases:
            with self.subTest(go_live_at=go_live_at, expected=expected, case=case):
                self.pending_bundle.publication_date = bundle_publication_date
                self.pending_bundle.save(update_fields=["publication_date"])

                self.statistical_article_page.go_live_at = go_live_at
                self.statistical_article_page.save(update_fields=["go_live_at"])

                response = self.client.get(self.article_edit_url)
                context_page = response.context["page"]
                self.assertEqual(context_page.go_live_at, expected)

    def test_preset_golive_date__updates_only_if_page_in_active_bundle(self):
        """Checks the go live at update only happens if the page is in active bundle."""
        self.client.force_login(self.publishing_officer)

        nowish = timezone.now() + timedelta(minutes=15)
        self.pending_bundle.publication_date = nowish + timedelta(hours=1)
        self.pending_bundle.save(update_fields=["publication_date"])

        self.statistical_article_page.go_live_at = nowish
        self.statistical_article_page.save(update_fields=["go_live_at"])

        response = self.client.get(self.article_edit_url)
        context_page = response.context["page"]
        self.assertEqual(context_page.go_live_at, nowish)

    def test_preset_golive_date__updates_only_if_page_is_bundleable(self):
        """Checks the go live at change happens only for bundleable pages.."""
        self.client.force_login(self.publishing_officer)

        nowish = timezone.now() + timedelta(minutes=15)
        self.pending_bundle.publication_date = nowish + timedelta(hours=1)
        self.pending_bundle.save(update_fields=["publication_date"])

        page = ReleaseCalendarPageFactory()
        page.go_live_at = nowish
        page.save(update_fields=["go_live_at"])

        response = self.client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))
        context_page = response.context["page"]
        self.assertEqual(context_page.go_live_at, nowish)

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
        BundlePageFactory(parent=self.pending_bundle, page=self.statistical_article_page)

        self.client.force_login(self.publishing_officer)

        for url, context in contexts:
            with self.subTest(msg=f"Non-bundleable page - {context}"):
                response = self.client.get(url)
                self.assertNotContains(response, "Add to Bundle")
                self.assertNotContains(response, self.add_to_bundle_url)
