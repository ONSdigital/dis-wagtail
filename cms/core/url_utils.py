from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError


def is_hostname_in_domain(hostname: str, allowed_domain: str) -> bool:
    """Check if the hostname matches the allowed domain or its subdomains."""
    return hostname == allowed_domain or hostname.endswith(f".{allowed_domain}")


def validate_ons_url(url):
    """Checks that the given URL matches the allowed ONS domain,
    otherwise return a dict holding a ValidationError to be used in the clean method of a StructBlock.
    """
    errors = {}
    parsed_url = urlparse(url)

    if not parsed_url.hostname or parsed_url.scheme != "https":
        errors["url"] = ValidationError(
            "Please enter a valid URL. It should start with 'https://' and contain a valid domain name."
        )
    elif not any(
        is_hostname_in_domain(parsed_url.hostname, allowed_domain)
        for allowed_domain in settings.ONS_ALLOWED_LINK_DOMAINS
    ):
        patterns_str = " or ".join(settings.ONS_ALLOWED_LINK_DOMAINS)
        errors["url"] = ValidationError(
            f"The URL hostname is not in the list of allowed domains or their subdomains: {patterns_str}"
        )

    return errors


def normalise_url(url):
    """Normalise functionally equivalent URLs for comparison
    when checking for duplicates across StreamValue entities.
    """
    url = url.lower().rstrip("/")  # Treat URLs with and without trailing slashes as equivalent
    url = url.removeprefix("https://").removeprefix("www.")  # Normalise the URL
    return url
