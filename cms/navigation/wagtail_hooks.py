from typing import TYPE_CHECKING

from wagtail.permissions import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import FooterMenu, MainMenu

if TYPE_CHECKING:
    from cms.users.models import User


class SingleInstanceModelPermissionPolicy(ModelPermissionPolicy):
    """Permission policy that prevents creating a new instance of the model
    if one already exists.
    """

    def user_has_permission(self, user: "User", action: str) -> bool:
        # Disallow "add" if an instance already exists
        if action == "add" and self.model.objects.exists():
            return False
        has_permission: bool = super().user_has_permission(user, action)
        return has_permission


class MainMenuViewSet(SnippetViewSet):
    """A snippet viewset for MainMenu."""

    model = MainMenu

    @property
    def permission_policy(self) -> SingleInstanceModelPermissionPolicy:
        return SingleInstanceModelPermissionPolicy(self.model)


class FooterMenuViewSet(SnippetViewSet):
    """A snippet viewset for FooterMenu."""

    model = FooterMenu

    @property
    def permission_policy(self) -> SingleInstanceModelPermissionPolicy:
        return SingleInstanceModelPermissionPolicy(self.model)


register_snippet(MainMenuViewSet)
register_snippet(FooterMenuViewSet)
