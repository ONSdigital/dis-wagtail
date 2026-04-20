from typing import TYPE_CHECKING

from django.contrib.auth.models import AnonymousUser

from cms.users.permissions import get_permission_name

from .enums import PREVIEWABLE_BUNDLE_STATUSES

if TYPE_CHECKING:
    from cms.users.models import User

    from .models import Bundle


def get_bundle_permission(action: str) -> str:
    # imported inline to prevent partial initialization and circular import errors
    from .models import Bundle  # pylint: disable=import-outside-toplevel

    return get_permission_name(Bundle, action)


def user_can_manage_bundles(user: User | AnonymousUser) -> bool:
    if isinstance(user, AnonymousUser):
        return False

    # superusers can do anything
    if user.is_superuser:
        return True

    # users that can manage or view bundles can preview any bundle
    return any(
        user.has_perm(permission) for permission in [get_bundle_permission("add"), get_bundle_permission("change")]
    )


def user_can_preview_bundle(user: User | AnonymousUser, bundle: Bundle) -> bool:
    if isinstance(user, AnonymousUser):
        return False

    # if the user can manage bundles, they can preview
    if user_can_manage_bundles(user):
        return True

    # otherwise, only users in the same team(s) as the bundle team(s)
    return (
        user.has_perm(get_bundle_permission("view"))
        and bundle.status in PREVIEWABLE_BUNDLE_STATUSES
        and bool(set(user.active_team_ids) & set(bundle.active_team_ids))
    )
