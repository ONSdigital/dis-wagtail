from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from cms.users.models import User


def user_can_remove_notice(user: "User | AnonymousUser") -> bool:
    """Check if the user can remove notice from a Release Calendar Page."""
    return user.has_perm("release_calendar.remove_notice")
