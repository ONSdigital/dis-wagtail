import dataclasses
import uuid
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from cms.datavis.clients.chart_exporter import ChartObjectResponse
from cms.datavis.models import RenderedChartImage
from cms.datavis.tests.factories import RenderedChartImageFactory
from cms.private_media.constants import Privacy
from cms.private_media.managers import PrivateDocumentManager
from cms.private_media.models import PrivateDocumentMixin


class RenderedChartImageModelConfigurationTests(SimpleTestCase):
    def test_uses_private_document_mixin(self):
        self.assertTrue(issubclass(RenderedChartImage, PrivateDocumentMixin))
        self.assertIsInstance(RenderedChartImage.objects, PrivateDocumentManager)


class RenderedChartImageTests(TestCase):
    def test_default_privacy_is_private(self):
        instance = RenderedChartImageFactory()
        self.assertIs(instance.privacy, Privacy.PRIVATE)
        self.assertTrue(instance.is_private)

    def test_filename_is_derived_from_file_name(self):
        instance = RenderedChartImageFactory(file="charts/6f9619ff-8b86-d011-b42d-00cf4fc964ff.png")
        self.assertEqual(instance.filename, "6f9619ff-8b86-d011-b42d-00cf4fc964ff.png")

    def test_str_returns_filename(self):
        instance = RenderedChartImageFactory(file="charts/abc.png")
        self.assertEqual(str(instance), "abc.png")

    def test_serve_url_reverses_dedicated_view_name(self):
        instance = RenderedChartImageFactory()
        with mock.patch("cms.datavis.models.rendered_chart_image.reverse") as mock_reverse:
            mock_reverse.return_value = "/mock/serve/url/"
            self.assertEqual(instance.serve_url, "/mock/serve/url/")
        mock_reverse.assert_called_once_with("rendered_chart_image_serve", args=[instance.pk])


class RenderedChartImageManagerTests(TestCase):
    def setUp(self):
        self.response = ChartObjectResponse(
            id="6f9619ff-8b86-d011-b42d-00cf4fc964ff",
            created_at="2026-07-02T12:00:00Z",
            bucket=settings.AWS_STORAGE_BUCKET_NAME,
            key="charts/6f9619ff-8b86-d011-b42d-00cf4fc964ff.png",
            content_type="image/png",
            size_bytes=48213,
            width=1200,
            height=640,
        )

    def test_create_from_export_response(self):
        instance = RenderedChartImage.objects.create_from_export_response(self.response, config_hash="a" * 64)

        self.assertEqual(instance.export_id, uuid.UUID(self.response.id))
        self.assertEqual(instance.file.name, self.response.key)
        self.assertEqual(instance.config_hash, "a" * 64)
        self.assertEqual(instance.width, 1200)
        self.assertEqual(instance.height, 640)
        self.assertEqual(instance.content_type, "image/png")
        self.assertEqual(instance.size_bytes, 48213)
        self.assertTrue(instance.pk)

    def test_create_from_export_response_logs_error_on_bucket_mismatch(self):
        response = dataclasses.replace(self.response, bucket="some-other-bucket")

        with self.assertLogs("cms.datavis.models.rendered_chart_image", level="ERROR") as logs:
            RenderedChartImage.objects.create_from_export_response(response, config_hash="a" * 64)

        self.assertIn("some-other-bucket", logs.output[0])
        self.assertIn(settings.AWS_STORAGE_BUCKET_NAME, logs.output[0])

    def test_create_from_export_response_no_error_logged_when_bucket_matches(self):
        with self.assertNoLogs("cms.datavis.models.rendered_chart_image", level="ERROR"):
            RenderedChartImage.objects.create_from_export_response(self.response, config_hash="a" * 64)
