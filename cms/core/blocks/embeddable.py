from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _
from wagtail import blocks
from wagtail.blocks import StructBlockValidationError
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue, StructValue


class ImageBlock(blocks.StructBlock):
    """Image block with caption."""

    image = ImageChooserBlock()
    caption = blocks.CharBlock(required=False)

    class Meta:
        icon = "image"
        template = "templates/components/streamfield/image_block.html"


class DocumentBlockStructValue(blocks.StructValue):
    """Bespoke StructValue to convert a struct block value to DS macro data."""

    def as_macro_data(self) -> dict[str, str | bool | dict]:
        """Return the value as a macro data dict."""
        return {
            "thumbnail": True,
            "title": {
                "text": self["title"] or self["document"].title,
                "url": self["document"].url,
            },
            "description": self["description"],
            "metadata": {
                "file": {
                    "fileType": self["document"].file_extension.upper(),
                    "fileSize": filesizeformat(self["document"].get_file_size()),
                }
            },
        }


class DocumentBlock(blocks.StructBlock):
    """Defines a DS document block."""

    document = DocumentChooserBlock()
    title = blocks.CharBlock(required=False)
    description = blocks.RichTextBlock(features=settings.RICH_TEXT_BASIC, required=False)

    class Meta:
        icon = "doc-full-inverse"
        value_class = DocumentBlockStructValue
        template = "templates/components/streamfield/document_block.html"


class DocumentsBlock(blocks.StreamBlock):
    """A documents 'list' StramBlock."""

    document = DocumentBlock()

    def get_context(self, value: "StreamValue", parent_context: dict | None = None) -> dict:
        """Inject the document list as DS component macros data."""
        context: dict = super().get_context(value, parent_context)
        context["macro_data"] = [document.value.as_macro_data() for document in value]
        return context

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"document": {"min_num": 1}}
        icon = "doc-full-inverse"
        template = "templates/components/streamfield/documents_block.html"


class ONSEmbedBlock(blocks.StructBlock):
    """An embed block for only pages starting with ONS_EMBED_PREFIX."""

    url = blocks.URLBlock(help_text=f"Must start with <code>{ settings.ONS_EMBED_PREFIX }</code> to your URL.")
    title = blocks.CharBlock(default="Interactive chart")

    def clean(self, value: "StructValue") -> "StructValue":
        """Checks that the given URL matches the ONS_EMBED_PREFIX."""
        errors = {}

        if not value["url"].startswith(settings.ONS_EMBED_PREFIX):
            errors["url"] = ValidationError(
                _("The URL must start with %(prefix)s") % {"prefix": settings.ONS_EMBED_PREFIX}
            )

        if errors:
            raise StructBlockValidationError(block_errors=errors)

        return super().clean(value)

    class Meta:
        icon = "code"
        template = "templates/components/streamfield/ons_embed_block.html"


class VideoEmbedBlock(blocks.StructBlock):
    """A video embed block."""

    embed_url = blocks.URLBlock(
        help_text="""
        The embed URL to the video hosted on YouTube or Vimeo, for example,
        https://www.youtube.com/embed/{ video ID } or https://player.vimeo.com/video/{ video ID }
        """
    )
    link_url = blocks.URLBlock(
        help_text="""
        The URL to the video hosted on YouTube or Vimeo, for example,
        https://www.youtube.com/watch?v={ video ID } or https://vimeo.com/video/{ video ID }.
        Used to link to the video when cookies are not enabled.
        """
    )
    image = ImageChooserBlock(help_text="The video cover image, used when cookies are not enabled.")
    title = blocks.CharBlock(
        help_text="""
        The descriptive title for the video used by screen readers.
        """
    )
    link_text = blocks.CharBlock(
        help_text="""
        The text to be shown when cookies are not enabled
        e.g. 'Watch the {title} on Youtube'.
        """
    )

    def clean(self, value: "StructValue") -> "StructValue":
        """Checks that the given embed and link urls match youtube or vimeo."""
        errors = {}

        if urlparse(value["embed_url"]).hostname not in [
            "www.vimeo.com",
            "vimeo.com",
            "player.vimeo.com",
            "www.youtube.com",
            "youtube.com",
        ]:
            errors["embed_url"] = ValidationError(_("The embed URL must use the vimeo.com or youtube.com domain"))

        if urlparse(value["link_url"]).hostname not in [
            "www.vimeo.com",
            "vimeo.com",
            "player.vimeo.com",
            "www.youtube.com",
            "youtube.com",
        ]:
            errors["link_url"] = ValidationError(_("The link URL must use the vimeo.com or youtube.com domain"))

        if errors:
            raise StructBlockValidationError(block_errors=errors)

        return super().clean(value)

    class Meta:
        icon = "code"
        template = "templates/components/streamfield/video_embed_block.html"
