from http import HTTPStatus

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from wagtail.models import GroupPagePermission, Page
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import create_bundle_viewer
from cms.datavis.tests.factories import TableDataFactory
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory


class RevisionChartDownloadViewTestCase(WagtailTestUtils, TestCase):
    """Test RevisionChartDownloadView for downloading charts from page revisions."""

    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.table_data = TableDataFactory(
            table_data=[
                ["Category", "Value 1", "Value 2"],
                ["2020", "100", "150"],
                ["2021", "120", "180"],
            ]
        )
        cls.article = StatisticalArticlePageFactory(parent=cls.series)
        cls.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Chart Title",
                                "subtitle": "Chart subtitle",
                                "theme": "primary",
                                "table": cls.table_data,
                            },
                            "id": "test-chart-id",
                        }
                    ],
                },
            }
        ]
        cls.article.save_revision().publish()
        cls.revision_id = cls.article.latest_revision_id

    def setUp(self):
        self.login()

    def get_download_url(self, page_id=None, revision_id=None, chart_id="test-chart-id"):
        """Helper to build the download URL."""
        return reverse(
            "articles:revision_chart_download",
            kwargs={
                "page_id": page_id or self.article.pk,
                "revision_id": revision_id or self.revision_id,
                "chart_id": chart_id,
            },
        )

    def test_download_success_for_superuser(self):
        """Test successful chart download for superuser."""
        response = self.client.get(self.get_download_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("test-chart-title.csv", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        self.assertIn("Category", content)
        self.assertIn("2020", content)
        self.assertIn("100", content)

    def test_download_success_for_user_with_edit_permission(self):
        """Test chart download for user with edit permission on the page."""
        # Create a group with edit permission on the page
        group, _ = Group.objects.get_or_create(name="Editors")
        GroupPagePermission.objects.create(
            group=group,
            page=Page.objects.get(pk=self.article.pk),
            permission_type="change",
        )

        # Create non-superuser with admin access and add to group
        editor = UserFactory(username="editor", access_admin=True)
        editor.groups.add(group)

        self.client.logout()
        self.client.force_login(editor)

        response = self.client.get(self.get_download_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_download_success_for_user_with_publish_permission(self):
        """Test chart download for user with publish permission on the page."""
        # Create a group with publish permission on the page
        group, _ = Group.objects.get_or_create(name="Publishers")
        GroupPagePermission.objects.create(
            group=group,
            page=Page.objects.get(pk=self.article.pk),
            permission_type="publish",
        )

        # Create non-superuser with admin access and add to group
        publisher = UserFactory(username="publisher", access_admin=True)
        publisher.groups.add(group)

        self.client.logout()
        self.client.force_login(publisher)

        response = self.client.get(self.get_download_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_download_denied_for_anonymous_user(self):
        """Test chart download is denied for anonymous users."""
        self.client.logout()

        response = self.client.get(self.get_download_url())
        # Should redirect to login
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("/admin/login/", response.url)

    def test_download_404_nonexistent_page(self):
        """Test 404 when page doesn't exist."""
        response = self.client.get(self.get_download_url(page_id=99999))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_404_nonexistent_revision(self):
        """Test 404 when revision doesn't exist."""
        response = self.client.get(self.get_download_url(revision_id=99999))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_404_nonexistent_chart(self):
        """Test 404 when chart_id doesn't exist in the revision."""
        response = self.client.get(self.get_download_url(chart_id="nonexistent-chart"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_from_draft_revision(self):
        """Test downloading chart from an unpublished draft revision."""
        # Create a new draft with different chart data
        draft_table_data = TableDataFactory(
            table_data=[
                ["Month", "Sales"],
                ["January", "500"],
                ["February", "750"],
            ]
        )
        self.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Draft Chart",
                                "subtitle": "Draft subtitle",
                                "theme": "primary",
                                "table": draft_table_data,
                            },
                            "id": "draft-chart-id",
                        }
                    ],
                },
            }
        ]
        # Save as draft (don't publish)
        draft_revision = self.article.save_revision()

        # Download from the draft revision
        response = self.client.get(self.get_download_url(revision_id=draft_revision.pk, chart_id="draft-chart-id"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("draft-chart.csv", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        self.assertIn("Month", content)
        self.assertIn("January", content)
        self.assertIn("500", content)

    def test_download_from_old_revision(self):
        """Test downloading chart from an older revision after page has been updated."""
        old_revision_id = self.revision_id

        # Update the article with new chart data
        new_table_data = TableDataFactory(
            table_data=[
                ["Region", "Population"],
                ["London", "9000000"],
            ]
        )
        self.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Updated Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": new_table_data,
                            },
                            "id": "updated-chart-id",
                        }
                    ],
                },
            }
        ]
        self.article.save_revision().publish()

        # Download from the old revision should still return the original data
        response = self.client.get(self.get_download_url(revision_id=old_revision_id))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode("utf-8")
        self.assertIn("Category", content)
        self.assertIn("2020", content)
        # Should NOT contain new data
        self.assertNotIn("Region", content)
        self.assertNotIn("London", content)


