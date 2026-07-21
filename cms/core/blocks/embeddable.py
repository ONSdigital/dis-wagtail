import os
import re
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.blocks import StructBlockValidationError
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue, StructValue


class ImageBlock(blocks.StructBlock):
    """Image block with caption."""

    image = ImageChooserBlock()
    alternative_text = blocks.CharBlock(
        required=False,
        label="Alternative text",
        help_text=(
            "A description of what the image shows for screen reader users. "
            "If this field is left blank, alt text will be sourced from the mandatory "
            "'alternative text' field when the image was uploaded to Wagtail"
        ),
    )
    figure_number = blocks.CharBlock(
        required=False, label="Figure number", help_text="Include a label for the figure, for example Figure 1."
    )
    figure_title = blocks.CharBlock(required=False, label="Title")
    figure_subtitle = blocks.CharBlock(required=False, label="Subtitle")
    supporting_text = blocks.TextBlock(required=False, label="Source text")
    notes_section = blocks.RichTextBlock(required=False, features=settings.RICH_TEXT_BASIC, label="Footnotes")
    decorative_image = blocks.BooleanBlock(
        required=False,
        label="Image is decorative, so alt text should be empty",
    )
    download = blocks.BooleanBlock(required=False, label="Show image download link")

    def clean(self, value: StructValue) -> StructValue:
        errors = {}
        if value.get("decorative_image") and value.get("alternative_text"):
            errors["alternative_text"] = ValidationError(
                "Alternative text must be empty when the image is marked as decorative."
            )
        if errors:
            raise StructBlockValidationError(block_errors=errors)
        return super().clean(value)

    def get_context(self, value: StreamValue, parent_context: dict | None = None) -> dict:
        context: dict = super().get_context(value, parent_context)

        # Guard: image may be missing at render time if the asset was
        # deleted after publishing (accidental or otherwise). Return early
        # to avoid calling get_rendition() on a None value.
        image = value.get("image")
        if not image:
            return context

        small = image.get_rendition("width-1024")
        large = image.get_rendition("width-2048")

        _base, ext = os.path.splitext(large.file.name)
        file_type = ext.lstrip(".").upper() or "IMG"
        size_bytes = getattr(large.file, "size", None)
        file_size_human = filesizeformat(size_bytes) if size_bytes is not None else None

        options = {
            "id": f"image-{context.get('block_id') or ''}",
            "headingLevel": 3,
            "figureNumber": value.get("figure_number"),
            "title": value.get("figure_title"),
            "subtitle": value.get("figure_subtitle"),
            "image": {
                "smallSrc": small.url,
                "largeSrc": large.url,
            },
            "alt": "" if value.get("decorative_image") else (value.get("alternative_text") or image.description),
            "caption": _("Source") + ": " + value.get("supporting_text") if value.get("supporting_text") else None,
        }

        if (notes := value.get("notes_section")) and strip_tags(str(notes)).strip():
            options["footnotes"] = {"title": _("Footnotes"), "content": notes}

        if value.get("download"):
            size_text = f" ({file_size_human})" if file_size_human else ""
            options["download"] = {
                "title": _("Download this image"),
                "itemsList": [{"text": f"{file_type}{size_text}", "url": large.url, "download": "file"}],
            }

        context["options"] = options
        return context

    class Meta:
        icon = "image"
        template = "templates/components/streamfield/image_block.html"
        form_layout = [  # noqa
            "figure_number",
            "figure_title",
            "figure_subtitle",
            "alternative_text",
            "decorative_image",
            "image",
            "supporting_text",
            "notes_section",
            "download",
        ]


class DocumentBlockStructValue(blocks.StructValue):
    """Bespoke StructValue to convert a struct block value to DS macro data."""

    def as_macro_data(self) -> dict[str, str | bool | dict]:
        """Return the value as a macro data dict."""
        return {
            "thumbnail": False,
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
            "attributes": {
                "data-ga-event": "file-download",
                "data-ga-file-extension": self["document"].file_extension.lower(),
                "data-ga-file-name": self["document"].title,
                "data-ga-link-text": self["title"] or self["document"].title,
                "data-ga-link-url": self["document"].url,
                "data-ga-link-domain": urlparse(self["document"].url).hostname,
                "data-ga-file-size": str(self["document"].get_file_size() / 1000),  # Convert from Bytes to KB
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
    """A documents 'list' StreamBlock."""

    document = DocumentBlock()

    def get_context(self, value: StreamValue, parent_context: dict | None = None) -> dict:
        """Inject the document list as DS component macros data."""
        context: dict = super().get_context(value, parent_context)
        context["macro_data"] = [document.value.as_macro_data() for document in value]
        return context

    class Meta:
        block_counts: ClassVar[dict[str, dict]] = {"document": {"min_num": 1}}
        icon = "doc-full-inverse"
        template = "templates/components/streamfield/documents_block.html"


class VideoEmbedBlock(blocks.StructBlock):
    """A video embed block."""

    link_url = blocks.URLBlock(
        help_text=(
            "The URL to the video hosted on YouTube or Vimeo, for example, "
            "https://www.youtube.com/watch?v={ video ID } or https://vimeo.com/video/{ video ID }. "
            "Used to link to the video when cookies are not enabled."
        )
    )
    image = ImageChooserBlock(help_text="The video cover image, used when cookies are not enabled.")
    title = blocks.CharBlock(help_text="The descriptive title for the video used by screen readers.")
    link_text = blocks.CharBlock(
        help_text="The text to be shown when cookies are not enabled e.g. 'Watch the {title} on Youtube'."
    )

    def get_embed_url(self, link_url: str) -> str:
        """Get the embed URL for the video based on the link URL."""
        embed_url = ""
        # Vimeo
        if urlparse(link_url).hostname in ["www.vimeo.com", "vimeo.com", "player.vimeo.com"]:
            url_path = urlparse(link_url).path.strip("/")
            # Handle different Vimeo URL patterns
            if "video/" in url_path:  # noqa: SIM108
                # Handle https://vimeo.com/showcase/7934865/video/ID format
                video_id = url_path.split("video/")[-1]
            else:
                # Handle https://player.vimeo.com/video/ID or https://vimeo.com/ID format
                video_id = url_path.split("/")[0]
            # Remove any query parameters from video ID
            video_id = video_id.split("?")[0]
            embed_url = "https://player.vimeo.com/video/" + video_id
        # YouTube
        elif urlparse(link_url).hostname in ["www.youtube.com", "youtube.com", "youtu.be"]:
            url_parts = urlparse(link_url)
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
        return embed_url

    def get_context(self, value: StreamValue, parent_context: dict | None = None) -> dict:
        """Get the embed URL for the video based on the link URL."""
        context: dict = super().get_context(value, parent_context=parent_context)
        context["value"]["embed_url"] = self.get_embed_url(value["link_url"])
        return context

    def clean(self, value: StructValue) -> StructValue:
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
            errors["link_url"] = ValidationError("The link URL must use a valid Vimeo or YouTube video URL")

        if errors:
            raise StructBlockValidationError(block_errors=errors)

        return super().clean(value)

    class Meta:
        icon = "code"
        template = "templates/components/streamfield/video_embed_block.html"
