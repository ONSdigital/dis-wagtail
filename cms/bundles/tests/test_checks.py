from unittest.mock import patch

from django.core.checks import Info
from django.core.checks import Warning as DjangoWarning
from django.test import TestCase, override_settings

from cms.bundles.api import BundleAPIClientError
from cms.bundles.checks import check_bundle_api_health


class BundleAPIHealthCheckTests(TestCase):
    """Test cases for Bundle API health system check."""

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=False)
    def test_health_check_skipped_when_api_disabled(self):
        """Test that health check is skipped when Bundle API is disabled."""
        errors = check_bundle_api_health(None)
        self.assertEqual(errors, [])

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.checks.BundleAPIClient")
    def test_health_check_success_with_healthy_api(self, mock_client_class):
        """Test health check success when API is healthy."""
        mock_client = mock_client_class.return_value
        mock_client.get_health.return_value = {"status": "healthy", "version": "1.0.0"}

        errors = check_bundle_api_health(None)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Info)
        self.assertEqual(errors[0].id, "bundles.I001")
        self.assertIn("Bundle API is responding and healthy", errors[0].msg)

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.checks.BundleAPIClient")
    def test_health_check_handles_api_disabled_response(self, mock_client_class):
        """Test health check handles API disabled response gracefully."""
        mock_client = mock_client_class.return_value
        mock_client.get_health.return_value = {"status": "disabled", "message": "Bundle API is disabled"}

        errors = check_bundle_api_health(None)

        self.assertEqual(errors, [])

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True, ONS_API_BASE_URL="https://test-api.example.com")
    @patch("cms.bundles.checks.BundleAPIClient")
    def test_health_check_handles_api_client_error(self, mock_client_class):
        """Test health check handles BundleAPIClientError gracefully."""
        mock_client = mock_client_class.return_value
        mock_client.get_health.side_effect = BundleAPIClientError("Connection failed")

        errors = check_bundle_api_health(None)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], DjangoWarning)
        self.assertEqual(errors[0].id, "bundles.W001")
        self.assertIn("Bundle API health check failed: Connection failed", errors[0].msg)
        self.assertIn("https://test-api.example.com", errors[0].hint)

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.checks.BundleAPIClient")
    def test_health_check_handles_unexpected_error(self, mock_client_class):
        """Test health check handles unexpected errors gracefully."""
        mock_client = mock_client_class.return_value
        mock_client.get_health.side_effect = ValueError("Unexpected error")

        errors = check_bundle_api_health(None)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], DjangoWarning)
        self.assertEqual(errors[0].id, "bundles.W002")
        self.assertIn("Unexpected error during Bundle API health check: Unexpected error", errors[0].msg)
        self.assertIn("Review Bundle API configuration", errors[0].hint)

    @override_settings(DIS_DATASETS_BUNDLE_API_ENABLED=True)
    @patch("cms.bundles.checks.BundleAPIClient")
    def test_health_check_includes_api_url_in_error_hint(self, mock_client_class):
        """Test health check includes API URL in error hint."""
        mock_client = mock_client_class.return_value
        mock_client.get_health.side_effect = BundleAPIClientError("Connection failed")

        errors = check_bundle_api_health(None)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], DjangoWarning)
        self.assertEqual(errors[0].id, "bundles.W001")
        self.assertIn("API URL:", errors[0].hint)
        self.assertIn("Connection failed", errors[0].msg)
