from typing import TYPE_CHECKING, Optional

from wagtail.permissions import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import MainMenu

if TYPE_CHECKING:
    from cms.users.models import User


class NoAddModelPermissionPolicy(ModelPermissionPolicy):
    """Model permission that doesn't allow creating more than one main menu instance."""

    def user_has_permission(self, user: Optional["User"] = None, action: str | None = None) -> bool:
        if action == "add" and MainMenu.objects.exists():
            return False
        return user is not None and user.has_perm(self._get_permission_name(action))


class MainMenuViewSet(SnippetViewSet):
    """A snippet viewset for MainMenu."""

    model = MainMenu

    @property
    def permission_policy(self) -> NoAddModelPermissionPolicy:
        return NoAddModelPermissionPolicy(self.model)


register_snippet(MainMenuViewSet)
