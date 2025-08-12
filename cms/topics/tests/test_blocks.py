from django.conf import settings
from django.test import TestCase
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.blocks.stream_block import StreamValue
from wagtail.images.tests.utils import get_test_image_file

from cms.datasets.blocks import TimeSeriesPageLinkBlock, TimeSeriesPageStoryBlock
from cms.home.models import HomePage
from cms.images.models import CustomImage
from cms.themes.tests.factories import ThemePageFactory
from cms.topics.blocks import ExploreMoreExternalLinkBlock, ExploreMoreInternalLinkBlock, ExploreMoreStoryBlock
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

        with self.assertRaises(StreamBlockValidationError):
            block.clean(stream_value)


class TimeSeriesPageLinkBlockTestCase(TestCase):
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
            f"The time series page URL must start with {settings.TIME_SERIES_PAGE_ALLOWED_DOMAIN}",
        )
