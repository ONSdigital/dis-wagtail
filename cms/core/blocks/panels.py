from django.conf import settings
from wagtail import blocks


class PanelBlock(blocks.StructBlock):
    variant = blocks.ChoiceBlock(
        choices=[
            ("announcement", "Announcement"),
            ("bare", "Bare"),
            ("branded", "Branded"),
            ("error", "Error"),
            ("ghost", "Ghost"),
            ("success", "Success"),
            ("warn-branded", "Warn (branded)"),
            ("warn", "Warn"),
        ],
        default="warn",
    )
    body = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC)
    title = blocks.CharBlock(required=False, label="Title (optional)")

    class Meta:
        label = "Warning or information panel"
        template = "templates/components/streamfield/panel_block.html"