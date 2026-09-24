import os
import uuid
from typing import TYPE_CHECKING, Any
from urllib.parse import ParseResult, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail import blocks

from cms.core.analytics_utils import get_gtm_attributes_file_download
from cms.core.blocks.struct_blocks import RelativeOrAbsoluteURLBlock
from cms.core.url_utils import is_hostname_in_domain
from cms.datavis.blocks.base import BaseVisualisationBlock

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.blocks.struct_block import StructValue


def _validate_visualisation_url(url: str, *, field_name: str) -> dict[str, ValidationError]:
    """Validate an iframe source URL or download URL. Validation errors are returned as an errors dict. The URL can be
    either absolute (with scheme and hostname) or relative (path only).
    """
    parsed_url = urlparse(url)

    if parsed_url.scheme or parsed_url.netloc:
        # If a scheme or netloc is present, validate as an absolute URL
        return _validate_absolute_visualisation_url(parsed_url, url=url, field_name=field_name)

    # Otherwise, validate as a relative URL path
    return _validate_visualisation_url_path(parsed_url, field_name=field_name)


def _validate_absolute_visualisation_url(
    parsed_url: ParseResult, *, url: str, field_name: str
) -> dict[str, ValidationError]:
    """Validate an absolute iframe source URL or download URL. Validation errors are returned as an errors dict."""
    errors = {}
    allowed_domains = " or ".join(settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS)

    # Check the original `url` string scheme here, as URL parse is permissive of malformed schemes
    if not (url.startswith("https://") and parsed_url.hostname):
        errors[field_name] = ValidationError("Please enter a valid URL. Full URLs must start with 'https://'.")
    elif not any(
        is_hostname_in_domain(parsed_url.hostname, allowed_domain)
        for allowed_domain in settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS
    ):
        errors[field_name] = ValidationError(
            f"The URL hostname is not in the list of allowed domains: {allowed_domains}"
        )
    else:
        path_errors = _validate_visualisation_url_path(parsed_url, field_name=field_name)
        errors.update(path_errors)

    return errors


def _validate_visualisation_url_path(parsed_url: ParseResult, *, field_name: str) -> dict[str, ValidationError]:
    """Validate the path of an iframe source URL or download URL. Validation errors are returned as an errors dict."""
    errors = {}
    url_path = parsed_url.path.rstrip("/")
    allowed_prefixes = [prefix.rstrip("/") for prefix in settings.IFRAME_VISUALISATION_PATH_PREFIXES]

    if not any(url_path.startswith(prefix + "/") and len(url_path) > len(prefix) + 1 for prefix in allowed_prefixes):
        readable_prefixes = " or ".join(settings.IFRAME_VISUALISATION_PATH_PREFIXES)
        errors[field_name] = ValidationError(
            f"The URL path is not allowed. It must start with: {readable_prefixes}, "
            "and include a subpath after the prefix."
        )
    return errors


class DownloadBlock(blocks.StructBlock):
    url = RelativeOrAbsoluteURLBlock(required=False)

    def __init__(self, local_blocks=None, search_index=True, *, link_text_help_text=None, **kwargs):
        # Inject link_text here so each block instance can provide its own help text.
        local_blocks = list(local_blocks or [])
        local_blocks.append(
            (
                "link_text",
                blocks.CharBlock(
                    required=False,
                    help_text=link_text_help_text,
                ),
            )
        )
        super().__init__(local_blocks=local_blocks, search_index=search_index, **kwargs)

    def _validate_download_url(self, value: StructValue) -> dict[str, ValidationError]:
        """Validate a download URL. Validation errors are returned as an errors dict. The URL can be either
        absolute (with scheme and hostname) or relative (path only).
        """
        return _validate_visualisation_url(
            (value.get("url") or "").strip(),
            field_name="url",
        )

    def clean(self, value: StructValue) -> StructValue:
        errors = {}
        url = (value.get("url") or "").strip()
        link_text = (value.get("link_text") or "").strip()

        if url and not link_text:
            errors |= {"link_text": ValidationError("Link text is required when a URL is provided.")}

        if link_text and not url:
            errors |= {"url": ValidationError("A URL is required when link text is provided.")}

        if url:
            errors |= self._validate_download_url(value)

        if errors:
            raise blocks.StructBlockValidationError(errors)
        return super().clean(value)


