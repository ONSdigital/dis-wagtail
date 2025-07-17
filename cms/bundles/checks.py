from collections.abc import Sequence
from typing import Any, Optional

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import CheckMessage, Info, register
from django.core.checks import Warning as DjangoWarning

from cms.bundles.api import BundleAPIClient, BundleAPIClientError


@register()
def check_bundle_api_health(app_configs: Optional[Sequence[AppConfig]], **kwargs: Any) -> list[CheckMessage]:  # pylint: disable=unused-argument
    """Check if the Bundle API is healthy when enabled."""
    errors: list[CheckMessage] = []

    # Only check if Bundle API is enabled
    if not getattr(settings, "ONS_BUNDLE_API_ENABLED", False):
        return errors

    try:
        client = BundleAPIClient()
        response = client.get_health()

        # Check if the response indicates healthy status
        if response.get("status") == "disabled":
            # API is disabled, which is expected when ONS_BUNDLE_API_ENABLED is False
            return errors

        # If we got here, the API responded, which is good
        errors.append(
            Info(
                "Bundle API is responding and healthy",
                hint=f"Health check response: {response}",
                id="bundles.I001",
            )
        )

    except BundleAPIClientError as e:
        errors.append(
            DjangoWarning(
                f"Bundle API health check failed: {e}",
                hint=(
                    "Check if the Bundle API service is running and accessible. "
                    f"API URL: {getattr(settings, 'ONS_API_BASE_URL', 'Not configured')}"
                ),
                id="bundles.W001",
            )
        )

    except Exception as e:  # pylint: disable=broad-exception-caught
        errors.append(
            DjangoWarning(
                f"Unexpected error during Bundle API health check: {e}",
                hint="Review Bundle API configuration and network connectivity.",
                id="bundles.W002",
            )
        )

    return errors
