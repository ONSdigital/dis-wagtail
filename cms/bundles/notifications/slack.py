import logging
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from django.conf import settings
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient
from slack_sdk.webhook import WebhookClient

from cms.bundles.models import Bundle

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise

    from cms.users.models import User


logger = logging.getLogger("cms.bundles")


def get_slack_client() -> WebClient | None:
    """Get Slack Bot API client if configured.

    Returns:
        WebClient instance if SLACK_BOT_TOKEN is configured, None otherwise.
    """
    if not (token := settings.SLACK_BOT_TOKEN):
        return None
    return WebClient(token=token)


def _send_and_update_message(
    bundle: Bundle,
    text: str,
    color: str,
    fields: list[dict],
) -> None:
    """Send or update a Slack message for bundle notifications.

    This function attempts to update an existing message if the bundle has a stored
    message timestamp. If the update fails or no timestamp exists, it creates a new
    message and stores the timestamp.

    Args:
        bundle: The bundle being published
        text: Message text/title
        color: Slack attachment color ("warning", "good", "danger")
        fields: Slack attachment fields
    """
    if not settings.SLACK_NOTIFICATION_CHANNEL:
        logger.warning("SLACK_NOTIFICATION_CHANNEL not configured")
        return

    channel = settings.SLACK_NOTIFICATION_CHANNEL
    client = get_slack_client()
    if not client:
        logger.warning("Slack Bot API client not configured")
        return

    attachments = [{"color": color, "fields": fields}]

    try:
        if bundle.slack_notification_ts:
            # Try to update existing message
            response = client.chat_update(
                channel=channel,
                ts=bundle.slack_notification_ts,
                text=text,
                attachments=attachments,
            )
        else:
            # Create new message
            response = client.chat_postMessage(
                channel=channel,
                text=text,
                attachments=attachments,
                unfurl_links=False,
                unfurl_media=False,
            )

        # Store timestamp for future updates
        if response and response.get("ok") and response.get("ts"):
            bundle.slack_notification_ts = response["ts"]
            bundle.save(update_fields=["slack_notification_ts"])

    except SlackApiError as e:
        logger.exception("Failed to send/update Slack message: %s", e)
        # If update fails (e.g., message not found), try creating a new message
        if bundle.slack_notification_ts:
            try:
                response = client.chat_postMessage(
                    channel=channel,
                    text=text,
                    attachments=attachments,
                    unfurl_links=False,
                    unfurl_media=False,
                )
                if response and response.get("ok") and response.get("ts"):
                    bundle.slack_notification_ts = response["ts"]
                    bundle.save(update_fields=["slack_notification_ts"])
            except SlackApiError:
                logger.exception("Failed to create fallback Slack message")


def _get_publish_type(bundle: Bundle) -> str:
    """Determine the publish type for a bundle.

    Returns:
        "Release Calendar" if bundle has a release calendar page,
        "Scheduled" if bundle has a publication date,
        "Manual" otherwise.
    """
    if bundle.release_calendar_page_id:
        return "Release Calendar"
    if bundle.publication_date:
        return "Scheduled"
    return "Manual"


def _format_publish_datetime(dt: datetime) -> str:
    """Format datetime as DD/MM/YYYY - HH:MM:SS.

    Args:
        dt: The datetime to format.

    Returns:
        Formatted string in DD/MM/YYYY - HH:MM:SS format.
    """
    return dt.strftime("%d/%m/%Y - %H:%M:%S")


def _get_example_page_url(bundle: Bundle) -> str | None:
    """Get the example page URL for a bundle.

    Returns the release calendar page URL if available,
    otherwise the first bundled page URL.

    Args:
        bundle: The bundle to get the example page URL for.

    Returns:
        The example page URL or None if no pages available.
    """
    if release_page := bundle.release_calendar_page:
        return str(release_page.full_url)

    first_page = bundle.get_bundled_pages().first()
    return str(first_page.full_url) if first_page else None


def _get_bundle_notification_context(bundle: Bundle) -> dict[str, str | int | None]:
    """Extract common notification context for a bundle.

    Args:
        bundle: The bundle to extract context from.

    Returns:
        Dictionary containing publish_type, page_count, and example_page_url.
    """
    return {
        "publish_type": _get_publish_type(bundle),
        "page_count": bundle.get_bundled_pages().count(),
        "example_page_url": _get_example_page_url(bundle),
    }


