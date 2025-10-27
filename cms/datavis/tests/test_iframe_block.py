from django.conf import settings
from django.core.exceptions import ValidationError
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import IframeBlock
from cms.datavis.tests.test_chart_blocks_base import BaseVisualisationBlockTestCase


class IframeBlockTestCase(BaseVisualisationBlockTestCase):
    block_type = IframeBlock
    valid_domains = settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS

    def setUp(self):
        super().setUp()
        self.raw_data["iframe_source_url"] = "https://www.ons.gov.uk/visualisations/dvc/1234567890"

    def test_generic_properties(self):
        self._test_generic_properties()

    def test_validating_data(self):
        """Test that the data we're using for these unit tests is good."""
        value = self.get_value()
        self.assertIsInstance(value, StructValue)
        try:
            self.block.clean(value)
        except ValidationError as e:
            self.fail(f"ValidationError raised: {e}")

    def test_invalid_data(self):
        """Validate that these tests can detect invalid data."""
        invalid_data = self.raw_data.copy()
        invalid_data["title"] = ""  # Required field
        value = self.get_value(invalid_data)
        with self.assertRaises(ValidationError, msg="Expected ValidationError for missing title"):
            self.block.clean(value)

    def test_invalid_url(self):
        """Validate that invalid URLs are rejected."""
        invalid_data = self.raw_data.copy()

        readable_prefixes = " or ".join(settings.IFRAME_VISUALISATION_PATH_PREFIXES)
        cases = {
            "https://www.random.url.com": "The URL hostname is not in the list of allowed domains: ons.gov.uk",
            "http://ons.gov.uk": "Please enter a valid URL. "
            "It should start with 'https://' and contain a valid domain name.",
            "https://ons.gov.uk/invalidpath/12345": (
                f"The URL path is not allowed. It must start with one of: {readable_prefixes}, "
                "and include a subpath after the prefix."
            ),
            "https://www.ons.gov.uk/visualisations/": (
                f"The URL path is not allowed. It must start with one of: {readable_prefixes}, "
                "and include a subpath after the prefix."
            ),
            "https://www.ons.gov.uk/visualisations": (
                f"The URL path is not allowed. It must start with one of: {readable_prefixes}, "
                "and include a subpath after the prefix."
            ),
        }

        for bad_url, message in cases.items():
            with self.subTest(bad_url=bad_url):
                invalid_data["iframe_source_url"] = bad_url
                value = self.get_value(invalid_data)
                with self.assertRaises(ValidationError, msg="Expected ValidationError for invalid URL") as info:
                    self.block.clean(value)

                self.assertEqual(info.exception.block_errors["iframe_source_url"].message, message)

    def test_valid_urls(self):
        """Test valid URL patterns for each domain in the valid_domains list."""
        for base_domain in self.valid_domains:
            url_patterns = [
                f"https://{base_domain}/visualisations/dvc/1234567890",
                f"https://www.{base_domain}/visualisations/dvc/1234567890",
                f"https://subdomain.random.{base_domain}/visualisations/dvc/1234567890",
            ]

            for url in url_patterns:
                with self.subTest(domain=base_domain, url=url):
                    valid_data = self.raw_data.copy()
                    valid_data["iframe_source_url"] = url
                    value = self.get_value(valid_data)
                    self.block.clean(value)
