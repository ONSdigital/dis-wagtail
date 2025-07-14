import logging
from typing import Any

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpRequest
from wagtail.users.models import UserProfile

from cms.core.utils import get_client_ip

from .models import User

logger = logging.getLogger("cms.users")


@receiver(user_logged_in)
def audit_user_logged_in(sender: Any, request: HttpRequest, user: User, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    logger.info(
        "User logged in",
        extra={
            "user_id": user.id,
            "email": user.email,
            "event": "user_logged_in",
            "ip_address": get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
        },
    )


@receiver(user_logged_out)
def audit_user_logged_out(sender: Any, request: HttpRequest, user: User | None, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    if user is None:
        # We don't care that no one logged out
        return

    logger.info(
        "User logged out",
        extra={
            "user_id": user.id,
            "email": user.email,
            "event": "user_logged_out",
            "ip_address": get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
        },
    )


@receiver(user_login_failed)
def audit_user_login_failed(sender: Any, credentials: dict, request: HttpRequest | None, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    logger.warning(
        "Login failed",
        extra={
            "username": credentials.get("username"),
            "event": "user_login_failed",
            "ip_address": get_client_ip(request) if request else None,
            "user_agent": request.headers.get("User-Agent") if request else None,
        },
    )


@receiver(post_save, sender=UserProfile)
def disable_profile_notifications(sender: Any, instance: UserProfile, created: bool, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    if created:
        instance.submitted_notifications = False
        instance.approved_notifications = False
        instance.rejected_notifications = False
        instance.updated_comments_notifications = False
        instance.save(
            update_fields=[
                "submitted_notifications",
                "approved_notifications",
                "rejected_notifications",
                "updated_comments_notifications",
            ]
        )
