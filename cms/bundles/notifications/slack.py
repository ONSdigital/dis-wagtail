import logging
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


def notify_slack_of_publication_start(bundle: Bundle, user: User | None = None, url: str | None = None) -> None:
    """Send a Slack notification for Bundle publication start.

    Uses webhook for backward compatibility unless Bot API is fully configured.
    """
    # Use Bot API if fully configured, otherwise fall back to webhook
    if settings.SLACK_BOT_TOKEN and settings.SLACK_NOTIFICATION_CHANNEL:
        fields: list[dict[Any, Any]] = [
            {"title": "Title", "value": bundle.name, "short": True},
            {"title": "User", "value": user.get_full_name() if user else "System", "short": True},
            {"title": "Pages", "value": bundle.get_bundled_pages().count(), "short": True},
        ]
        if url:
            fields.append({"title": "Link", "value": url, "short": False})

        _send_and_update_message(
            bundle=bundle,
            text="Starting bundle publication",
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
        {"title": "User", "value": user.get_full_name() if user else "System", "short": True},
        {"title": "Pages", "value": bundle.get_bundled_pages().count(), "short": True},
    ]
    if url:
        fields.append(
            {"title": "Link", "value": url, "short": False},
        )

    response = client.send(
        text="Starting bundle publication",
        attachments=[{"color": "good", "fields": fields}],
        unfurl_links=False,
        unfurl_media=False,
    )

    if response.status_code != HTTPStatus.OK:
        logger.error("Unable to notify Slack of bundle publication start: %s", response.body)


def notify_slack_of_publish_end(
    bundle: Bundle, elapsed: float, user: User | None = None, url: str | None = None
) -> None:
    """Send a Slack notification for Bundle publication end.

    Uses webhook for backward compatibility unless Bot API is fully configured.
    """
    # Use Bot API if fully configured, otherwise fall back to webhook
    if settings.SLACK_BOT_TOKEN and settings.SLACK_NOTIFICATION_CHANNEL:
        fields: list[dict[Any, Any]] = [
            {"title": "Title", "value": bundle.name, "short": True},
            {"title": "User", "value": user.get_full_name() if user else "System", "short": True},
            {"title": "Pages", "value": bundle.get_bundled_pages().count(), "short": True},
            {"title": "Total time", "value": f"{elapsed:.3f} seconds"},
        ]
        if url:
            fields.append({"title": "Link", "value": url, "short": False})

        _send_and_update_message(
            bundle=bundle,
            text="Finished bundle publication",
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
        {"title": "User", "value": user.get_full_name() if user else "System", "short": True},
        {"title": "Pages", "value": bundle.get_bundled_pages().count(), "short": True},
        {"title": "Total time", "value": f"{elapsed:.3f} seconds"},
    ]
    if url:
        fields.append(
            {"title": "Link", "value": url, "short": False},
        )

    response = client.send(
        text="Finished bundle publication",
        attachments=[{"color": "good", "fields": fields}],
        unfurl_links=False,
        unfurl_media=False,
    )

    if response.status_code != HTTPStatus.OK:
        logger.error("Unable to notify Slack of bundle publication finish: %s", response.body)
