from typing import TYPE_CHECKING

from django.contrib.auth.models import Permission
from django.db.models import QuerySet
from wagtail.models import GroupPagePermission, Workflow

from cms.home.models import HomePage

if TYPE_CHECKING:
    from django.contrib.auth.models import Group
    from wagtail.models import Page

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


def make_bundle_manager(user: "User") -> None:
    """Givess all the bundle permissions to the given user."""
    user.user_permissions.add(*get_all_bundle_permissions())


def make_bundle_viewer(user: "User") -> None:
    """Gives the view bundle permission to the given user."""
    user.user_permissions.add(get_view_bundle_permission())


def grant_all_bundle_permissions(group: "Group") -> None:
    """Adds all the bundle permissions to the given group."""
    group.permissions.add(*get_all_bundle_permissions())


def grant_view_bundle_permissions(group: "Group") -> None:
    """Adds the view bundle permission to the given group."""
    group.permissions.add(get_view_bundle_permission())


def grant_all_page_permissions(group: "Group") -> None:
    """Adds all the page permissions to the given group."""
    home = HomePage.objects.first()
    for permission_type in ["add", "change", "delete", "view"]:
        GroupPagePermission.objects.create(group=group, page=home, permission_type=permission_type)


def mark_page_as_ready_to_publish(page: "Page", user: "User") -> None:
    page.save_revision()
    workflow = Workflow.objects.get(name="Release review")
    # start the workflow
    workflow_state = workflow.start(page, user)
    task_state = workflow_state.current_task_state
    # approve the first task ("review" / "preview")
    task_state.task.on_action(task_state, user=None, action_name="approve")
