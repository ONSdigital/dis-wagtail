from typing import TYPE_CHECKING

from django.contrib.auth import get_permission_codename

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import Model

    from cms.users.models import User


def get_permission_name(model: "type[Model]", action: str) -> str:
    """Get the full app-label-qualified permission name (as required by
    user.has_perm(...) ) for the given action on this model.
    """
    return f"{model._meta.app_label}.{get_permission_codename(action, model._meta)}"


def user_can_access_unpublished_datasets(user: "User | AnonymousUser") -> bool:
    """Check if the user can access unpublished datasets.

    Uses the view_previewteam permission which is granted to Publishing Admins
    and Publishing Officers who are authorized to access unpublished content.
    """
    return user.is_superuser or user.has_perm("users.view_previewteam")
