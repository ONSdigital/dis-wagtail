from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings
from wagtail.blocks.struct_block import StructValue

from cms.datavis.blocks.iframe import DownloadBlock, IframeBlock
from cms.datavis.tests.test_chart_blocks_base import BaseVisualisationBlockTestCase

VALID_DOMAINS = ["example.com"]


def get_invalid_url_cases() -> dict[str, str]:
    readable_prefixes = " or ".join(settings.IFRAME_VISUALISATION_PATH_PREFIXES)
    return {
        "https://www.random.url.com": "The URL hostname is not in the list of allowed domains: example.com",
        "http://example.com": "Please enter a valid URL. Full URLs must start with 'https://'.",
        "https://example.com/invalidpath/12345": (
            f"The URL path is not allowed. It must start with: {readable_prefixes}, "
            "and include a subpath after the prefix."
        ),
        "https://www.example.com/visualisations/": (
            f"The URL path is not allowed. It must start with: {readable_prefixes}, "
            "and include a subpath after the prefix."
        ),
        "https://www.example.com/visualisations": (
            f"The URL path is not allowed. It must start with: {readable_prefixes}, "
            "and include a subpath after the prefix."
        ),
        "/visualisations": (
            f"The URL path is not allowed. It must start with: {readable_prefixes}, "
            "and include a subpath after the prefix."
        ),
        "/foo/bar": (
            f"The URL path is not allowed. It must start with: {readable_prefixes}, "
            "and include a subpath after the prefix."
        ),
    }


def get_valid_absolute_urls(base_domain: str) -> list[str]:
    return [
        f"https://{base_domain}/visualisations/dvc/1234567890",
        f"https://www.{base_domain}/visualisations/dvc/1234567890",
        f"https://subdomain.random.{base_domain}/visualisations/dvc/1234567890",
    ]


