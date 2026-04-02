from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from django.conf import settings

from cms.core.slack import send_or_update_message

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise

    from cms.bundles.models import Bundle
    from cms.users.models import User

logger = logging.getLogger("cms.bundles")


class BundleAlertType(str, Enum):
    """Alert severity levels for Slack bundle notifications."""

    CRITICAL = "Critical"
    FAIL = "Fail"
    WARNING = "Warning"


def send_bundle_notification(  # pylint: disable=too-many-arguments  # noqa: PLR0913
    bundle: Bundle,
    text: str,
    color: str,
    fields: list[dict],
    *,
    force_new: bool = False,
    save_timestamp: bool = True,
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
        force_new: If True, always create a new message (default: False)
        save_timestamp: If True, save the message timestamp to the bundle to allow future updates (default: True)
    """
    message_ts = send_or_update_message(
        text=text,
        color=color,
        fields=fields,
        update_message_ts=bundle.slack_notification_ts if not force_new else None,
        channel=settings.SLACK_PUBLICATION_LOG_CHANNEL,
    )
    if message_ts and save_timestamp:
        bundle.slack_notification_ts = message_ts
        bundle.save(update_fields=["slack_notification_ts"])


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
    otherwise the first bundled page URL, excluding alias pages.

    Args:
        bundle: The bundle to get the example page URL for.

    Returns:
        The example page URL or None if no pages available.
    """
    if release_page := bundle.release_calendar_page:
        return str(release_page.full_url)

    first_page = bundle.get_bundled_pages().filter().first()
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
    """Send a Slack notification for Bundle status changes."""
    if not settings.SLACK_NOTIFY_ON_BUNDLE_STATUS_CHANGE:
        return

    fields: list[dict[str, Any]] = [
        {"title": "Title", "value": bundle.name, "short": True},
        {"title": "Changed by", "value": user.get_full_name() if user else "System", "short": True},
        {"title": "Old status", "value": old_status, "short": True},
        {"title": "New status", "value": bundle.get_status_display(), "short": True},
    ]
    if context_message:
        fields.append({"title": "Context", "value": context_message})
    if url:
        fields.append({"title": "Link", "value": url, "short": False})

    send_bundle_notification(
        bundle=bundle,
        text="Bundle status changed",
        color="good",
        fields=fields,
    )


def notify_slack_of_bundle_pre_publish(
    bundle: Bundle,
    scheduled_time: datetime,
) -> None:
    """Send pre-publish notification for a bundle.

    Creates initial Slack message that will be updated when publishing starts
    and completes. Uses amber color to indicate upcoming publication.

    Args:
        bundle: The bundle scheduled for publication.
        scheduled_time: The scheduled publication datetime.
    """
    fields: list[dict[str, Any]] = [
        {"title": "Bundle Name", "value": f"<{bundle.full_inspect_url}|{bundle.name}>", "short": False},
        {"title": "Publish Start", "value": _format_publish_datetime(scheduled_time), "short": True},
    ]

    send_bundle_notification(
        bundle=bundle,
        text="Preparing bundle for publication",
        color="warning",  # Amber
        fields=fields,
        force_new=True,  # Always create a new message to ensure publication notifications are visible.
    )


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
    fields: list[dict[str, Any]] = [
        {"title": "Bundle Name", "value": f"<{url or bundle.full_inspect_url}|{bundle.name}>", "short": False},
        {"title": "Publish Type", "value": _get_publish_type(bundle), "short": True},
        {"title": "Scheduled Start", "value": _format_publish_datetime(start_time), "short": True},
        {"title": "Page Count", "value": str(bundle.get_bundled_pages().count()), "short": True},
    ]

    if example_page_url := _get_example_page_url(bundle):
        fields.append({"title": "Example Page", "value": example_page_url, "short": False})

    send_bundle_notification(
        bundle=bundle,
        text="Publishing the bundle has started",
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
    fields: list[dict[str, Any]] = [
        {"title": "Bundle Name", "value": f"<{url or bundle.full_inspect_url}|{bundle.name}>", "short": False},
        {"title": "Publish Type", "value": _get_publish_type(bundle), "short": True},
        {"title": "Publish Start", "value": _format_publish_datetime(start_time), "short": True},
        {"title": "Publish End", "value": _format_publish_datetime(end_time), "short": True},
        {"title": "Duration", "value": f"{(end_time - start_time).total_seconds():.3f} seconds", "short": True},
        {"title": "Page Count", "value": str(bundle.get_bundled_pages().count()), "short": True},
        {"title": "Pages Published", "value": str(pages_published), "short": True},
    ]

    if example_page_url := _get_example_page_url(bundle):
        fields.append({"title": "Example Page", "value": example_page_url, "short": False})

    send_bundle_notification(
        bundle=bundle,
        text="Publishing the bundle has ended",
        color="good",
        fields=fields,
    )


def notify_slack_of_bundle_failure(  # pylint: disable=too-many-arguments  # noqa: PLR0913
    *,
    bundle: Bundle,
    start_time: datetime,
    end_time: datetime,
    pages_published: int,
    exception_message: str,
    alert_type: BundleAlertType = BundleAlertType.CRITICAL,
    url: str | None = None,
) -> None:
    """Send failure notification for a bundle.

    Always creates a new Slack message (does not update existing messages).
    Uses red color to indicate failure.

    Args:
        bundle: The bundle that failed.
        start_time: The time publishing started.
        end_time: The time publishing ended.
        pages_published: Number of pages successfully published.
        exception_message: Brief description of the error.
        alert_type: Alert severity.
        url: The URL to link to the bundle (optional).
    """
    fields: list[dict[str, Any]] = [
        {"title": "Bundle Name", "value": f"<{url or bundle.full_inspect_url}|{bundle.name}>", "short": False},
        {"title": "Publish Type", "value": _get_publish_type(bundle), "short": True},
        {"title": "Publish Start", "value": _format_publish_datetime(start_time), "short": True},
        {"title": "Publish End", "value": _format_publish_datetime(end_time), "short": True},
        {"title": "Duration", "value": f"{(end_time - start_time).total_seconds():.3f} seconds", "short": True},
        {"title": "Page Count", "value": str(bundle.get_bundled_pages().count()), "short": True},
        {"title": "Pages Published", "value": str(pages_published), "short": True},
        {"title": "Alert Type", "value": alert_type, "short": True},
        {"title": "Exception", "value": exception_message, "short": False},
    ]

    send_bundle_notification(
        bundle=bundle,
        text="Bundle Publication Failure Detected",
        color="danger",
        fields=fields,
    )


def alert_slack_of_bundle_content_failure(
    bundle: Bundle,
    exception_message: str,
    alert_type: BundleAlertType = BundleAlertType.FAIL,
) -> None:
    """Send content failure alert for a bundle item.

    Always creates a new Slack message (does not update existing messages).
    Uses red color to indicate failure.

    Args:
        bundle: The bundle with content issues.
        exception_message: Brief description of the content error.
        alert_type: Alert severity (default=FAIL)
    """
    fields: list[dict[str, Any]] = [
        {"title": "Bundle Name", "value": f"<{bundle.full_inspect_url}|{bundle.name}>", "short": False},
        {"title": "Timestamp", "value": _format_publish_datetime(datetime.now()), "short": True},
        {"title": "Publish Type", "value": _get_publish_type(bundle), "short": True},
        {"title": "Alert Type", "value": alert_type, "short": True},
        {"title": "Exception", "value": exception_message, "short": False},
    ]

    send_or_update_message(
        text="Bundle Publication Failure Detected",
        color="danger",
        fields=fields,
        channel=settings.SLACK_ALARM_CHANNEL,
    )