def notify_slack_of_status_change(
    bundle: Bundle,
    old_status: _StrOrPromise,
    user: User | None = None,
    url: str | None = None,
    context_message: str | None = None,
) -> None:
    """Send a Slack notification for Bundle status changes.

    Uses webhook for backward compatibility unless Bot API is fully configured.
    """
    # Use Bot API if fully configured, otherwise fall back to webhook
    if settings.SLACK_BOT_TOKEN and settings.SLACK_NOTIFICATION_CHANNEL:
        fields: list[dict[Any, Any]] = [
            {"title": "Title", "value": bundle.name, "short": True},
            {"title": "Changed by", "value": user.get_full_name() if user else "System", "short": True},
            {"title": "Old status", "value": old_status, "short": True},
            {"title": "New status", "value": bundle.get_status_display(), "short": True},
        ]
        if context_message:
            fields.append({"title": "Context", "value": context_message})
        if url:
            fields.append({"title": "Link", "value": url, "short": False})

        _send_and_update_message(
            bundle=bundle,
            text="Bundle status changed",
            color="good",
            fields=fields,
        )
        return

    # Fallback to webhook for backward compatibility
    if (webhook_url := settings.SLACK_NOTIFICATIONS_WEBHOOK_URL) is None:
        return

    client = WebhookClient(webhook_url)

    fields = [
        {"title": "Title", "value": bundle.name, "short": True},
        {"title": "Changed by", "value": user.get_full_name() if user else "System", "short": True},
        {"title": "Old status", "value": old_status, "short": True},
        {"title": "New status", "value": bundle.get_status_display(), "short": True},
    ]
    if context_message:
        fields.append({"title": "Context", "value": context_message})

    if url:
        fields.append(
            {"title": "Link", "value": url, "short": False},
        )

    response = client.send(
        text="Bundle status changed",
        attachments=[{"color": "good", "fields": fields}],
        unfurl_links=False,
        unfurl_media=False,
    )

    if response.status_code != HTTPStatus.OK:
        logger.error("Unable to notify Slack of bundle status change: %s", response.body)


def notify_slack_of_publication_start(
    bundle: Bundle,
    start_time: datetime,
    url: str | None = None,
) -> None:
    """Send notification when bundle publishing starts.

    Includes bundle name, publish type, scheduled start time, page count,
    and example page URL. Uses amber color to indicate publishing in progress.

    Args:
        bundle: The bundle being published.
        start_time: The scheduled start time (publication_date or current time).
        url: The URL to link to the bundle (optional).
    """
    if not settings.SLACK_NOTIFICATION_CHANNEL:
        return

    context = _get_bundle_notification_context(bundle)

    fields: list[dict[Any, Any]] = [
        {"title": "Bundle Name", "value": f"<{url or bundle.full_inspect_url}|{bundle.name}>", "short": False},
        {"title": "Publish Type", "value": context["publish_type"], "short": True},
        {"title": "Scheduled Start", "value": _format_publish_datetime(start_time), "short": True},
        {"title": "Page Count", "value": str(context["page_count"]), "short": True},
    ]

    if context["example_page_url"]:
        fields.append({"title": "Example Page", "value": context["example_page_url"], "short": False})

    text = "Publishing the bundle has started"

    _send_and_update_message(
        bundle=bundle,
        text=text,
        color="warning",  # Amber
        fields=fields,
    )


def notify_slack_of_publish_end(
    bundle: Bundle,
    start_time: datetime,
    end_time: datetime,
    pages_published: int,
    url: str | None = None,
) -> None:
    """Send notification when bundle publishing ends successfully.

    Includes bundle name, publish type, start/end times, duration, page counts,
    and example page URL. Uses green color to indicate successful completion.

    Args:
        bundle: The bundle that was published.
        start_time: The time publishing started.
        end_time: The time publishing ended.
        pages_published: Number of pages successfully published.
        url: The URL to link to the bundle (optional).
    """
    if not settings.SLACK_NOTIFICATION_CHANNEL:
        return

    context = _get_bundle_notification_context(bundle)

    # Calculate elapsed time in seconds
    elapsed_seconds = (end_time - start_time).total_seconds()

    fields: list[dict[Any, Any]] = [
        {"title": "Bundle Name", "value": f"<{url or bundle.full_inspect_url}|{bundle.name}>", "short": False},
        {"title": "Publish Type", "value": context["publish_type"], "short": True},
        {"title": "Publish Start", "value": _format_publish_datetime(start_time), "short": True},
        {"title": "Publish End", "value": _format_publish_datetime(end_time), "short": True},
        {"title": "Duration", "value": f"{elapsed_seconds:.3f} seconds", "short": True},
        {"title": "Page Count", "value": str(context["page_count"]), "short": True},
        {"title": "Pages Published", "value": str(pages_published), "short": True},
    ]

    if context["example_page_url"]:
        fields.append({"title": "Example Page", "value": context["example_page_url"], "short": False})

    text = "Publishing the bundle has ended"

    _send_and_update_message(
        bundle=bundle,
        text=text,
        color="good",  # Green
        fields=fields,
    )
