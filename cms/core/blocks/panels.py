from django.conf import settings
from django.utils.translation import gettext_lazy as _
from wagtail import blocks


class WarningPanelBlock(blocks.StructBlock):
    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        context: dict = super().get_context(value, parent_context)
        context["variant"] = "warn"
        return context

    class Meta:
        template = "templates/components/streamfield/warn_announcement_panel.html"
        label = _("Warning Panel")
        group = _("Panels")


class InformationPanelBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, label=_("Title"))
    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        context: dict = super().get_context(value, parent_context)
        context["variant"] = "info"
        return context

    class Meta:
        template = "templates/components/streamfield/information_panel.html"
        label = _("Information Panel")
        group = _("Panels")


class AnnouncementPanelBlock(blocks.StructBlock):
    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)

    def get_context(self, value: dict, parent_context: dict | None = None) -> dict:
        context: dict = super().get_context(value, parent_context)
        context["variant"] = "announcement"
        return context

    class Meta:
        template = "templates/components/streamfield/warn_announcement_panel.html"
        label = _("Announcement Panel")
        group = _("Panels")
