import time
import unittest
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings

from cms.articles.models import StatisticalArticlePage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.datavis.clients.chart_exporter import (
    ChartExporterClient,
    ChartExporterError,
    ChartExporterMalformedRequest,
    ChartExporterUnavailable,
    ChartObjectResponse,
)
from cms.datavis.models import RenderedChartImage
from cms.datavis.services import (
    GENERIC_RENDER_ERROR,
    UNAVAILABLE_RENDER_ERROR,
    ChartRenderResult,
    iter_chart_blocks,
    render_chart_blocks,
)
from cms.datavis.tests.chart_exporter_mock import ERRORS, PNG
from cms.datavis.tests.test_services import chart_block, make_page_with_chart
from cms.datavis.tests.utils import mock_chart_exporter
from cms.users.tests.factories import UserFactory

CHART_CONFIG = {"chartType": "column", "series": []}


def make_chart_blocks(count):
    """Create a StatisticalArticlePage with ``count`` charts in one section, and return their blocks."""
    page = StatisticalArticlePageFactory()
    page.content = [
        {
            "type": "section",
            "id": str(uuid.uuid4()),
            "value": {"title": "Section", "content": [chart_block(title=f"Chart {n}") for n in range(count)]},
        }
    ]
    page.save()
    return list(iter_chart_blocks(StatisticalArticlePage.objects.get(pk=page.pk).content))


class ChartExporterMockTestCase(TestCase):
    """Points the chart exporter client at a mock exporter, so tests make real HTTP requests."""

    @classmethod
    def setUpClass(cls):
        cls.chart_exporter = cls.enterClassContext(mock_chart_exporter())
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.chart_exporter.reset()


@override_settings(CMS_CHART_EXPORTER_API_MAX_RETRIES=2)
class ChartExporterClientMockTests(ChartExporterMockTestCase):
    def test_create_chart_success(self):
        result = ChartExporterClient().create_chart(CHART_CONFIG)

        self.assertIsInstance(result, ChartObjectResponse)
        self.assertEqual(str(uuid.UUID(result.id)), result.id)
        self.assertEqual(result.bucket, settings.AWS_STORAGE_BUCKET_NAME)
        self.assertEqual(result.key, f"charts/{result.id}.png")
        self.assertEqual((result.width, result.height), (1200, 640))

        recorded = self.chart_exporter.requests
        self.assertEqual(len(recorded), 1)
        self.assertEqual((recorded[0].method, recorded[0].path), ("POST", "/charts"))
        self.assertEqual(recorded[0].body, {"language": "en", "device": "desktop", "chart_config": CHART_CONFIG})
        self.assertEqual(recorded[0].headers["content-type"], "application/json")

    def test_bad_request_is_not_retried(self):
        self.chart_exporter.set_default("invalid_chart_config")

        with self.assertRaises(ChartExporterMalformedRequest) as ctx:
            ChartExporterClient().create_chart(CHART_CONFIG)

        self.assertEqual(
            ctx.exception.errors,
            [{"code": "invalid_chart_config", "description": ERRORS["invalid_chart_config"][1]}],
        )
        self.assertEqual(len(self.chart_exporter.requests), 1)

    def test_busy_renderer_is_retried(self):
        self.chart_exporter.queue("renderer_busy", "renderer_busy")

        result = ChartExporterClient().create_chart(CHART_CONFIG)

        self.assertIsInstance(result, ChartObjectResponse)
        self.assertEqual(
            [request.scenario for request in self.chart_exporter.requests],
            ["renderer_busy", "renderer_busy", "success"],
        )

    @override_settings(CMS_CHART_EXPORTER_API_TIMEOUT_SECONDS=0.2, CMS_CHART_EXPORTER_API_MAX_RETRIES=0)
    def test_slow_response_times_out(self):
        self.chart_exporter.set_default("success", delay=2)
        client = ChartExporterClient()
        start = time.monotonic()

        with self.assertRaises(ChartExporterUnavailable):
            client.create_chart(CHART_CONFIG)

        self.assertLess(time.monotonic() - start, 1)
        self.assertEqual(len(self.chart_exporter.requests), 1)


