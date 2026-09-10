from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.datavis.models import RenderedChartImage
from cms.datavis.services import iter_chart_blocks
from cms.datavis.tests.test_services import make_export_response, make_page_with_chart
from cms.users.tests.factories import UserFactory


class ChartRenderOnSaveTests(TestCase):
    """Covers the save trigger: pre-rendering chart images whenever a revision is saved."""

    def test_save_revision_renders_and_persists_the_reference(self):
        page = make_page_with_chart()

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            mock_client_cls.return_value.create_chart.return_value = make_export_response()
            revision = page.save_revision()

        rendered_block = next(iter_chart_blocks(revision.as_object().content))
        self.assertIsInstance(rendered_block.value["rendered_chart_image"], RenderedChartImage)

    def test_second_save_revision_with_unchanged_config_does_not_call_the_exporter(self):
        page = make_page_with_chart()

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            mock_client_cls.return_value.create_chart.return_value = make_export_response()
            page.save_revision()

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            page.save_revision()

        mock_client_cls.return_value.create_chart.assert_not_called()
        self.assertEqual(RenderedChartImage.objects.count(), 1)

    def test_save_revision_succeeds_when_rendering_raises(self):
        page = make_page_with_chart()

        with (
            patch("cms.datavis.mixins.render_chart_blocks", side_effect=RuntimeError("boom")),
            self.assertLogs("cms.datavis.mixins", level="ERROR"),
        ):
            revision = page.save_revision()

        self.assertEqual(page.revisions.count(), 1)
        rendered_block = next(iter_chart_blocks(revision.as_object().content))
        self.assertIsNone(rendered_block.value["rendered_chart_image"])

    def test_page_without_chart_blocks_does_not_reach_the_exporter(self):
        page = StatisticalArticlePageFactory()

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            page.save_revision()

        mock_client_cls.assert_not_called()

    def test_preview_does_not_render(self):
        """The live preview panel POSTs the whole form on every edit, and its validation must
        not reach the exporter.
        """
        page = make_page_with_chart()
        self.client.force_login(UserFactory(is_superuser=True, access_admin=True))
        data = nested_form_data(
            {
                "title": page.title,
                "slug": page.slug,
                "summary": rich_text(page.summary),
                "main_points_summary": rich_text(page.main_points_summary),
                "release_date": page.release_date,
                "content": streamfield(
                    [("section", {"title": "Test", "content": streamfield([("rich_text", rich_text("text"))])})]
                ),
                "datasets": streamfield([]),
                "dataset_sorting": "AS_SHOWN",
                "corrections": streamfield([]),
                "notices": streamfield([]),
                "headline_figures": streamfield([]),
                "featured_chart": streamfield([]),
            }
        )

        with (
            patch("cms.datavis.mixins.render_chart_blocks") as mock_mixin_render,
            patch("cms.core.forms.render_chart_blocks") as mock_form_render,
        ):
            response = self.client.post(reverse("wagtailadmin_pages:preview_on_edit", args=[page.pk]), data)

        self.assertEqual(response.status_code, 200)
        mock_mixin_render.assert_not_called()
        mock_form_render.assert_not_called()