class RevisionChartDownloadBundlePermissionsTestCase(WagtailTestUtils, TestCase):
    """Test bundle preview permissions for RevisionChartDownloadView.

    Bundle viewers (users with view_bundle permission) should be able to download
    chart CSVs from pages in bundles they can preview, even without page edit/publish
    permissions.
    """

    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.table_data = TableDataFactory(
            table_data=[
                ["Category", "Value"],
                ["2020", "100"],
            ]
        )
        cls.article = StatisticalArticlePageFactory(parent=cls.series)
        cls.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Chart",
                                "subtitle": "",
                                "theme": "primary",
                                "table": cls.table_data,
                            },
                            "id": "test-chart-id",
                        }
                    ],
                },
            }
        ]
        cls.article.save_revision().publish()
        cls.revision_id = cls.article.latest_revision_id

        # Create preview team and bundle
        cls.preview_team = TeamFactory(name="Preview Team")
        cls.bundle = BundleFactory(in_review=True)
        BundlePageFactory(parent=cls.bundle, page=cls.article)
        BundleTeam.objects.create(parent=cls.bundle, team=cls.preview_team)

    def get_download_url(self):
        """Helper to build the download URL."""
        # We do this because we use factories to create the pages
        return reverse(
            "articles:revision_chart_download",
            kwargs={
                "page_id": self.article.pk,
                "revision_id": self.revision_id,
                "chart_id": "test-chart-id",
            },
        )

    def test_bundle_viewer_can_download_when_in_preview_team(self):
        """Test that a bundle viewer in the correct team can download chart CSV."""
        viewer = create_bundle_viewer()
        viewer.teams.add(self.preview_team)

        self.client.force_login(viewer)
        response = self.client.get(self.get_download_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_bundle_viewer_denied_when_not_in_preview_team(self):
        """Test that a bundle viewer not in the bundle's team cannot download."""
        viewer = create_bundle_viewer()
        # Not adding viewer to preview_team

        self.client.force_login(viewer)
        response = self.client.get(self.get_download_url(), follow=True)

        # Permission denied redirects with message (Wagtail standard behavior)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_bundle_viewer_denied_when_bundle_not_in_previewable_status(self):
        """Test that bundle viewer cannot download when bundle is in draft status."""
        viewer = create_bundle_viewer()
        viewer.teams.add(self.preview_team)

        # Change bundle to draft status (not previewable)
        self.bundle.status = BundleStatus.DRAFT
        self.bundle.save(update_fields=["status"])

        self.client.force_login(viewer)
        response = self.client.get(self.get_download_url(), follow=True)

        # Permission denied redirects with message (Wagtail standard behavior)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_bundle_viewer_denied_when_team_is_inactive(self):
        """Test that bundle viewer in inactive team cannot download."""
        viewer = create_bundle_viewer()

        # Create inactive team and add to bundle
        inactive_team = TeamFactory(name="Inactive Team", is_active=False)
        BundleTeam.objects.create(parent=self.bundle, team=inactive_team)
        viewer.teams.add(inactive_team)

        self.client.force_login(viewer)
        response = self.client.get(self.get_download_url(), follow=True)

        # Permission denied redirects with message (Wagtail standard behavior)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")

    def test_user_without_bundle_permission_denied(self):
        """Test that a user with only admin access but no bundle permissions is denied."""
        user = UserFactory(access_admin=True)
        # User has basic admin access but no bundle view permission and no page permissions

        self.client.force_login(user)
        response = self.client.get(self.get_download_url(), follow=True)

        # Permission denied redirects with message (Wagtail standard behavior)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")
