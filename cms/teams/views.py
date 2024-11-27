# Create TeamsViewSet
from typing import TYPE_CHECKING, ClassVar

from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.permission_policies import ModelPermissionPolicy

from .models import Team

if TYPE_CHECKING:
    from cms.users.models import User


class ViewOnlyModelPermissionPolicy(ModelPermissionPolicy):
    """A permission policy that enforces view only permission at the model level, by consulting
    the standard django.contrib.auth permission model directly.
    """

    def user_has_permission(self, user: "User", action: str) -> bool:
        """Ensure only view action is allowed."""
        if action != "view":
            return False

        return user.has_perm(self._get_permission_name(action))


class TeamsViewSet(ModelViewSet):
    model = Team
    # Not important for the PoC but for Beta build, we need a
    # custom admin view or disable ability to add/edit/delete.
    form_fields: ClassVar[list[str]] = ["name"]
    icon = "group"
    add_to_admin_menu = True
    menu_order = 200
    inspect_view_enabled = True
    list_display: ClassVar[list[str]] = ["name", "total_members", "created_at", "updated_at"]
    list_filter: ClassVar[list[str]] = ["name", "is_active", "created_at", "updated_at"]
    inspect_view_fields: ClassVar[list[str]] = [
        "name",
        "created_at",
        "updated_at",
        "is_active",
        "total_members",
        "users",
    ]

    @property
    def permission_policy(self) -> ViewOnlyModelPermissionPolicy:
        return ViewOnlyModelPermissionPolicy(self.model)


teams_viewset = TeamsViewSet("teams")
