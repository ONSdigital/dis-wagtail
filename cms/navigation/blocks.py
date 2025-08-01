from typing import Any

from wagtail.blocks import CharBlock, ListBlock, PageChooserBlock, StructBlock, URLBlock

from cms.core.blocks.base import LinkBlock


class ThemeLinkBlock(LinkBlock):
    page = PageChooserBlock(required=False, page_type="themes.ThemePage")

    # TODO: day 2, remove external_url, title overrides when allowing Theme page creation
    external_url = URLBlock(required=True, label="External Link")
    title = CharBlock(required=True)

    # TODO: day 2, remove this __init__ when we allow creating Theme pages
    def __init__(self, **kwargs: Any) -> None:
        if "page" in self.base_blocks:  # pylint: disable=no-member
            del self.base_blocks["page"]  # pylint: disable=no-member

        super().__init__(**kwargs)

    class Meta:
        label = "Theme Link"


class TopicLinkBlock(LinkBlock):
    page = PageChooserBlock(required=False, page_type="topics.TopicPage")

    class Meta:
        label = "Topic Link"


class MainMenuHighlightsBlock(LinkBlock):
    description = CharBlock(
        required=True, max_length=50, help_text="For example: 'View our latest and upcoming releases.'"
    )

    class Meta:
        icon = "star"
        label = "Highlight"


class MainMenuSectionBlock(StructBlock):
    section_link = ThemeLinkBlock(help_text="Main link for this section (Theme pages or external URLs).")
    links = ListBlock(
        TopicLinkBlock(),
        help_text="Sub-links for this section (Topic pages or external URLs).",
        max_num=15,
    )

    class Meta:
        icon = "folder"
        label = "Section"


class MainMenuColumnBlock(StructBlock):
    sections = ListBlock(MainMenuSectionBlock(), label="Sections", max_num=3)

    class Meta:
        icon = "list-ul"
        label = "Column"


class LinksColumn(StructBlock):
    title = CharBlock(required=True, label="Column title")
    links = ListBlock(
        LinkBlock(),
        help_text="Links for this column (pages or external URLs).",
        max_num=10,
    )

    class Meta:
        label = "Links Column"
