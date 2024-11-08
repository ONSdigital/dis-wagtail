from django.test import TestCase

from cms.release_calendar.blocks import ContentSectionBlock


class ContentSectionBlockTests(TestCase):
    """Tests for the content section block."""

    def test_content_section_block_toc(self):
        """Check the content section table of contents."""
        block = ContentSectionBlock()
        value = block.to_python(
            {"title": "The section", "links": [{"external_url": "https://ons.gov.uk", "title": "test"}]}
        )
        self.assertListEqual(block.to_table_of_contents_items(value), [{"url": "#the-section", "text": "The section"}])
