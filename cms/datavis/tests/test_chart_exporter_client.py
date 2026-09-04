from http import HTTPStatus
from unittest.mock import patch

import requests
import responses
from django.test import TestCase, override_settings

from cms.datavis.clients.chart_exporter import (
    ChartExporterClient,
    ChartExporterError,
    ChartExporterMalformedRequest,
    ChartExporterUnavailable,
    ChartObjectResponse,
)

BASE_URL = "https://chart-exporter.example.com"


@override_settings(CMS_CHART_EXPORTER_API_ENABLED=True, CMS_CHART_EXPORTER_API_MAX_RETRIES=2)
class ChartExporterClientTests(TestCase):
    def setUp(self):
        self.client = ChartExporterClient(base_url=BASE_URL)
        self.chart_config = {"chartType": "column", "series": []}
        self.mock_response_data = {
            "id": "6f9619ff-8b86-d011-b42d-00cf4fc964ff",
            "created_at": "2026-07-02T12:00:00Z",
            "bucket": "ons-charts",
            "key": "charts/6f9619ff-8b86-d011-b42d-00cf4fc964ff.png",
            "content_type": "image/png",
            "size_bytes": 48213,
            "width": 1200,
            "height": 640,
        }

    @override_settings(CMS_CHART_EXPORTER_API_ENABLED=False)
    def test_create_chart_noop_when_disabled(self):
        client = ChartExporterClient(base_url=BASE_URL)
        self.assertIsNone(client.create_chart(self.chart_config))

    @responses.activate
    def test_create_chart_success(self):
        responses.post(f"{BASE_URL}/charts", json=self.mock_response_data, status=HTTPStatus.CREATED)

        result = self.client.create_chart(self.chart_config)

        self.assertEqual(result, ChartObjectResponse(**self.mock_response_data))
        request_body = responses.calls[0].request.body
        self.assertIn('"language": "en"', request_body if isinstance(request_body, str) else request_body.decode())

    @responses.activate
    def test_create_chart_malformed_request_not_retried(self):
        error_body = {"errors": [{"code": "invalid_config", "description": "chart_config must be an object"}]}
        responses.post(f"{BASE_URL}/charts", json=error_body, status=HTTPStatus.BAD_REQUEST)

        with self.assertRaises(ChartExporterMalformedRequest) as ctx:
            self.client.create_chart(self.chart_config)

        self.assertEqual(ctx.exception.errors, error_body["errors"])
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_create_chart_unavailable_is_retried_then_raises(self):
        responses.post(f"{BASE_URL}/charts", status=HTTPStatus.SERVICE_UNAVAILABLE)
        responses.post(f"{BASE_URL}/charts", status=HTTPStatus.SERVICE_UNAVAILABLE)
        responses.post(f"{BASE_URL}/charts", status=HTTPStatus.SERVICE_UNAVAILABLE)

        # Skip the real backoff delay between retries.
        with patch("cms.datavis.clients.chart_exporter.time.sleep"), self.assertRaises(ChartExporterUnavailable):
            self.client.create_chart(self.chart_config)

        # initial attempt + CMS_CHART_EXPORTER_API_MAX_RETRIES retries
        self.assertEqual(len(responses.calls), 3)

    @responses.activate
    def test_create_chart_succeeds_after_transient_failure(self):
        responses.post(f"{BASE_URL}/charts", status=HTTPStatus.INTERNAL_SERVER_ERROR)
        responses.post(f"{BASE_URL}/charts", json=self.mock_response_data, status=HTTPStatus.CREATED)

        # Skip the real backoff delay between retries.
        with patch("cms.datavis.clients.chart_exporter.time.sleep"):
            result = self.client.create_chart(self.chart_config)

        self.assertEqual(result, ChartObjectResponse(**self.mock_response_data))
        self.assertEqual(len(responses.calls), 2)

    @responses.activate
    def test_create_chart_timeout_is_retried(self):
        responses.post(f"{BASE_URL}/charts", body=requests.exceptions.Timeout("boom"))
        responses.post(f"{BASE_URL}/charts", json=self.mock_response_data, status=HTTPStatus.CREATED)

        # Skip the real backoff delay between retries.
        with patch("cms.datavis.clients.chart_exporter.time.sleep"):
            result = self.client.create_chart(self.chart_config)

        self.assertEqual(result, ChartObjectResponse(**self.mock_response_data))

    @responses.activate
    def test_create_chart_payload_too_large_not_retried(self):
        responses.post(f"{BASE_URL}/charts", status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

        with self.assertRaises(ChartExporterMalformedRequest):
            self.client.create_chart(self.chart_config)

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_create_chart_unsupported_media_type_not_retried(self):
        responses.post(f"{BASE_URL}/charts", status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        with self.assertRaises(ChartExporterMalformedRequest):
            self.client.create_chart(self.chart_config)

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_create_chart_connection_error_is_retried_then_raises(self):
        responses.post(f"{BASE_URL}/charts", body=requests.exceptions.ConnectionError("boom"))
        responses.post(f"{BASE_URL}/charts", body=requests.exceptions.ConnectionError("boom"))
        responses.post(f"{BASE_URL}/charts", body=requests.exceptions.ConnectionError("boom"))

        with patch("cms.datavis.clients.chart_exporter.time.sleep"), self.assertRaises(ChartExporterUnavailable):
            self.client.create_chart(self.chart_config)

        self.assertEqual(len(responses.calls), 3)

    @responses.activate
    def test_create_chart_unexpected_status_raises_generic_error_and_is_not_retried(self):
        responses.post(f"{BASE_URL}/charts", status=HTTPStatus.NOT_FOUND)

        with self.assertRaises(ChartExporterError) as ctx:
            self.client.create_chart(self.chart_config)

        self.assertNotIsInstance(ctx.exception, ChartExporterMalformedRequest)
        self.assertNotIsInstance(ctx.exception, ChartExporterUnavailable)
        self.assertEqual(len(responses.calls), 1)
