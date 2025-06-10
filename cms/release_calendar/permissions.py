from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from cms.users.models import User


def user_can_remove_notice(user: "User | AnonymousUser") -> bool:
    """Check if the user can remove notice from a Release Calendar Page."""
    from cms.release_calendar.models import ReleaseCalendarPage  # pylint: disable=import-outside-toplevel

    return user.has_perm(f"{ReleaseCalendarPage._meta.app_label}.remove_notice")
