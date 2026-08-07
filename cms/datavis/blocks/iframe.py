import uuid
from typing import TYPE_CHECKING, Any
from urllib.parse import ParseResult, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail import blocks

from cms.core.blocks.struct_blocks import RelativeOrAbsoluteURLBlock
from cms.core.url_utils import is_hostname_in_domain
from cms.datavis.blocks.base import BaseVisualisationBlock

if TYPE_CHECKING:
    from wagtail.blocks.struct_block import StructValue


class IframeBlock(BaseVisualisationBlock):
    # Overrides title in BaseVisualisationBlock as it is not required for the iframe
    title = blocks.CharBlock(required=False)
    iframe_source_url = RelativeOrAbsoluteURLBlock(
        required=True,
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
        help_text=(
            "A brief but descriptive label for the embed, for example "
            "“Bar chart of GDP per region” or “Interactive personal inflation calculator tool”"
        ),
    )
    # Overrides audio_description in BaseVisualisationBlock in order to update the help text
    audio_description = blocks.TextBlock(
        required=True,
        help_text=(
            "An overview of what the embed shows for screen reader users, for example"
            " “GDP is the highest in London and lowest in the North East” or"
            " “Inputs for users to describe what their household spends on different categories, which gives an"
            " estimate of how much monthly spend has increased over the past year and compares to previous years”"
        ),
        label="Accessible description",
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
        """Validate the source URL of the iframe. Validation errors are returned as an errors dict.
        The URL can be either absolute (with scheme and hostname) or relative (path only).
        """
        source_url = value["iframe_source_url"]
        if not source_url:
            return {"iframe_source_url": ValidationError("Please enter a valid URL.")}

        parsed_url = urlparse(source_url)

        if parsed_url.scheme or parsed_url.netloc:
            # If a scheme or netloc is present, validate as an absolute URL
            return self._validate_absolute_source_url(parsed_url, source_url=source_url)

        # Otherwise, validate as a relative URL path
        return self._validate_source_url_path(parsed_url)

    def _validate_absolute_source_url(self, parsed_url: ParseResult, *, source_url: str) -> dict[str, ValidationError]:
        """Validate the absolute source URL of the iframe. Validation errors are returned as an errors dict."""
        errors = {}
        allowed_domains = " or ".join(settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS)

        # Check the original source_url string scheme here, as URL parse is permissive of malformed schemes
        if not (source_url.startswith("https://") and parsed_url.hostname):
            errors["iframe_source_url"] = ValidationError(
                "Please enter a valid URL. Full URLs must start with 'https://'."
            )
        elif not any(
            is_hostname_in_domain(parsed_url.hostname, allowed_domain)
            for allowed_domain in settings.IFRAME_VISUALISATION_ALLOWED_DOMAINS
        ):
            errors["iframe_source_url"] = ValidationError(
                f"The URL hostname is not in the list of allowed domains: {allowed_domains}"
            )
        else:
            path_errors = self._validate_source_url_path(parsed_url)
            errors.update(path_errors)

        return errors

    @staticmethod
    def _validate_source_url_path(parsed_url: ParseResult) -> dict[str, ValidationError]:
        """Validate the path of the iframe source URL. Validation errors are returned as an errors dict."""
        errors = {}
        url_path = parsed_url.path.rstrip("/")
        allowed_prefixes = [prefix.rstrip("/") for prefix in settings.IFRAME_VISUALISATION_PATH_PREFIXES]

        if not any(
            url_path.startswith(prefix + "/") and len(url_path) > len(prefix) + 1 for prefix in allowed_prefixes
        ):
            readable_prefixes = " or ".join(settings.IFRAME_VISUALISATION_PATH_PREFIXES)
            errors["iframe_source_url"] = ValidationError(
                f"The URL path is not allowed. It must start with: {readable_prefixes}, "
                "and include a subpath after the prefix."
            )
        return errors

    def get_figure_config(self, value: StructValue) -> dict[str, Any]:
        config = {
            "figureNumber": value.get("figure_number"),
            "headingLevel": 3,
            "title": value.get("title"),
            "subtitle": value.get("subtitle"),
            "caption": _("Source") + ": " + value.get("caption") if value.get("caption") else None,
            "audioDescription": value.get("audio_description"),
        }

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

        context["figure_config"] = self.get_figure_config(value)
        # fallback is only when block_id is not available, which should not happen in normal usage
        context["figure_config"]["id"] = f"{context.get('block_id') or uuid.uuid4().hex[:8]}"
        context["iframe_config"] = self.get_iframe_config(value)
        return context
