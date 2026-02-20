import logging
from typing import TYPE_CHECKING

from django.conf import settings

from cms.bundles.notifications.slack import BundleAlertType, get_slack_client, require_slack_config

if TYPE_CHECKING:
    from wagtail.models import Page

    from cms.bundles.models import Bundle


logger = logging.getLogger("cms.bundles")


@require_slack_config
def notify_slack_of_dataset_api_failure(
    page: Page | None,
    exception_message: str,
    alert_type: BundleAlertType = BundleAlertType.WARNING,
) -> None:
    """Send notification when Dataset API call fails.

    Creates a new Slack message (does not update existing messages).
    Uses red border to indicate failure.

    Args:
        page: Optional page related to the dataset API call.
        exception_message: Brief description of the error.
        alert_type: Alert severity.
    """
    # TODO: Consider implementing rate limiting to prevent flooding Slack with repeated errors

    fields = [
        {"title": "Alert Type", "value": alert_type, "short": True},
        {"title": "Exception", "value": exception_message, "short": False},
    ]

    if page:
        admin_url = page.get_admin_display_title()
        fields.insert(
            0,
            {"title": "Page Name", "value": f"<{page.full_url}|{admin_url}>", "short": False},
        )

    client = get_slack_client()
    if not client:
        logger.warning("Slack Bot API client not configured")
        return

    try:
        client.chat_postMessage(
            channel=settings.SLACK_NOTIFICATION_CHANNEL,
            text="Data API Call Failure",
            attachments=[{"color": "danger", "fields": fields}],
            unfurl_links=False,
            unfurl_media=False,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Failed to send dataset API failure notification")


@require_slack_config
def notify_slack_of_third_party_api_failure(
    service_name: str,
    exception_message: str,
    alert_type: BundleAlertType = BundleAlertType.WARNING,
    bundle: Bundle | None = None,
    page: Page | None = None,
) -> None:
    """Send notification when third-party API call fails.

    Creates a new Slack message (does not update existing messages).
    Uses red border to indicate failure.

    Args:
        service_name: Name of the third-party service (e.g., "Bundle API").
        exception_message: Brief description of the error.
        alert_type: Alert severity.
        bundle: Optional bundle related to the API call.
        page: Optional page related to the API call.
    """
    # TODO: Consider implementing rate limiting to prevent flooding Slack with repeated errors

    title = f"API Call Failure to {service_name} failed"

    fields = [
        {"title": "Alert Type", "value": alert_type, "short": True},
        {"title": "Exception", "value": exception_message, "short": False},
    ]

    # Add bundle or page context if available
    if bundle:
        fields.insert(
            0,
            {"title": "Bundle Name", "value": f"<{bundle.full_inspect_url}|{bundle.name}>", "short": False},
        )
    elif page:
        admin_url = page.get_admin_display_title()
        fields.insert(
            0,
            {"title": "Page Name", "value": f"<{page.full_url}|{admin_url}>", "short": False},
        )

    client = get_slack_client()
    if not client:
        logger.warning("Slack Bot API client not configured")
        return

    try:
        client.chat_postMessage(
            channel=settings.SLACK_NOTIFICATION_CHANNEL,
            text=title,
            attachments=[{"color": "danger", "fields": fields}],
            unfurl_links=False,
            unfurl_media=False,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Failed to send third-party API failure notification to %s", service_name)
