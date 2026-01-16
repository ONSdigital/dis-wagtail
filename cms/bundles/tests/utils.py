from typing import TYPE_CHECKING

from django.contrib.auth.models import Permission
from django.db.models import QuerySet
from wagtail.models import GroupPagePermission

from cms.home.models import HomePage
from cms.users.tests.factories import GroupFactory, UserFactory

if TYPE_CHECKING:
    from django.contrib.auth.models import Group

    from cms.users.models import User


def get_all_bundle_permissions() -> QuerySet[Permission]:
    """Gets all bundle permissions."""
    return Permission.objects.filter(
        codename__in=[
            "add_bundle",
            "change_bundle",
            "delete_bundle",
            "view_bundle",
        ]
    )


def get_view_bundle_permission() -> Permission:
    """Returns the view bundle permission."""
    return Permission.objects.get(codename="view_bundle")


def create_bundle_manager(username: str = "publishing_officer") -> User:
    publishing_group = GroupFactory(name="Publishing Officers", access_admin=True)
    grant_all_bundle_permissions(publishing_group)
    grant_all_page_permissions(publishing_group)

    publishing_officer = UserFactory(username=username)
    publishing_officer.groups.add(publishing_group)

    return publishing_officer


def make_bundle_manager(user: User) -> None:
    """Gives all the bundle permissions to the given user."""
    user.user_permissions.add(*get_all_bundle_permissions())


def create_bundle_viewer(username: str = "bundle.viewer") -> User:
    bundle_viewer = UserFactory(username=username, access_admin=True)
    make_bundle_viewer(bundle_viewer)

    return bundle_viewer


def make_bundle_viewer(user: User) -> None:
    """Gives the view bundle permission to the given user."""
    user.user_permissions.add(get_view_bundle_permission())


def grant_all_bundle_permissions(group: Group) -> None:
    """Adds all the bundle permissions to the given group."""
    group.permissions.add(*get_all_bundle_permissions())


def grant_view_bundle_permissions(group: Group) -> None:
    """Adds the view bundle permission to the given group."""
    group.permissions.add(get_view_bundle_permission())


def grant_all_page_permissions(group: Group) -> None:
    """Adds all the page permissions to the given group."""
    home = HomePage.objects.first()
    for permission_type in ["add", "change", "delete", "view"]:
        GroupPagePermission.objects.create(group=group, page=home, permission_type=permission_type)
