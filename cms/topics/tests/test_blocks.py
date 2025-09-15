from django.test import TestCase, override_settings
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.blocks.stream_block import StreamValue
from wagtail.images.tests.utils import get_test_image_file

from cms.home.models import HomePage
from cms.images.models import CustomImage
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.blocks import (
    ExploreMoreExternalLinkBlock,
    ExploreMoreInternalLinkBlock,
    ExploreMoreStoryBlock,
    TimeSeriesPageLinkBlock,
    TimeSeriesPageStoryBlock,
)
from cms.topics.tests.factories import TopicPageFactory


class ExploreMoreBlocksTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = HomePage.objects.first()
        cls.theme_page = ThemePageFactory(listing_summary="Theme summary")
        cls.topic_page = TopicPageFactory(parent=cls.theme_page, live=False)

        cls.image = CustomImage.objects.create(title="Test Image", file=get_test_image_file())

    def test_external_link_block__get_formatted_value(self):
        block = ExploreMoreExternalLinkBlock()
        value = block.to_python(
            {
                "url": "https://ons.gov.uk",
                "title": "External Link",
                "description": "Test description",
                "thumbnail": self.image.pk,
            }
        )

        formatted = block.get_formatted_value(value)

        self.assertEqual(formatted["title"]["text"], "External Link")
        self.assertEqual(formatted["title"]["url"], "https://ons.gov.uk")
        self.assertEqual(formatted["description"], "Test description")
        self.assertIn("smallSrc", formatted["thumbnail"])
        self.assertIn("largeSrc", formatted["thumbnail"])

    def test_internal_link_block__get_formatted_value_with_overrides(self):
        block = ExploreMoreInternalLinkBlock()
        value = block.to_python(
            {
                "page": self.home_page.pk,
                "title": "Custom Title",
                "description": "Custom Description",
                "thumbnail": self.image.pk,
            }
        )

        formatted = block.get_formatted_value(value)

        self.assertEqual(formatted["title"]["text"], "Custom Title")
        self.assertEqual(formatted["description"], "Custom Description")
        self.assertIn("smallSrc", formatted["thumbnail"])

    def test_internal_link_block__get_formatted_value_without_overrides(self):
        block = ExploreMoreInternalLinkBlock()
        value = block.to_python({"page": self.home_page.pk, "title": "", "description": "", "thumbnail": None})

        # Add page attributes that would normally exist
        self.home_page.listing_summary = "Page listing summary"
        self.home_page.listing_image = self.image
        self.home_page.save()

        formatted = block.get_formatted_value(value)

        self.assertEqual(formatted["title"]["text"], self.home_page.title)
        self.assertEqual(formatted["description"], "Page listing summary")
        self.assertIn("smallSrc", formatted["thumbnail"])

    def test_internal_link_block__get_formatted_value_with_unpublished_page_returns_empty(self):
        block = ExploreMoreInternalLinkBlock()
        value = block.to_python({"page": self.topic_page.pk})

        self.assertEqual(block.get_formatted_value(value), {})

    def test_explore_more_storyblock__get_context(self):
        block = ExploreMoreStoryBlock()

        # Create stream value with valid and invalid items
        stream_value = block.to_python(
            [
                {
                    "type": "external_link",
                    "value": {
                        "url": "https://ons.gov.uk",
                        "title": "External",
                        "description": "Test",
                        "thumbnail": self.image.pk,
                    },
                },
                {"type": "internal_link", "value": {"page": self.theme_page.pk}},
                {"type": "internal_link", "value": {"page": self.topic_page.pk}},
            ]
        )

        context = block.get_context(stream_value)
        formatted_items = context["formatted_items"]

        # Should only contain the valid external link
        self.assertEqual(len(formatted_items), 2)
        self.assertEqual(formatted_items[0]["title"]["text"], "External")
        self.assertIn("thumbnail", formatted_items[0])

        self.assertEqual(formatted_items[1]["title"]["text"], self.theme_page.title)
        self.assertEqual(formatted_items[1]["description"], self.theme_page.listing_summary)


