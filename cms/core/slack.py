import logging
from collections.abc import Callable
from functools import wraps
from http import HTTPStatus
from typing import Any

from django.conf import settings
from slack_sdk import WebClient, WebhookClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


def require_slack_notification_config[T: Callable[..., Any]](func: T) -> T:
    """Decorator to check Slack configuration before sending notifications.

    Returns:
        Decorated function that returns None if configuration checks fail.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not settings.SLACK_BOT_TOKEN:
            logger.warning("SLACK_BOT_TOKEN not configured")
            return None
        if not settings.SLACK_NOTIFICATION_CHANNEL:
            logger.warning("SLACK_NOTIFICATION_CHANNEL not configured")
            return None

        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def get_slack_client() -> WebClient | None:
    """Get Slack Bot API client if configured.

    Returns:
        WebClient instance if SLACK_BOT_TOKEN is configured, None otherwise.
    """
    if not (token := settings.SLACK_BOT_TOKEN):
        return None
    return WebClient(token=token)


def send_or_update_message(
    text: str,
    color: str,
    fields: list[dict],
    channel: str,
    *,
    update_message_ts: str | None = None,
) -> str | None:
    """Send or update a Slack message.

    This function attempts to update an existing message if given a message timestamp.
    If the update fails or no timestamp is supplied, it posts a new message.

    Args:
        text: Message text/title
        color: Slack attachment color ("warning", "good", "danger")
        fields: Slack attachment fields
        channel: Slack channel to send the message to
        update_message_ts: Optional timestamp of the message to update. Forces a new message to be posted if not
                           provided

    Returns: Timestamp of the sent or updated message, or None if sending/updating failed
    """
    client = get_slack_client()
    if not client:
        logger.warning("Slack Bot API client not configured")
        return None

    attachments = [{"color": color, "fields": fields}]

    try:
        if update_message_ts:
            # Try to update existing message
            response = client.chat_update(
                channel=channel,
                ts=update_message_ts,
                text=text,
                attachments=attachments,
            )
            # Return timestamp if response is valid
            if response and response.get("ok") and response.get("ts"):
                return response["ts"]
        else:
            # Create new message
            response = client.chat_postMessage(
                channel=channel,
                text=text,
                attachments=attachments,
                unfurl_links=False,
                unfurl_media=False,
            )
            # Return the
            if response and response.get("ok") and response.get("ts"):
                return response["ts"]

    except SlackApiError as e:
        logger.exception("Failed to send/update Slack message: %s", e)
        # If update fails (e.g., message not found), try creating a new message
        if update_message_ts:
            try:
                response = client.chat_postMessage(
                    channel=channel,
                    text=text,
                    attachments=attachments,
                    unfurl_links=False,
                    unfurl_media=False,
                )
                if response and response.get("ok") and response.get("ts"):
                    return response["ts"]
            except SlackApiError:
                logger.exception("Failed to create fallback Slack message")
    return None


def send_message_via_webhook(
    text: str,
    color: str,
    fields: list[dict],
    webhook_url: str,
) -> None:
    """Send a Slack message using an incoming webhook.

    Args:
        text: Message text/title
        color: Slack attachment color ("warning", "good", "danger")
        fields: Slack attachment fields
        webhook_url: URL of the Slack incoming webhook
    """
    client = WebhookClient(webhook_url)

    response = client.send(
        text=text,
        attachments=[{"color": color, "fields": fields}],
        unfurl_links=False,
        unfurl_media=False,
    )

    if response.status_code != HTTPStatus.OK:
        logger.error("Unable to send Slack message: %s", response.body)
