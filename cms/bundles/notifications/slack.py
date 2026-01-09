import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from django.conf import settings
from slack_sdk.webhook import WebhookClient

from cms.bundles.models import Bundle

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise

    from cms.users.models import User


logger = logging.getLogger("cms.bundles")


def notify_slack_of_status_change(
    bundle: Bundle,
    old_status: _StrOrPromise,
    user: User | None = None,
    url: str | None = None,
    context_message: str | None = None,
) -> None:
    """Sends a Slack notification for Bundle status changes."""
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
    """Sends a Slack notification for Bundle publication start."""
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
    """Sends a Slack notification for Bundle publication end."""
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