class TimeSeriesPageStoryBlockTestCase(TestCase):
    def test_time_series_page_link_block_validation_fails_on_duplicated_links(self):
        block = TimeSeriesPageStoryBlock()
        stream_value = StreamValue(
            block,
            [
                (
                    "time_series_page_link",
                    {"title": "Link 1", "url": "https://example.com/1", "description": "Summary 1"},
                ),
                (
                    "time_series_page_link",
                    {"title": "Link 2", "url": "https://example.com/1", "description": "Summary 2"},
                ),
            ],
        )

        with self.assertRaises(StreamBlockValidationError) as error_context:
            block.clean(stream_value)
            self.assertEqual(error_context.exception.message, "Duplicate time series links are not allowed")

    def test_identical_links_with_and_without_trailing_slash_are_considered_duplicates(self):
        block = TimeSeriesPageStoryBlock()
        stream_value = StreamValue(
            block,
            [
                (
                    "time_series_page_link",
                    {"title": "Link 1", "url": "https://example.com/1/", "description": "Summary 1"},
                ),
                (
                    "time_series_page_link",
                    {"title": "Link 2", "url": "https://example.com/1", "description": "Summary 2"},
                ),
            ],
        )

        with self.assertRaises(StreamBlockValidationError) as error_context:
            cleaned_value = block.clean(stream_value)

            self.assertEqual(error_context.exception.message, "Duplicate time series links are not allowed")

            self.assertEqual(
                cleaned_value[0].value["url"], "https://example.com/1"
            )  # Ensure that the trailing slash has been removed

    def test_identical_links_with_and_without_www_are_considered_duplicates(self):
        block = TimeSeriesPageStoryBlock()
        stream_value = StreamValue(
            block,
            [
                (
                    "time_series_page_link",
                    {"title": "Link 1", "url": "https://www.example.com/1", "description": "Summary 1"},
                ),
                (
                    "time_series_page_link",
                    {"title": "Link 2", "url": "https://example.com/1", "description": "Summary 2"},
                ),
            ],
        )

        with self.assertRaises(StreamBlockValidationError) as error_context:
            block.clean(stream_value)

            self.assertEqual(error_context.exception.message, "Duplicate time series links are not allowed")

    def test_identical_links_with_uppercase_and_lowercase_are_considered_duplicates(self):
        block = TimeSeriesPageStoryBlock()
        stream_value = StreamValue(
            block,
            [
                (
                    "time_series_page_link",
                    {"title": "Link 1", "url": "https://EXAMPLE.com/1", "description": "Summary 1"},
                ),
                (
                    "time_series_page_link",
                    {"title": "Link 2", "url": "https://example.com/1", "description": "Summary 2"},
                ),
            ],
        )

        with self.assertRaises(StreamBlockValidationError) as error_context:
            block.clean(stream_value)
            self.assertEqual(error_context.exception.message, "Duplicate time series links are not allowed")


class TimeSeriesPageLinkBlockTestCase(TestCase):
    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["domain1.com"])
    def test_time_series_page_link_block_validation_fails_on_invalid_domain(self):
        block = TimeSeriesPageLinkBlock()
        value = {
            "title": "Invalid Link",
            "description": "This link is invalid",
            "url": "https://invalid-domain.com/time-series",
        }

        with self.assertRaises(StructBlockValidationError) as info:
            block.clean(value)

        self.assertEqual(
            info.exception.block_errors["url"].message,
            "The URL hostname is not in the list of allowed domains or their subdomains: domain1.com",
        )

    def test_raises_errors_for_empty_mandatory_fields(self):
        block = TimeSeriesPageLinkBlock()
        value = {
            "title": "",
            "description": "",
            "url": "",
        }

        with self.assertRaises(StructBlockValidationError) as info:
            block.clean(value)

        self.assertEqual(info.exception.block_errors["title"].message, "This field is required.")
        self.assertEqual(info.exception.block_errors["description"].message, "This field is required.")
        self.assertEqual(info.exception.block_errors["url"].message, "This field is required.")

    @override_settings(ONS_ALLOWED_LINK_DOMAINS=["domain1.com", "domain2.example.com"])
    def test_raises_error_even_when_only_some_mandatory_fields_are_absent(self):
        """Check that the validation error is raised correctly when only some mandatory fields aren't present."""
        block = TimeSeriesPageLinkBlock()
        value = {
            "title": "",
            "description": "",
            "url": "https://invalid-domain.com/time-series",
        }

        expected_validation_error = (
            "The URL hostname is not in the list of allowed domains or their subdomains: "
            "domain1.com or domain2.example.com"
        )

        with self.assertRaises(StructBlockValidationError) as info:
            block.clean(value)

        self.assertEqual(info.exception.block_errors["title"].message, "This field is required.")
        self.assertEqual(info.exception.block_errors["description"].message, "This field is required.")
        self.assertEqual(info.exception.block_errors["url"].message, expected_validation_error)

        # Now, run validation on non-empty title and description and (the same) invalid URL
        value = {
            "title": "Title",
            "description": "Description",
            "url": "https://invalid-domain.com/time-series",
        }

        with self.assertRaises(StructBlockValidationError) as info:
            block.clean(value)

        self.assertNotIn("title", info.exception.block_errors)
        self.assertNotIn("description", info.exception.block_errors)
        self.assertEqual(info.exception.block_errors["url"].message, expected_validation_error)
