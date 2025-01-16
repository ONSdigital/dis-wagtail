from typing import TYPE_CHECKING, ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import CharBlock, ListBlock, PageChooserBlock, StructBlock
from wagtail.contrib.settings.models import register_setting
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin

from cms.core.blocks.base import LinkBlock
from cms.core.fields import StreamField
from cms.core.models import BaseSiteSetting

MAIN_MENU_MAX_NUM_HIGHLIGHTS = 3
MAIN_MENU_MAX_NUM_COLUMNS = 3
MAIN_MENU_MAX_NUM_SECTIONS = 3
MAIN_MENU_MAX_NUM_TOPIC_LINKS = 15

if TYPE_CHECKING:
    from django.http import HttpRequest


class ThemeLinkBlock(LinkBlock):
    page = PageChooserBlock(required=False, page_type="themes.ThemePage")

    class Meta:
        label = _("Theme Link")


class TopicLinkBlock(LinkBlock):
    page = PageChooserBlock(required=False, page_type="topics.TopicPage")

    class Meta:
        label = _("Topic Link")


class HighlightsBlock(LinkBlock):
    description = CharBlock(
        required=True, max_length=50, help_text=_("For example: 'View our latest and upcoming releases.'")
    )

    class Meta:
        icon = "star"
        label = _("Highlight")


class SectionBlock(StructBlock):
    section_link = ThemeLinkBlock(help_text=_("Main link for this section (Theme pages or external URLs)."))
    links = ListBlock(
        TopicLinkBlock(),
        help_text=_("Sub-links for this section (Topic pages or external URLs)."),
        max_num=MAIN_MENU_MAX_NUM_TOPIC_LINKS,
    )

    class Meta:
        icon = "folder"
        label = _("Section")


class ColumnBlock(StructBlock):
    sections = ListBlock(SectionBlock(), label="Sections", max_num=MAIN_MENU_MAX_NUM_SECTIONS)

    class Meta:
        icon = "list-ul"
        label = _("Column")


class MainMenu(DraftStateMixin, RevisionMixin, PreviewableMixin, models.Model):
    highlights = StreamField(
        [("highlight", HighlightsBlock())],
        blank=True,
        max_num=MAIN_MENU_MAX_NUM_HIGHLIGHTS,
        help_text=_("Up to 3 highlights. Each highlight must have either a page or a URL."),
    )
    columns = StreamField(
        [("column", ColumnBlock())],
        blank=True,
        max_num=MAIN_MENU_MAX_NUM_COLUMNS,
        help_text=_("Up to 3 columns. Each column contains sections with links."),
    )

    panels: ClassVar[list] = [
        FieldPanel("highlights"),
        FieldPanel("columns"),
    ]

    def get_preview_template(self, request: "HttpRequest", mode_name: str) -> str:
        return "templates/components/navigation/main_menu_preview.html"

    def __str__(self) -> str:
        return "Main Menu"


@register_setting(icon="list-ul")
class NavigationSettings(BaseSiteSetting):
    main_menu: models.ForeignKey = models.ForeignKey(
        MainMenu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=_("Select the main menu to display on the site."),
    )

    panels: ClassVar[list] = [
        FieldPanel("main_menu"),
    ]
