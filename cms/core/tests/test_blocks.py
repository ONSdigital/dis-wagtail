import pytest
from django.conf import settings
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError

from cms.core.blocks import HeadingBlock, ONSEmbedBlock, RelatedContentBlock, RelatedLinksBlock

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "show_back_to_toc",
    [None, False, True],
)
def test_headingblock__get_context(show_back_to_toc):
    """Checks that the headingblock context has the TOC."""
    block = HeadingBlock(show_back_to_toc=show_back_to_toc)
    value = block.to_python("The Heading")

    assert block.get_context(value)["show_back_to_toc"] == show_back_to_toc


def test_headingblock__toc():
    """Checks the headingblock TOC."""
    block = HeadingBlock()
    value = block.to_python("The Heading")

    assert block.to_table_of_contents_items(value) == [{"url": "#the-heading", "text": "The Heading"}]


def test_onsemebedblock__clean():
    """Check the ONSEmbedBlock validates the supplied URL."""
    block = ONSEmbedBlock()

    with pytest.raises(StructBlockValidationError) as info:
        value = block.to_python(
            {
                "url": "https://ons.gov.uk",
            }
        )
        block.clean(value)

    assert info.value.block_errors["url"].message == f"The URL must start with {settings.ONS_EMBED_PREFIX}"


def test_relatedcontentblock_clean__no_page_nor_url():
    """Checks that the RelatedContentBlock validates that one of page or URL is supplied."""
    block = RelatedContentBlock()
    value = block.to_python({})

    with pytest.raises(StreamBlockValidationError) as info:
        block.clean(value)

    assert info.value.block_errors["page"].message == "Either Page or External Link is required."
    assert info.value.block_errors["external_url"].message == "Either Page or External Link is required."


def test_relatedcontentblock_clean__page_and_url():
    """Checks that the RelatedContentBlock validates either page or URL is supplied."""
    block = RelatedContentBlock()
    value = block.to_python(
        {
            "page": 1,
            "external_url": "https://ons.gov.uk",
        }
    )

    with pytest.raises(StreamBlockValidationError) as info:
        block.clean(value)

    assert info.value.block_errors["page"].message == "Please select either a page or a URL, not both."
    assert info.value.block_errors["external_url"].message == "Please select either a page or a URL, not both."


def test_relatedcontentblock_clean__url_no_title():
    """Checks that the title is supplied if checking an external url."""
    block = RelatedContentBlock()
    value = block.to_python(
        {
            "external_url": "https://ons.gov.uk",
        }
    )

    with pytest.raises(StreamBlockValidationError) as info:
        block.clean(value)

    assert info.value.block_errors["title"].message == "Title is required for external links."


def test_relatedcontentblock_clean__happy_path():
    """Happy path for the RelatedContentBlock validation."""
    block = RelatedContentBlock()
    value = block.to_python({"external_url": "https://ons.gov.uk", "title": "The link", "description": ""})

    assert block.clean(value) == value


def test_relatedcontentblock_clean__link_value(home_page):
    """Checks the RelatedContentValue link value."""
    block = RelatedContentBlock()

    value = block.to_python({})
    assert value.link is None

    value = block.to_python(
        {
            "external_url": "https://ons.gov.uk",
            "title": "Example",
            "description": "A link",
        }
    )

    assert value.link == {
        "url": "https://ons.gov.uk",
        "text": "Example",
        "description": "A link",
    }

    value = block.to_python(
        {
            "page": home_page.pk,
            "title": "Example",
            "description": "A link",
        }
    )

    assert value.link == {
        "url": home_page.url,
        "text": "Example",
        "description": "A link",
    }

    value = block.to_python(
        {
            "page": home_page.pk,
        }
    )

    assert value.link == {
        "url": home_page.url,
        "text": home_page.title,
        "description": "",
    }


def test_relatedlinksblock__get_context():
    """Check that RelatedLinksBlock heading and slug are in the context."""
    block = RelatedLinksBlock(child_block=RelatedContentBlock)
    value = block.to_python([])

    context = block.get_context(value)
    assert context["heading"] == "Related links"
    assert context["slug"] == "related-links"


def test_relatedlinksblock__toc():
    """Check the RelatedLinksBlock TOC."""
    block = RelatedLinksBlock(child_block=RelatedContentBlock)
    value = block.to_python([])
    assert block.to_table_of_contents_items(value) == [{"url": "#related-links", "text": "Related links"}]
