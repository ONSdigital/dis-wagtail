from typing import TYPE_CHECKING

from django.contrib.auth.models import AnonymousUser

from .enums import BundleStatus

if TYPE_CHECKING:
    from cms.users.models import User

    from .models import Bundle


def user_can_manage(user: "User | AnonymousUser") -> bool:
    if isinstance(user, AnonymousUser):
        return False

    # superusers can do anything
    if user.is_superuser:
        return True

    # users that can manage or view bundles can preview any bundle
    return any(user.has_perm(permission) for permission in ["bundles.add_bundle", "bundles.change_bundle"])


def user_can_preview(user: "User | AnonymousUser", bundle: "Bundle") -> bool:
    if isinstance(user, AnonymousUser):
        return False

    # if the user can manage bundles, they can preview
    if user_can_manage(user):
        return True

    # otherwise, only users in the same team(s) as the bundle team(s)
    has_view_permission = user.has_perm("bundles.view_bundle")
    bundle_in_review = bundle.status == BundleStatus.IN_REVIEW
    has_the_right_team = bool(set(user.active_team_ids) & set(bundle.active_team_ids))

    return has_view_permission and bundle_in_review and has_the_right_team
