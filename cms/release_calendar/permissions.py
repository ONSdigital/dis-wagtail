from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from cms.users.models import User


def user_can_modify_notice(user: User | AnonymousUser) -> bool:
    """Check if the user can modify notice from a Release Calendar Page."""
    return user.is_superuser or user.has_perm("release_calendar.modify_notice")
