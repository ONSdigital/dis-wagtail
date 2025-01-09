import re
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

    link_url = blocks.URLBlock(
        help_text=_(
            "The URL to the video hosted on YouTube or Vimeo, for example, "
            "https://www.youtube.com/watch?v={ video ID } or https://vimeo.com/video/{ video ID }. "
            "Used to link to the video when cookies are not enabled."
        )
    )
    image = ImageChooserBlock(help_text=_("The video cover image, used when cookies are not enabled."))
    title = blocks.CharBlock(help_text=_("The descriptive title for the video used by screen readers."))
    link_text = blocks.CharBlock(
        help_text=_("The text to be shown when cookies are not enabled e.g. 'Watch the {title} on Youtube'.")
    )

    def get_context(self, value: "StreamValue", parent_context: dict | None = None) -> dict:
        """Get the embed URL for the video based on the link URL."""
        context: dict = super().get_context(value, parent_context=parent_context)
        embed_url = ""
        # Vimeo
        if urlparse(value["link_url"]).hostname in ["www.vimeo.com", "vimeo.com", "player.vimeo.com"]:
            url_path = urlparse(value["link_url"]).path.strip("/")
            # Handle different Vimeo URL patterns
            if "video/" in url_path:
                # Handle https://vimeo.com/showcase/7934865/video/ID format
                video_id = url_path.split("video/")[-1]
            else:
                # Handle https://player.vimeo.com/video/ID or https://vimeo.com/ID format
                video_id = url_path.split("/")[0]
            # Remove any query parameters from video ID
            video_id = video_id.split("?")[0]
            embed_url = "https://player.vimeo.com/video/" + video_id
        # YouTube
        elif urlparse(value["link_url"]).hostname in ["www.youtube.com", "youtube.com", "youtu.be"]:
            url_parts = urlparse(value["link_url"])
            if url_parts.hostname == "youtu.be":
                # Handle https://youtu.be/ID format
                video_id = url_parts.path.lstrip("/")
            elif "/v/" in url_parts.path:
                # Handle https://www.youtube.com/v/ID format
                video_id = url_parts.path.split("/v/")[-1]
            else:
                # Handle https://www.youtube.com/watch?v=ID format
                query = dict(param.split("=") for param in url_parts.query.split("&"))
                video_id = query.get("v", "")
            # Remove any query parameters from video ID
            video_id = video_id.split("?")[0]
            embed_url = "https://www.youtube.com/embed/" + video_id
        context["value"]["embed_url"] = embed_url
        return context

    def clean(self, value: "StructValue") -> "StructValue":
        """Checks that the given embed and link urls match youtube or vimeo."""
        errors = {}

        vimeo_showcase_pattern = r"^https?://vimeo\.com/showcase/[^/]+/video/[^/]+$"
        other_patterns = [
            r"^https?://(?:[-\w]+\.)?youtube\.com/watch[^/]+$",
            r"^https?://(?:[-\w]+\.)?youtube\.com/v/[^/]+$",
            r"^https?://youtu\.be/[^/]+$",
            r"^https?://vimeo\.com/[^/]+$",
            r"^https?://player\.vimeo\.com/video/[^/]+$",
        ]

        # Check if the URL is a Vimeo showcase URL - do this first to avoid it clashing
        # with the r"^https?://vimeo\.com/[^/]+$", pattern
        if re.match(vimeo_showcase_pattern, value["link_url"]):
            return super().clean(value)

        if not any(re.match(pattern, value["link_url"]) for pattern in other_patterns):
            errors["link_url"] = ValidationError(_("The link URL must use a valid vimeo or youtube video URL"))

        if errors:
            raise StructBlockValidationError(block_errors=errors)

        return super().clean(value)

    class Meta:
        icon = "code"
        template = "templates/components/streamfield/video_embed_block.html"
