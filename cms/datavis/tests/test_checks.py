from django.test import TestCase, override_settings

from cms.datavis.checks import check_chart_exporter_api


class ChartExporterApiCheckTests(TestCase):
    def test_disabled_no_errors(self):
        with override_settings(CMS_CHART_EXPORTER_API_ENABLED=False, CMS_CHART_EXPORTER_API_BASE_URL=""):
            errors = check_chart_exporter_api(app_configs=None)
        self.assertEqual(errors, [])

    def test_enabled_without_base_url_raises_error(self):
        with override_settings(CMS_CHART_EXPORTER_API_ENABLED=True, CMS_CHART_EXPORTER_API_BASE_URL=""):
            errors = check_chart_exporter_api(app_configs=None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "datavis.E001")
        self.assertIn("CMS_CHART_EXPORTER_API_BASE_URL is required", errors[0].msg)

    def test_enabled_with_base_url_no_errors(self):
        with override_settings(
            CMS_CHART_EXPORTER_API_ENABLED=True, CMS_CHART_EXPORTER_API_BASE_URL="https://example.com"
        ):
            errors = check_chart_exporter_api(app_configs=None)
        self.assertEqual(errors, [])