class IframeBlock(BaseVisualisationBlock):
    # Overrides title in BaseVisualisationBlock as it is not required for the iframe
    title = blocks.CharBlock(required=False)
    iframe_source_url = RelativeOrAbsoluteURLBlock(
        required=True,
        required_on_save=True,
        help_text=(
            "Enter the full URL or relative URL path (preferred) of the visualisation you want to embed. "
            "A full URL must start with <code>https://</code>, the hostname must match one of the allowed domains. "
            "The URL path must start with an allowed prefix for both full or relative URLs. "
            f"Allowed domains: "
            f"{' or '.join(f'<code>{d}</code>' for d in settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS)}. "
            f"Allowed path prefixes: "
            f"{' or '.join(f'<code>{p}</code>' for p in settings.IFRAME_VISUALISATION_PATH_PREFIXES)}."
        ),
    )
    # Used in the iframe title attribute
    accessible_label = blocks.CharBlock(
        required=True,
        required_on_save=True,
        help_text=(
            "A brief but descriptive label for the embed, for example "
            "“Bar chart of GDP per region” or “Interactive personal inflation calculator tool”"
        ),
    )
    # Overrides audio_description in BaseVisualisationBlock in order to update the help text
    audio_description = blocks.TextBlock(
        required=True,
        required_on_save=True,
        help_text=(
            "An overview of what the embed shows for screen reader users, for example"
            " “GDP is the highest in London and lowest in the North East” or"
            " “Inputs for users to describe what their household spends on different categories, which gives an"
            " estimate of how much monthly spend has increased over the past year and compares to previous years”"
        ),
        label="Accessible description",
    )

    image_download = DownloadBlock(
        required=False,
        label="Image download",
        link_text_help_text=(
            "This should always follow the format 'Download image (23KB)', with the correct file "
            "size substituted. The file size suffix should be capitalised."
        ),
    )

    data_download = DownloadBlock(
        required=False,
        label="Data download",
        link_text_help_text=(
            "This should always follow the format 'Download CSV (23KB)', with the correct file "
            "type and file size substituted. The file type and file size suffix should be "
            "capitalised."
        ),
    )

    class Meta:
        template = "templates/components/streamfield/datavis/iframe_visualisation_block.html"
        icon = "code"
        form_layout = [  # noqa
            "figure_number",
            "title",
            "subtitle",
            "accessible_label",
            "audio_description",
            "iframe_source_url",
            "caption",
            "footnotes",
            "image_download",
            "data_download",
        ]

    def clean(self, value: StructValue) -> StructValue:
        errors = {}

        for field_name, field in self.child_blocks.items():
            if field.required and not value.get(field_name):
                errors[field_name] = ValidationError("This field is required.")

        errors |= self._validate_subtitle(value)
        errors |= self._validate_source_url(value)

        if errors:
            raise blocks.StructBlockValidationError(errors)

        return super().clean(value)

    @staticmethod
    def _validate_subtitle(value: StructValue) -> dict[str, ValidationError]:
        """Validate that a subtitle is only present when a title is also provided."""
        if value.get("subtitle") and not value.get("title"):
            return {"subtitle": ValidationError("Please add a title if you want to add a subtitle.")}
        return {}

    def _validate_source_url(self, value: StructValue) -> dict[str, ValidationError]:
        """Validate the iframe source URL. Validation errors are returned as an errors dict. The URL can be either
        absolute (with scheme and hostname) or relative (path only).
        """
        source_url = value.get("iframe_source_url")

        if not source_url:
            return {"iframe_source_url": ValidationError("Please enter a valid URL.")}

        return _validate_visualisation_url(
            source_url,
            field_name="iframe_source_url",
        )

    @staticmethod
    def _get_download_item(download: StructValue | None, request: HttpRequest | None) -> dict[str, str] | None:
        url = (download.get("url") or "").strip() if download else ""
        link_text = (download.get("link_text") or "").strip() if download else ""

        if not url or not link_text:
            return None

        absolute_csv_url = (
            request.build_absolute_uri(url) if request and not getattr(request, "is_preview", False) else url
        )
        file_name = os.path.basename(urlparse(url).path)
        _base, ext = os.path.splitext(file_name)

        attributes = get_gtm_attributes_file_download(
            text=link_text,
            url=absolute_csv_url,
            file_extension=ext.lstrip("."),
            file_name=file_name,
            file_size_kb=None,
        )

        return {"text": link_text, "url": url, "download": "file", "attributes": attributes}

    def _get_download_config(self, value: StructValue, request: HttpRequest | None = None) -> dict[str, Any] | None:
        items = [
            item
            for item in [
                self._get_download_item(value.get("image_download"), request),
                self._get_download_item(value.get("data_download"), request),
            ]
            if item
        ]

        if not items:
            return None

        return {
            "title": _("Downloads"),
            "itemsList": items,
        }

    def get_figure_config(self, value: StructValue, parent_context: dict[str, Any] | None = None) -> dict[str, Any]:
        request = parent_context.get("request") if parent_context else None
        config = {
            "figureNumber": value.get("figure_number"),
            "headingLevel": 3,
            "title": value.get("title"),
            "subtitle": value.get("subtitle"),
            "caption": _("Source") + ": " + value.get("caption") if value.get("caption") else None,
            "audioDescription": value.get("audio_description"),
        }

        if download := self._get_download_config(value, request=request):
            config["download"] = download

        # Check for meaningful text before displaying footnotes
        if (footnotes := value.get("footnotes")) and strip_tags(str(footnotes)).strip():
            config["footnotes"] = {
                "title": _("Footnotes"),
                "content": str(footnotes),
            }

        return config

    def get_iframe_config(self, value: StructValue) -> dict[str, Any]:
        config = {
            "iframeUrl": value.get("iframe_source_url"),
            "iframeTitle": value.get("accessible_label"),
        }
        return config

    def get_context(self, value: StructValue, parent_context: dict[str, Any] | None = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)

        context["figure_config"] = self.get_figure_config(value, parent_context=parent_context)
        # fallback is only when block_id is not available, which should not happen in normal usage
        context["figure_config"]["id"] = f"{context.get('block_id') or uuid.uuid4().hex[:8]}"
        context["iframe_config"] = self.get_iframe_config(value)
        return context
