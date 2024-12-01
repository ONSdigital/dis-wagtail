from typing import ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import CharBlock, ListBlock, PageChooserBlock, StructBlock, URLBlock
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.snippets.models import register_snippet

from cms.core.fields import StreamField


# Custom LinkBlock to support both pages and URLs
class BaseLinkBlock(StructBlock):
    page = PageChooserBlock(required=False)
    url = URLBlock(required=False, label="URL")
    title = CharBlock(required=False, help_text="Optional. Displayed as the link text.")

    def clean(self, value: dict) -> dict:
        value = super().clean(value)
        if not value.get("page") and not value.get("url"):
            raise ValidationError("Either a page or a URL must be provided.")
        return value

    class Meta:
        abstract = True


class LinkBlock(BaseLinkBlock):
    class Meta:
        icon = "link"
        label = "Link"


class ThemeLinkBlock(BaseLinkBlock):
    page = PageChooserBlock(required=False, page_type="themes.ThemePage")

    class Meta:
        icon = "link"
        label = "Theme Link"


class TopicLinkBlock(BaseLinkBlock):
    page = PageChooserBlock(required=False, page_type="topics.TopicPage")

    class Meta:
        icon = "link"
        label = "Topic Link"


class HighlightsBlock(BaseLinkBlock):
    description = CharBlock(required=True, max_length=50, help_text="E.g., It's never been more important")

    def clean(self, value: dict) -> dict:
        value = super().clean(value)
        if not value.get("page") and not value.get("url"):
            raise ValidationError("Either a page or a URL must be provided.")
        if value.get("url") and not value.get("title"):
            raise ValidationError("Title is required if adding an external URL.")
        return value

    class Meta:
        icon = "star"
        label = "Highlight"


# Section StructBlock for columns
class SectionBlock(StructBlock):
    section_link = ThemeLinkBlock(help_text="Main link for this section (Theme pages or external URLs).")
    links = ListBlock(
        TopicLinkBlock(), help_text="Sub-links for this section (Topic pages or external URLs).", max_num=15
    )

    class Meta:
        icon = "folder"
        label = "Section"


# Column StructBlock for the main menu
class ColumnBlock(StructBlock):
    sections = ListBlock(SectionBlock(), label="Sections", max_num=3)

    class Meta:
        icon = "list-ul"
        label = "Column"


# MainMenu model
@register_snippet
class MainMenu(models.Model):
    highlights = StreamField(
        [("highlight", HighlightsBlock())],
        blank=True,
        max_num=3,
        help_text="Up to 3 highlights. Each highlight must have either a page or a URL.",
    )  # TO DO: Do we want to restrict highlights to theme pages only?
    columns = StreamField(
        [("column", ColumnBlock())],
        blank=True,
        max_num=3,
        help_text="Up to 3 columns. Each column contains sections with links.",
    )

    panels: ClassVar[list] = [
        FieldPanel("highlights"),
        FieldPanel("columns"),
    ]

    def __str__(self) -> str:
        return "Main Menu"

    def save(self, *args, **kwargs):
        if not self.pk and MainMenu.objects.exists():
            raise ValidationError("There can only be one Main Menu instance.")
        super().save(*args, **kwargs)


# NavigationSettings model
@register_setting(icon="list-ul")
class NavigationSettings(BaseSiteSetting):
    main_menu: models.ForeignKey = models.ForeignKey(
        MainMenu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Select the main menu to display on the site.",
    )

    panels: ClassVar[list] = [
        FieldPanel("main_menu"),
    ]
