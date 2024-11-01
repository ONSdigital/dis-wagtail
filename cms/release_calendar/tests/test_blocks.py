from cms.release_calendar.blocks import ContentSectionBlock


def test_content_section_block_toc():
    """Check the content section table of contents."""
    block = ContentSectionBlock()
    value = block.to_python(
        {"title": "The section", "links": [{"external_url": "https://ons.gov.uk", "title": "test"}]}
    )
    assert block.to_table_of_contents_items(value) == [{"url": "#the-section", "text": "The section"}]