@override_settings(
    ONS_ALLOWED_LINK_DOMAINS=["example.com"],
    IFRAME_VISUALISATION_ALLOWED_DOMAINS=["example.com"],
    IFRAME_VISUALISATION_PATH_PREFIXES=["/visualisations"],
)
class IframeBlockTestCase(BaseVisualisationBlockTestCase):
    block_type = IframeBlock

    def setUp(self):
        super().setUp()
        self.raw_data["accessible_label"] = "Bar chart of GDP per region"
        self.raw_data["iframe_source_url"] = "https://www.example.com/visualisations/dvc/1234567890"

    def get_figure_config(self, raw_data: dict[str, Any] | None = None):
        """Helper method to get figure config, following the pattern from BaseChartBlockTestCase."""
        value = self.get_value(raw_data)
        return self.block.get_figure_config(value)

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

    def test_download_link_help_text_is_set(self):
        self.assertEqual(
            self.block.child_blocks["image_download"].child_blocks["link_text"].field.help_text,
            "This should always follow the format 'Download image (23KB)', with the correct file "
            "size substituted. The file size suffix should be capitalised.",
        )
        self.assertEqual(
            self.block.child_blocks["data_download"].child_blocks["link_text"].field.help_text,
            "This should always follow the format 'Download CSV (23KB)', with the correct file "
            "type and file size substituted. The file type and file size suffix should be "
            "capitalised.",
        )

    def test_invalid_data(self):
        """Validate that these tests can detect invalid data."""
        invalid_data = self.raw_data.copy()
        invalid_data["accessible_label"] = ""  # Required field
        value = self.get_value(invalid_data)
        with self.assertRaises(ValidationError, msg="Expected ValidationError for missing accessible label"):
            self.block.clean(value)

    def test_invalid_source_url(self):
        """Validate that invalid source URLs are rejected."""
        invalid_data = self.raw_data.copy()

        cases = get_invalid_url_cases()

        for bad_url, message in cases.items():
            with self.subTest(bad_url=bad_url):
                invalid_data["iframe_source_url"] = bad_url
                value = self.get_value(invalid_data)
                with self.assertRaises(ValidationError, msg="Expected ValidationError for invalid URL") as info:
                    self.block.clean(value)

                self.assertEqual(info.exception.block_errors["iframe_source_url"].message, message)

    def test_valid_absolute_urls(self):
        """Test valid URL patterns for each domain in the valid_domains list."""
        for base_domain in VALID_DOMAINS:
            for url in get_valid_absolute_urls(base_domain):
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
            "accessible_label": "",
            "audio_description": "",
            "iframe_source_url": "",
            # Optional fields
            "title": "",
            "subtitle": "",
            "caption": "",
            "footnotes": "",
            "image_download": {"url": "", "link_text": ""},
            "data_download": {"url": "", "link_text": ""},
        }

        value = self.get_value(invalid_data)

        with self.assertRaises(ValidationError) as context:
            self.block.clean(value)

        errors = context.exception.block_errors

        # All required fields should have errors
        self.assertIn("accessible_label", errors)
        self.assertIn("audio_description", errors)
        self.assertIn("iframe_source_url", errors)

        # Check the error messages
        self.assertEqual(errors["accessible_label"].message, "This field is required.")
        self.assertEqual(errors["audio_description"].message, "This field is required.")
        self.assertEqual(errors["iframe_source_url"].message, "Please enter a valid URL.")

        # Optional fields should not have errors
        self.assertNotIn("title", errors)
        self.assertNotIn("subtitle", errors)
        self.assertNotIn("caption", errors)
        self.assertNotIn("footnotes", errors)
        self.assertNotIn("image_download", errors)
        self.assertNotIn("data_download", errors)

    def test_partial_validation_errors(self):
        """Test that missing required fields are shown along with URL validation errors."""
        invalid_data = {
            "accessible_label": "",  # Missing
            "audio_description": "",  # Missing
            "iframe_source_url": "https://www.invalid-domain.com/visualisations/dvc/123",  # Invalid domain
            "title": "",
            "subtitle": "",
            "caption": "",
            "footnotes": "",
            "image_download": {
                "url": "",
                "link_text": "",
            },
            "data_download": {
                "url": "",
                "link_text": "",
            },
        }

        value = self.get_value(invalid_data)

        with self.assertRaises(ValidationError) as context:
            self.block.clean(value)

        errors = context.exception.block_errors

        # Should have exactly 3 errors
        self.assertEqual(len(errors), 3)

        # Check which fields have errors
        self.assertIn("accessible_label", errors)
        self.assertIn("audio_description", errors)
        self.assertIn("iframe_source_url", errors)

        # Check error messages
        self.assertEqual(errors["accessible_label"].message, "This field is required.")
        self.assertEqual(errors["audio_description"].message, "This field is required.")
        self.assertEqual(
            errors["iframe_source_url"].message, "The URL hostname is not in the list of allowed domains: example.com"
        )

    def test_clean__subtitle_without_title_raises(self):
        """A subtitle cannot be saved without a title."""
        invalid_data = self.raw_data.copy()
        invalid_data["title"] = ""
        invalid_data["subtitle"] = "A subtitle"
        value = self.get_value(invalid_data)

        with self.assertRaises(ValidationError) as info:
            self.block.clean(value)

        self.assertEqual(
            info.exception.block_errors["subtitle"].message,
            "Please add a title if you want to add a subtitle.",
        )

    def test_clean__subtitle_error_shown_with_other_errors(self):
        """The subtitle error is reported alongside other validation errors."""
        invalid_data = self.raw_data.copy()
        invalid_data["title"] = ""
        invalid_data["subtitle"] = "A subtitle"
        invalid_data["accessible_label"] = ""
        value = self.get_value(invalid_data)

        with self.assertRaises(ValidationError) as info:
            self.block.clean(value)

        self.assertIn("subtitle", info.exception.block_errors)
        self.assertIn("accessible_label", info.exception.block_errors)

    def test_clean__subtitle_with_title(self):
        """A subtitle paired with a title is allowed."""
        valid_data = self.raw_data.copy()
        valid_data["subtitle"] = "A subtitle"
        value = self.get_value(valid_data)
        self.block.clean(value)

    def test_clean__no_subtitle(self):
        """No subtitle is allowed regardless of whether there is a title."""
        valid_data = self.raw_data.copy()
        valid_data["subtitle"] = ""
        value = self.get_value(valid_data)
        self.block.clean(value)

    def test_footnotes_configuration(self):
        """Test that footnotes are configured correctly in the component config when set."""
        self.raw_data["footnotes"] = "Important note: This is test footnote text"
        config = self.get_figure_config()
        self.assertEqual(
            config["footnotes"],
            {
                "title": "Footnotes",
                "content": '<div class="rich-text">Important note: This is test footnote text</div>',
            },
        )

    def test_footnotes_not_in_config_when_not_set(self):
        """Footnotes should be omitted from the component config when no footnotes have been entered."""
        self.raw_data["footnotes"] = ""
        config = self.get_figure_config()
        self.assertNotIn("footnotes", config)

    def test_footnotes_html_only_omitted(self):
        for html in ("<p></p>", "<p> </p>"):
            with self.subTest(html=html):
                self.raw_data["footnotes"] = html
                config = self.get_figure_config()
                self.assertNotIn("footnotes", config)
                rendered = self.block.render(self.raw_data)
                self.assertNotIn("Footnotes", rendered)
        content = "Valid content"
        with self.subTest(content=content):
            self.raw_data["footnotes"] = content
            config = self.get_figure_config()
            self.assertIn("footnotes", config)
            rendered = self.block.render(self.raw_data)
            self.assertIn(content, rendered)

    def test_download_block_errors_are_nested_under_the_parent_field(self):
        invalid_data = self.raw_data.copy()
        invalid_data["data_download"] = {
            "url": "https://www.invalid-domain.com/visualisations/dvc/123/data.csv",
            "link_text": "Download CSV (23KB)",
        }

        value = self.get_value(invalid_data)

        with self.assertRaises(ValidationError) as info:
            self.block.clean(value)

        self.assertIn("data_download", info.exception.block_errors)
        self.assertEqual(
            info.exception.block_errors["data_download"].block_errors["url"].message,
            "The URL hostname is not in the list of allowed domains: example.com",
        )

    def test_download_validation_errors_shown_together(self):
        """Nested download blocks show both URL and link text errors together."""
        for field_name in ("image_download", "data_download"):
            with self.subTest(field_name=field_name):
                invalid_data = self.raw_data.copy()
                invalid_data[field_name] = {
                    "url": "https://www.invalid-domain.com/visualisations/dvc/123/data.csv",
                    "link_text": "",
                }

                value = self.get_value(invalid_data)

                with self.assertRaises(ValidationError) as info:
                    self.block.clean(value)

                self.assertEqual(
                    info.exception.block_errors[field_name].block_errors["url"].message,
                    "The URL hostname is not in the list of allowed domains: example.com",
                )
                self.assertEqual(
                    info.exception.block_errors[field_name].block_errors["link_text"].message,
                    "Link text is required when a URL is provided.",
                )

    def test_clean__valid_download_data_is_allowed(self):
        """Valid nested download data is accepted when cleaning the iframe block."""
        valid_data = self.raw_data.copy()
        valid_data["data_download"] = {
            "url": "/visualisations/dvc/1234567890/data.csv",
            "link_text": "Download CSV (23KB)",
        }

        value = self.get_value(valid_data)

        self.block.clean(value)

    def test_download_not_in_config_when_not_set(self):
        """Downloads should be omitted from the component config when no download fields are set."""
        data = self.raw_data.copy()
        data["image_download"] = {"url": "", "link_text": ""}
        data["data_download"] = {"url": "", "link_text": ""}

        config = self.get_figure_config(data)

        self.assertNotIn("download", config)

    def test_only_download_which_is_set_appears_in_config(self):
        """Only downloads which are set should appear in the component config."""
        data = self.raw_data.copy()
        data["image_download"] = {"url": "", "link_text": ""}
        data["data_download"] = {"url": "/visualisations/dvc/1234567890/data.csv", "link_text": "Download CSV (23KB)"}

        config = self.get_figure_config(data)
        downloads = config["download"]["itemsList"]

        # Only one download should be present in the config
        self.assertEqual(len(downloads), 1)

        # Confirm the data download is present in the config
        self.assertEqual(downloads[0]["text"], "Download CSV (23KB)")
        self.assertEqual(downloads[0]["url"], "/visualisations/dvc/1234567890/data.csv")

    def test_both_downloads_appear_in_config(self):
        """Image and data downloads are both included in the config when they are both set."""
        data = self.raw_data.copy()
        data["image_download"] = {
            "url": "/visualisations/dvc/1234567890/image.png",
            "link_text": "Download image (23KB)",
        }
        data["data_download"] = {"url": "/visualisations/dvc/1234567890/data.csv", "link_text": "Download CSV (23KB)"}

        config = self.get_figure_config(data)
        downloads = config["download"]["itemsList"]

        # Both downloads should be present in the config
        self.assertEqual(len(downloads), 2)

        self.assertEqual(downloads[0]["text"], "Download image (23KB)")
        self.assertEqual(downloads[0]["url"], "/visualisations/dvc/1234567890/image.png")
        self.assertEqual(downloads[1]["text"], "Download CSV (23KB)")
        self.assertEqual(downloads[1]["url"], "/visualisations/dvc/1234567890/data.csv")


