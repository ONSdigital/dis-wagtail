from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import override_settings
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.charts import IframeBlock
from cms.datavis.tests.test_chart_blocks_base import BaseVisualisationBlockTestCase


@override_settings(
    ONS_ALLOWED_LINK_DOMAINS=["example.com"],
    IFRAME_VISUALISATION_ALLOWED_DOMAINS=["example.com"],
    IFRAME_VISUALISATION_PATH_PREFIXES=["/visualisations"],
)
class IframeBlockTestCase(BaseVisualisationBlockTestCase):
    block_type = IframeBlock
    valid_domains: ClassVar[list[str]] = ["example.com"]

    def setUp(self):
        super().setUp()
        self.raw_data["iframe_source_url"] = "https://www.example.com/visualisations/dvc/1234567890"

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
            # Absolute URL with invalid domain
            "https://www.random.url.com": "The URL hostname is not in the list of allowed domains: example.com.",
            # Absolute URL with invalid scheme
            "http://example.com": "Please enter a valid URL. Full URLs must start with 'https://'.",
            # Absolute URL with invalid prefix
            "https://example.com/invalidpath/12345": (
                f"The URL path is not allowed. It must start with: {readable_prefixes}, "
                "and include a subpath after the prefix."
            ),
            # Absolute URL missing subpath after path prefix
            "https://www.example.com/visualisations/": (
                f"The URL path is not allowed. It must start with: {readable_prefixes}, "
                "and include a subpath after the prefix."
            ),
            # Absolute URL missing subpath after path prefix
            "https://www.example.com/visualisations": (
                f"The URL path is not allowed. It must start with: {readable_prefixes}, "
                "and include a subpath after the prefix."
            ),
            # Relative URL missing subpath after prefix
            "/visualisations": (
                f"The URL path is not allowed. It must start with: {readable_prefixes}, "
                "and include a subpath after the prefix."
            ),
            # Relative URL with invalid prefix
            "/foo/bar": (
                f"The URL path is not allowed. It must start with: {readable_prefixes}, "
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

    def test_valid_absolute_urls(self):
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

    def test_valid_relative_url(self):
        """Test valid relative URL patterns."""
        valid_data = self.raw_data.copy()
        valid_data["iframe_source_url"] = "/visualisations/dvc/1234567890"
        value = self.get_value(valid_data)
        self.block.clean(value)

    def test_multiple_validation_errors_shown_together(self):
        """Test that all validation errors (required fields + invalid URL) are shown together."""
        invalid_data = {
            # All required fields are missing
            "title": "",
            "subtitle": "",
            "audio_description": "",
            "iframe_source_url": "",
            # Optional fields
            "caption": "",
            "footnotes": "",
        }

        value = self.get_value(invalid_data)

        with self.assertRaises(ValidationError) as context:
            self.block.clean(value)

        # Check that we have errors for all required fields
        errors = context.exception.block_errors

        # All required fields should have errors
        self.assertIn("title", errors)
        self.assertIn("subtitle", errors)
        self.assertIn("audio_description", errors)
        self.assertIn("iframe_source_url", errors)

        # Check the error messages
        self.assertEqual(errors["title"].message, "This field is required.")
        self.assertEqual(errors["subtitle"].message, "This field is required.")
        self.assertEqual(errors["audio_description"].message, "This field is required.")
        self.assertEqual(errors["iframe_source_url"].message, "Please enter a valid URL.")

        # Optional fields should not have errors
        self.assertNotIn("caption", errors)
        self.assertNotIn("footnotes", errors)

    def test_partial_validation_errors(self):
        """Test that missing required fields are shown along with URL validation errors."""
        invalid_data = {
            "title": "",  # Missing
            "subtitle": "Test subtitle",  # Provided
            "audio_description": "",  # Missing
            "iframe_source_url": "https://www.invalid-domain.com/visualisations/dvc/123",  # Invalid domain
            "caption": "",
            "footnotes": "",
        }

        value = self.get_value(invalid_data)

        with self.assertRaises(ValidationError) as context:
            self.block.clean(value)

        errors = context.exception.block_errors

        # Should have exactly 3 errors
        self.assertEqual(len(errors), 3)

        # Check which fields have errors
        self.assertIn("title", errors)
        self.assertIn("audio_description", errors)
        self.assertIn("iframe_source_url", errors)

        # Check error messages
        self.assertEqual(errors["title"].message, "This field is required.")
        self.assertEqual(errors["audio_description"].message, "This field is required.")
        self.assertEqual(
            errors["iframe_source_url"].message, "The URL hostname is not in the list of allowed domains: example.com"
        )
