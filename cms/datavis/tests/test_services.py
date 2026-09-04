import uuid
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.datavis.clients.chart_exporter import (
    ChartExporterMalformedRequest,
    ChartExporterUnavailable,
    ChartObjectResponse,
)
from cms.datavis.models import RenderedChartImage
from cms.datavis.services import (
    GENERIC_RENDER_ERROR,
    UNAVAILABLE_RENDER_ERROR,
    iter_chart_blocks,
    render_chart_blocks,
    render_charts_for_page,
)
from cms.datavis.tests.factories import RenderedChartImageFactory, TableDataFactory
from cms.datavis.utils import hash_chart_config


def chart_block(*, image_pk=None, title="Test Chart"):
    return {
        "type": "line_chart",
        "id": str(uuid.uuid4()),
        "value": {
            "title": title,
            "audio_description": "Description",
            "table": TableDataFactory(),
            "theme": "primary",
            "rendered_chart_image": image_pk,
        },
    }


def make_page_with_chart():
    """Create and persist a StatisticalArticlePage with a single chart block in its content.

    The chart must be nested in a section: SectionStoryBlock only permits `section` at the top
    level, and Wagtail silently drops any other block type when loading the stream.
    """
    page = StatisticalArticlePageFactory()
    page.content = [
        {
            "type": "section",
            "id": str(uuid.uuid4()),
            "value": {"title": "Section", "content": [chart_block()]},
        }
    ]
    page.save()
    return StatisticalArticlePage.objects.get(pk=page.pk)


def make_export_response(**overrides):
    defaults = {
        "id": str(uuid.uuid4()),
        "created_at": "2026-01-01T00:00:00Z",
        "bucket": settings.AWS_STORAGE_BUCKET_NAME,
        "key": "charts/abc.png",
        "content_type": "image/png",
        "size_bytes": 100,
        "width": 10,
        "height": 10,
    }
    defaults.update(overrides)
    return ChartObjectResponse(**defaults)


class RenderChartBlocksTests(TestCase):
    def setUp(self):
        self.page = make_page_with_chart()
        self.block = next(iter_chart_blocks(self.page.content))

    @patch("cms.datavis.services.ChartExporterClient")
    def test_creates_and_attaches_image_on_success(self, mock_client_cls):
        mock_client_cls.return_value.create_chart.return_value = make_export_response()

        results = render_chart_blocks([self.block])

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].changed)
        self.assertIsNone(results[0].error)
        self.assertIsInstance(self.block.value["rendered_chart_image"], RenderedChartImage)

    def test_skips_when_hash_matches_currently_attached_image(self):
        config_hash = hash_chart_config(self.block.block.get_export_config(self.block.value))
        existing = RenderedChartImageFactory(config_hash=config_hash)
        self.block.value["rendered_chart_image"] = existing

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            results = render_chart_blocks([self.block])

        mock_client_cls.return_value.create_chart.assert_not_called()
        self.assertFalse(results[0].changed)
        self.assertIsNone(results[0].error)
        self.assertEqual(self.block.value["rendered_chart_image"], existing)

    @patch("cms.datavis.services.ChartExporterClient")
    def test_malformed_request_produces_generic_error_and_leaves_image_unset(self, mock_client_cls):
        mock_client_cls.return_value.create_chart.side_effect = ChartExporterMalformedRequest("bad")

        results = render_chart_blocks([self.block])

        self.assertFalse(results[0].changed)
        self.assertEqual(results[0].error, GENERIC_RENDER_ERROR)
        self.assertIsNone(self.block.value["rendered_chart_image"])

    @patch("cms.datavis.services.ChartExporterClient")
    def test_unavailable_produces_retry_error(self, mock_client_cls):
        mock_client_cls.return_value.create_chart.side_effect = ChartExporterUnavailable("down")

        results = render_chart_blocks([self.block])

        self.assertFalse(results[0].changed)
        self.assertEqual(results[0].error, UNAVAILABLE_RENDER_ERROR)

    def test_empty_blocks_returns_empty_list_without_creating_a_client(self):
        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            results = render_chart_blocks([])

        self.assertEqual(results, [])
        mock_client_cls.assert_not_called()


class RenderChartsForPageTests(TestCase):
    def test_saves_a_new_revision_when_a_chart_is_rendered(self):
        page = make_page_with_chart()
        self.assertEqual(page.revisions.count(), 0)

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            mock_client_cls.return_value.create_chart.return_value = make_export_response()
            results = render_charts_for_page(page)

        self.assertTrue(any(result.changed for result in results))
        self.assertEqual(page.revisions.count(), 1)
        revision_content = page.get_latest_revision().as_object().content
        rendered_block = next(iter_chart_blocks(revision_content))
        self.assertIsInstance(rendered_block.value["rendered_chart_image"], RenderedChartImage)

    def test_second_render_with_unchanged_config_is_skipped(self):
        page = make_page_with_chart()

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            mock_client_cls.return_value.create_chart.return_value = make_export_response()
            render_charts_for_page(page)

        self.assertEqual(page.revisions.count(), 1)

        with patch("cms.datavis.services.ChartExporterClient") as mock_client_cls:
            results = render_charts_for_page(page)

        mock_client_cls.return_value.create_chart.assert_not_called()
        self.assertFalse(any(result.changed for result in results))
        self.assertEqual(page.revisions.count(), 1)