@override_settings(
    ONS_ALLOWED_LINK_DOMAINS=["example.com"],
    IFRAME_VISUALISATION_ALLOWED_DOMAINS=["example.com"],
    IFRAME_VISUALISATION_PATH_PREFIXES=["/visualisations"],
)
class DownloadBlockTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block = DownloadBlock()

    def test_clean__download_link_text_without_url_raises_error(self):
        """A download link text cannot be saved without a download url."""
        value = self.block.to_python({"url": "", "link_text": "Download CSV (23KB)"})

        with self.assertRaises(ValidationError) as info:
            self.block.clean(value)

        self.assertEqual(
            info.exception.block_errors["url"].message,
            "A URL is required when link text is provided.",
        )

    def test_clean__download_url_without_link_text_raises_error(self):
        """A download url cannot be saved without download link text."""
        value = self.block.to_python({"url": "/visualisations/dvc/1234567890/data.csv", "link_text": ""})

        with self.assertRaises(ValidationError) as info:
            self.block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_text"].message,
            "Link text is required when a URL is provided.",
        )

    def test_clean__download_url_with_whitespace_only_link_text_raises_error(self):
        """Whitespace-only download link text is treated as missing."""
        value = self.block.to_python({"url": "/visualisations/dvc/1234567890/data.csv", "link_text": "   "})

        with self.assertRaises(ValidationError) as info:
            self.block.clean(value)

        self.assertEqual(
            info.exception.block_errors["link_text"].message,
            "Link text is required when a URL is provided.",
        )

    def test_clean__download_url_with_link_text(self):
        """A download url with download link text is allowed."""
        value = self.block.to_python(
            {"url": "/visualisations/dvc/1234567890/data.csv", "link_text": "Download CSV (23KB)"}
        )

        self.block.clean(value)

    def test_clean__no_download_url_and_no_link_text(self):
        """The download block is not required so an empty download url and empty download link text is allowed."""
        value = self.block.to_python({"url": "", "link_text": ""})

        self.block.clean(value)

    def test_invalid_download_url(self):
        """Validate that invalid download URLs are rejected."""
        cases = get_invalid_url_cases()

        for bad_url, message in cases.items():
            with self.subTest(bad_url=bad_url):
                value = self.block.to_python({"url": bad_url, "link_text": "Download CSV (23KB)"})
                with self.assertRaises(ValidationError, msg="Expected ValidationError for invalid URL") as info:
                    self.block.clean(value)

                self.assertEqual(info.exception.block_errors["url"].message, message)

    def test_valid_absolute_download_urls(self):
        """Test valid URL patterns for each domain in the valid_domains list."""
        for base_domain in VALID_DOMAINS:
            for url in get_valid_absolute_urls(base_domain):
                with self.subTest(domain=base_domain, url=url):
                    value = self.block.to_python({"url": url, "link_text": "Download CSV (23KB)"})
                    self.block.clean(value)

    def test_valid_relative_download_url(self):
        """Test valid relative URL patterns."""
        value = self.block.to_python({"url": "/visualisations/dvc/1234567890", "link_text": "Download CSV (23KB)"})
        self.block.clean(value)