class RenderChartBlocksMockTests(ChartExporterMockTestCase):
    def test_bucket_mismatch_is_logged_but_the_image_is_created(self):
        self.chart_exporter.set_default("wrong_bucket")
        block = next(iter_chart_blocks(make_page_with_chart().content))

        with self.assertLogs("cms.datavis.models.rendered_chart_image", level="ERROR") as logs:
            results = render_chart_blocks([block])

        self.assertTrue(results[0].changed)
        self.assertIsInstance(block.value["rendered_chart_image"], RenderedChartImage)
        self.assertIn("'wrong-bucket' does not match configured bucket", logs.output[0])

    @override_settings(CMS_CHART_EXPORTER_API_MAX_CONCURRENT_RENDERS=1, CMS_CHART_EXPORTER_API_MAX_RETRIES=0)
    def test_mixed_outcomes(self):
        blocks = make_chart_blocks(3)
        # A single worker renders the blocks in order, so each gets the next queued behaviour.
        self.chart_exporter.queue("success", "invalid_chart_config", "renderer_busy")

        results = render_chart_blocks(blocks)

        self.assertEqual(
            results,
            [
                ChartRenderResult(block_id=blocks[0].id, changed=True),
                ChartRenderResult(block_id=blocks[1].id, changed=False, error=GENERIC_RENDER_ERROR),
                ChartRenderResult(block_id=blocks[2].id, changed=False, error=UNAVAILABLE_RENDER_ERROR),
            ],
        )
        image = RenderedChartImage.objects.get()
        self.assertEqual(blocks[0].value["rendered_chart_image"], image)
        self.assertTrue(default_storage.exists(image.file.name))

        self.client.force_login(UserFactory(is_superuser=True))
        response = self.client.get(image.serve_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(b"".join(response.streaming_content), PNG)

    @override_settings(CMS_CHART_EXPORTER_API_MAX_CONCURRENT_RENDERS=2, CMS_CHART_EXPORTER_API_MAX_RETRIES=0)
    def test_concurrent_renders_are_limited(self):
        blocks = make_chart_blocks(3)
        self.chart_exporter.set_default("success", delay=0.2)

        results = render_chart_blocks(blocks)

        self.assertTrue(all(result.changed for result in results))
        self.assertEqual(len(self.chart_exporter.requests), 3)
        self.assertIn(self.chart_exporter.peak_in_flight, (1, 2))


@override_settings(CMS_CHART_EXPORTER_API_MAX_RETRIES=2)
class ChartExporterKnownBugTests(ChartExporterMockTestCase):
    # Known bug: the client joins the base URL and path with "/", so a trailing slash makes it POST to //charts.
    @unittest.expectedFailure
    def test_base_url_with_trailing_slash(self):
        with self.settings(CMS_CHART_EXPORTER_API_BASE_URL=f"{self.chart_exporter.url}/"):
            result = ChartExporterClient().create_chart(CHART_CONFIG)

        self.assertIsInstance(result, ChartObjectResponse)
        self.assertEqual(self.chart_exporter.requests[0].path, "/charts")

    # Known bug: a 502 from the infrastructure in front of the exporter is not retried.
    @unittest.expectedFailure
    def test_bad_gateway_is_retried(self):
        self.chart_exporter.queue("bad_gateway")

        result = ChartExporterClient().create_chart(CHART_CONFIG)

        self.assertIsInstance(result, ChartObjectResponse)
        self.assertEqual(len(self.chart_exporter.requests), 2)

    # Known bug: a 504 from the infrastructure in front of the exporter is not retried.
    @unittest.expectedFailure
    def test_gateway_timeout_is_retried(self):
        self.chart_exporter.queue("gateway_timeout")

        result = ChartExporterClient().create_chart(CHART_CONFIG)

        self.assertIsInstance(result, ChartObjectResponse)
        self.assertEqual(len(self.chart_exporter.requests), 2)

    # Known bug: a 201 response with a missing field raises a KeyError instead of a ChartExporterError.
    @unittest.expectedFailure
    def test_malformed_response_raises_chart_exporter_error(self):
        self.chart_exporter.set_default("missing_fields")

        with self.assertRaises(ChartExporterError):
            ChartExporterClient().create_chart(CHART_CONFIG)

    # Known bug: a malformed response for one chart raises out of render_chart_blocks, losing the other charts.
    @unittest.expectedFailure
    @override_settings(CMS_CHART_EXPORTER_API_MAX_CONCURRENT_RENDERS=1)
    def test_malformed_response_does_not_abort_the_batch(self):
        blocks = make_chart_blocks(2)
        self.chart_exporter.queue("success", "missing_fields")

        results = render_chart_blocks(blocks)

        self.assertEqual(
            results,
            [
                ChartRenderResult(block_id=blocks[0].id, changed=True),
                ChartRenderResult(block_id=blocks[1].id, changed=False, error=GENERIC_RENDER_ERROR),
            ],
        )
