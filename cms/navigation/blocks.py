from django.utils.translation import gettext_lazy as _
from wagtail.blocks import CharBlock, ListBlock, PageChooserBlock, StructBlock

from cms.core.blocks.base import LinkBlock


class ThemeLinkBlock(LinkBlock):
    page = PageChooserBlock(required=False, page_type="themes.ThemePage")

    class Meta:
        label = _("Theme Link")


class TopicLinkBlock(LinkBlock):
    page = PageChooserBlock(required=False, page_type="topics.TopicPage")

    class Meta:
        label = _("Topic Link")


class MainMenuHighlightsBlock(LinkBlock):
    description = CharBlock(
        required=True, max_length=50, help_text=_("For example: 'View our latest and upcoming releases.'")
    )

    class Meta:
        icon = "star"
        label = _("Highlight")


class MainMenuSectionBlock(StructBlock):
    section_link = ThemeLinkBlock(help_text=_("Main link for this section (Theme pages or external URLs)."))
    links = ListBlock(
        TopicLinkBlock(),
        help_text=_("Sub-links for this section (Topic pages or external URLs)."),
        max_num=15,
    )

    class Meta:
        icon = "folder"
        label = _("Section")


class MainMenuColumnBlock(StructBlock):
    sections = ListBlock(MainMenuSectionBlock(), label="Sections", max_num=3)

    class Meta:
        icon = "list-ul"
        label = _("Column")


class LinksColumn(StructBlock):
    title = CharBlock(required=True, label=_("Column title"))
    links = ListBlock(
        LinkBlock(),
        help_text=_("Links for this column (pages or external URLs)."),
        max_num=10,
    )

    class Meta:
        label = "Links Column"
