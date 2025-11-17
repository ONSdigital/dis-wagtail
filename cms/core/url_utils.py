from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from wagtail.blocks import FieldBlock, StructValue


def is_hostname_in_domain(hostname: str, allowed_domain: str) -> bool:
    """Check if the hostname matches the allowed domain or its subdomains."""
    return hostname == allowed_domain or hostname.endswith(f".{allowed_domain}")


def validate_ons_url_struct_block(
    value: StructValue, child_blocks: dict[str, FieldBlock]
) -> dict[str, ValidationError]:
    """Custom validation for StructBlocks containing a URLBlock restricted to ONS domains.

    Note: Checks for the presence of the required fields are included here
    so that missing required field errors and custom URL validation errors can be raised simultaneously.
    """
    errors = {}

    for child_block in child_blocks.values():
        if child_block.required and not value.get(child_block.name):
            errors[child_block.name] = ValidationError("This field is required.")

    if not errors.get("url") and (error := validate_ons_url(value["url"])):
        errors["url"] = error

    return errors


def validate_ons_url(url: str) -> ValidationError | None:
    """Checks that the given URL matches the allowed ONS domain,
    otherwise return a dict holding a ValidationError to be used in the clean method of a StructBlock.
    """
    error = None
    parsed_url = urlparse(url)

    if not parsed_url.hostname or parsed_url.scheme != "https":
        error = ValidationError(
            "Please enter a valid URL. It should start with 'https://' and contain a valid domain name."
        )
    elif not any(
        is_hostname_in_domain(parsed_url.hostname, allowed_domain)
        for allowed_domain in settings.ONS_ALLOWED_LINK_DOMAINS
    ):
        patterns_str = " or ".join(settings.ONS_ALLOWED_LINK_DOMAINS)
        error = ValidationError(
            f"The URL hostname is not in the list of allowed domains or their subdomains: {patterns_str}"
        )

    return error


def normalise_url(url: str) -> str:
    """Normalise functionally equivalent URLs for comparison
    when checking for duplicates across StreamValue entities.
    """
    url = url.lower().rstrip("/")  # Treat URLs with and without trailing slashes as equivalent
    url = url.removeprefix("https://").removeprefix("www.")  # Normalise the URL
    return url


def extract_url_path(url: str) -> str:
    """Extracts and returns the path component of a URL."""
    parsed_url = urlparse(url)
    path = parsed_url.path.lower().rstrip("/")  # Treat paths with and without trailing slashes and caps as equivalent
    return path
