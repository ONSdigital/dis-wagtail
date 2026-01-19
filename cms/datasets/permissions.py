from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from cms.users.models import User


def user_can_access_unpublished_datasets(user: User | AnonymousUser) -> bool:
    """Check if the user can access unpublished datasets.

    Uses the access_unpublished_datasets permission which is granted to Publishing Admins
    and Publishing Officers who are authorized to access unpublished datasets.
    """
    return user.is_superuser or user.has_perm("datasets.access_unpublished_datasets")
