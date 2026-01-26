from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from wagtail.models import GroupPagePermission, Page, PageLogEntry
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import create_bundle_viewer
from cms.datavis.tests.factories import TableDataFactory, make_table_block_value
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory
from cms.workflows.tests.utils import mark_page_as_ready_for_review


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

        self.client.force_login(editor)

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

    def test_download_creates_audit_log_entry(self):
        """Test that downloading a chart creates an audit log entry."""
        # Verify no log entries exist yet for this action
        initial_count = PageLogEntry.objects.filter(action="content.chart_download").count()

        # Download the chart
        response = self.client.get(self.get_download_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Verify audit log entry was created
        log_entry = PageLogEntry.objects.filter(action="content.chart_download").latest("timestamp")
        self.assertEqual(log_entry.object_id, self.article.pk)
        self.assertEqual(log_entry.data["chart_id"], "test-chart-id")
        self.assertEqual(log_entry.data["revision_id"], self.revision_id)

        # Verify count increased
        final_count = PageLogEntry.objects.filter(action="content.chart_download").count()
        self.assertEqual(final_count, initial_count + 1)

    def test_download_audit_log_mirrors_to_stdout(self):
        """Test that chart download audit log entry is mirrored to stdout."""
        with patch("cms.core.audit.audit_logger") as mock_logger:
            # Download the chart
            response = self.client.get(self.get_download_url())

            self.assertEqual(response.status_code, HTTPStatus.OK)

            # Verify audit logger was called
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args

            # Verify the log message
            self.assertEqual(call_args[0][0], "Audit event: %s")
            self.assertEqual(call_args[0][1], "content.chart_download")

            # Verify extra data
            extra = call_args[1]["extra"]
            self.assertEqual(extra["event"], "content.chart_download")
            self.assertEqual(extra["object_id"], self.article.pk)
            self.assertEqual(extra["data"]["chart_id"], "test-chart-id")
            self.assertEqual(extra["data"]["revision_id"], self.revision_id)
            self.assertIn("timestamp", extra)


class RevisionChartDownloadBundlePermissionsTestCase(WagtailTestUtils, TestCase):
    """Test bundle preview permissions for RevisionChartDownloadView.

    Bundle viewers (users with view_bundle permission) should be able to download
    chart CSVs from pages in bundles they can preview, even without page edit/publish
    permissions. The page must be in a previewable workflow state (GroupReviewTask or
    ReadyToPublishGroupTask).
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

        # Put the article in a previewable workflow state
        mark_page_as_ready_for_review(cls.article)

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

    def test_bundle_viewer_denied_when_page_not_in_previewable_workflow_state(self):
        """Test that bundle viewer cannot download when page is not in a previewable workflow state.

        Note: The test setup puts the page in a previewable state, so we cancel it here
        to test the denial scenario.
        """
        viewer = create_bundle_viewer()
        viewer.teams.add(self.preview_team)

        # Cancel the workflow to remove the page from the previewable state
        workflow_state = self.article.current_workflow_state
        workflow_state.cancel(user=viewer)

        self.client.force_login(viewer)
        response = self.client.get(self.get_download_url(), follow=True)

        # Permission denied redirects with message (Wagtail standard behavior)
        self.assertContains(response, "Sorry, you do not have permission to access this area.")


class RevisionTableDownloadViewTestCase(WagtailTestUtils, TestCase):
    """Test RevisionTableDownloadView for downloading tables from page revisions."""

    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.article = StatisticalArticlePageFactory(parent=cls.series)
        cls.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Table Section",
                    "content": [
                        {
                            "type": "table",
                            "value": make_table_block_value(
                                title="Test Table Title",
                                caption="Table caption",
                                headers=[["Year", "Value"]],
                                rows=[["2020", "100"], ["2021", "150"]],
                            ),
                            "id": "test-table-id",
                        }
                    ],
                },
            }
        ]
        cls.article.save_revision().publish()
        cls.revision_id = cls.article.latest_revision_id

    def setUp(self):
        self.login()

    def get_download_url(self, page_id=None, revision_id=None, table_id="test-table-id"):
        """Helper to build the download URL."""
        return reverse(
            "articles:revision_table_download",
            kwargs={
                "page_id": page_id or self.article.pk,
                "revision_id": revision_id or self.revision_id,
                "table_id": table_id,
            },
        )

    def test_get_with_valid_table_returns_csv(self):
        """Test successful table download for superuser."""
        response = self.client.get(self.get_download_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("test-table-title.csv", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        self.assertIn("Year", content)
        self.assertIn("2020", content)
        self.assertIn("100", content)

    def test_get_with_missing_table_returns_404(self):
        """Test 404 when table_id does not exist in the revision."""
        response = self.client.get(self.get_download_url(table_id="nonexistent-table"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_get_with_invalid_data_returns_404(self):
        """Test 404 when table has no data."""
        self.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Empty Table Section",
                    "content": [
                        {
                            "type": "table",
                            "value": make_table_block_value(title="Empty Table", headers=[], rows=[]),
                            "id": "empty-table-id",
                        }
                    ],
                },
            }
        ]
        draft_revision = self.article.save_revision()

        response = self.client.get(self.get_download_url(revision_id=draft_revision.pk, table_id="empty-table-id"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_permission_required(self):
        """Test table download is denied for anonymous users."""
        self.client.logout()

        response = self.client.get(self.get_download_url())
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("/admin/login/", response.url)

    def test_bundle_preview_permission_allows_access(self):
        """Test that a bundle viewer can download table CSVs from pages in their bundle."""
        mark_page_as_ready_for_review(self.article)

        preview_team = TeamFactory(name="Preview Team")
        bundle = BundleFactory(in_review=True)
        BundlePageFactory(parent=bundle, page=self.article)
        BundleTeam.objects.create(parent=bundle, team=preview_team)

        viewer = create_bundle_viewer()
        viewer.teams.add(preview_team)

        self.client.force_login(viewer)
        response = self.client.get(self.get_download_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_download_audit_log_mirrors_to_stdout(self):
        """Test that table download audit log entry is mirrored to stdout."""
        with patch("cms.core.audit.audit_logger") as mock_logger:
            response = self.client.get(self.get_download_url())

            self.assertEqual(response.status_code, HTTPStatus.OK)

            # Verify audit logger was called
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args

            # Verify the log message
            self.assertEqual(call_args[0][0], "Audit event: %s")
            self.assertEqual(call_args[0][1], "content.table_download")

            # Verify extra data
            extra = call_args[1]["extra"]
            self.assertEqual(extra["event"], "content.table_download")
            self.assertEqual(extra["object_id"], self.article.pk)
            self.assertEqual(extra["data"]["table_id"], "test-table-id")
            self.assertEqual(extra["data"]["revision_id"], self.revision_id)
            self.assertIn("timestamp", extra)


class ChartAndTableDownloadTestCase(WagtailTestUtils, TestCase):
    """Test downloading both chart and table CSVs from the same article."""

    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.table_data = TableDataFactory(
            table_data=[
                ["Category", "Chart Value 1", "Chart Value 2"],
                ["2020", "100", "150"],
                ["2021", "120", "180"],
            ]
        )
        cls.article = StatisticalArticlePageFactory(parent=cls.series)
        cls.article.content = [
            {
                "type": "section",
                "value": {
                    "title": "Mixed Content Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Population Growth Chart",
                                "subtitle": "Annual growth rates",
                                "theme": "primary",
                                "table": cls.table_data,
                            },
                            "id": "population-chart",
                        },
                        {
                            "type": "table",
                            "value": make_table_block_value(
                                title="Regional Statistics Table",
                                caption="Regional breakdown",
                                headers=[["Region", "Population"]],
                                rows=[["North", "5000000"], ["South", "7000000"]],
                            ),
                            "id": "regional-table",
                        },
                    ],
                },
            }
        ]
        cls.article.save_revision().publish()
        cls.revision_id = cls.article.latest_revision_id

    def setUp(self):
        self.login()

    def get_chart_download_url(self, chart_id="population-chart"):
        """Helper to build the chart download URL."""
        return reverse(
            "articles:revision_chart_download",
            kwargs={
                "page_id": self.article.pk,
                "revision_id": self.revision_id,
                "chart_id": chart_id,
            },
        )

    def get_table_download_url(self, table_id="regional-table"):
        """Helper to build the table download URL."""
        return reverse(
            "articles:revision_table_download",
            kwargs={
                "page_id": self.article.pk,
                "revision_id": self.revision_id,
                "table_id": table_id,
            },
        )

    def test_chart_csv_download_has_correct_data(self):
        """Test chart CSV contains chart-specific data."""
        response = self.client.get(self.get_chart_download_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("population-growth-chart.csv", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        # Verify chart data is present
        self.assertIn("Category", content)
        self.assertIn("Chart Value 1", content)
        self.assertIn("Chart Value 2", content)
        self.assertIn("2020", content)
        self.assertIn("100", content)
        self.assertIn("150", content)

        # Verify table data is NOT in chart CSV
        self.assertNotIn("Region", content)
        self.assertNotIn("North", content)
        self.assertNotIn("5000000", content)

    def test_table_csv_download_has_correct_data(self):
        """Test table CSV contains table-specific data."""
        response = self.client.get(self.get_table_download_url())

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("regional-statistics-table.csv", response["Content-Disposition"])

        content = response.content.decode("utf-8")
        # Verify table data is present
        self.assertIn("Region", content)
        self.assertIn("Population", content)
        self.assertIn("North", content)
        self.assertIn("South", content)
        self.assertIn("5000000", content)
        self.assertIn("7000000", content)

        # Verify chart data is NOT in table CSV
        self.assertNotIn("Category", content)
        self.assertNotIn("Chart Value 1", content)
        self.assertNotIn("2020", content)

    def test_both_downloads_work_independently(self):
        """Test that both chart and table can be downloaded without interference."""
        # Download chart first
        chart_response = self.client.get(self.get_chart_download_url())
        self.assertEqual(chart_response.status_code, HTTPStatus.OK)
        chart_content = chart_response.content.decode("utf-8")

        # Download table second
        table_response = self.client.get(self.get_table_download_url())
        self.assertEqual(table_response.status_code, HTTPStatus.OK)
        table_content = table_response.content.decode("utf-8")

        # Verify both have distinct content
        self.assertNotEqual(chart_content, table_content)
        self.assertIn("Chart Value 1", chart_content)
        self.assertIn("Region", table_content)

        # Download chart again to ensure no state issues
        chart_response_2 = self.client.get(self.get_chart_download_url())
        self.assertEqual(chart_response_2.status_code, HTTPStatus.OK)
        chart_content_2 = chart_response_2.content.decode("utf-8")

        # Verify second chart download matches first
        self.assertEqual(chart_content, chart_content_2)

        # Dwonload table again to ensure no state issues
        table_response_2 = self.client.get(self.get_table_download_url())
        self.assertEqual(table_response_2.status_code, HTTPStatus.OK)
        table_content_2 = table_response_2.content.decode("utf-8")

        # Verify second table download matches first
        self.assertEqual(table_content, table_content_2)
