from typing import TYPE_CHECKING, ClassVar

from wagtail.admin.ui.tables import Column, LiveStatusTagColumn, LocaleColumn, UpdatedAtColumn
from wagtail.permissions import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.chooser import ChooseResultsView as SnippetChooseResultsView
from wagtail.snippets.views.chooser import ChooseView as SnippetChooseView
from wagtail.snippets.views.chooser import SnippetChooserViewSet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import FooterMenu, MainMenu

if TYPE_CHECKING:
    from cms.users.models import User


class SingleInstanceModelPermissionPolicy(ModelPermissionPolicy):
    """Permission policy that prevents creating a new instance of the model
    if one already exists.
    """

    def user_has_permission(self, user: User, action: str) -> bool:
        # Disallow "add" if an instance already exists
        if action == "add" and self.model.objects.exists():
            return False
        has_permission: bool = super().user_has_permission(user, action)
        return has_permission


class MenuChooseColumnsMixin:
    @property
    def columns(self) -> list[Column]:
        return [self.title_column, LocaleColumn()]  # type: ignore[attr-defined]


class MenuChooseView(MenuChooseColumnsMixin, SnippetChooseView): ...


class MenuChooseResultsView(MenuChooseColumnsMixin, SnippetChooseResultsView): ...


class MenuChooserViewset(SnippetChooserViewSet):
    choose_view_class = MenuChooseView
    choose_results_view_class = MenuChooseResultsView


class MainMenuViewSet(SnippetViewSet):
    """A snippet viewset for MainMenu."""

    model = MainMenu
    list_display: ClassVar[list[str | Column]] = [
        "name",
        "locale",
        UpdatedAtColumn(),
        LiveStatusTagColumn(),
    ]

    chooser_viewset_class = MenuChooserViewset

    @property
    def permission_policy(self) -> SingleInstanceModelPermissionPolicy:
        return SingleInstanceModelPermissionPolicy(self.model)


class FooterMenuViewSet(SnippetViewSet):
    """A snippet viewset for FooterMenu."""

    model = FooterMenu
    list_display: ClassVar[list[str | Column]] = [
        "name",  # Name contains the locale
        UpdatedAtColumn(),
        LiveStatusTagColumn(),
    ]

    chooser_viewset_class = MenuChooserViewset

    @property
    def permission_policy(self) -> SingleInstanceModelPermissionPolicy:
        return SingleInstanceModelPermissionPolicy(self.model)


register_snippet(MainMenuViewSet)
register_snippet(FooterMenuViewSet)
