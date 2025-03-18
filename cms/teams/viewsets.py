from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.views.generic import IndexView
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
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
        # Note: we allow temporary management, hidden behind a flag
        if action != "view" and not settings.ALLOW_TEAM_MANAGEMENT:
            return False

        return user.has_perm(self._get_permission_name(action))


class TeamsIndexView(IndexView):
    page_title = "Preview teams"


class TeamsViewSet(ModelViewSet):
    model = Team
    index_view_class = TeamsIndexView
    menu_label = "Preview teams"
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
    def form_fields(self) -> list[str]:
        # note: when ALLOW_TEAM_MANAGEMENT is removed, conver this to an actual property
        # form_fields: ClassVar[list[str]] = ["name"]
        return ["name", "identifier"] if settings.ALLOW_TEAM_MANAGEMENT else ["name"]

    @property
    def permission_policy(self) -> ViewOnlyModelPermissionPolicy:
        return ViewOnlyModelPermissionPolicy(self.model)


teams_viewset = TeamsViewSet("teams")


class TeamChooseMixin:
    @property
    def columns(self) -> list[Column]:
        return [
            self.title_column,  # type: ignore[attr-defined]
            Column("identifier"),
            DateColumn(
                "updated_at",
                label="Last Updated",
                width="12%",
            ),
            Column("is_active", label="Active?", width="10%"),
        ]


class TeamChooseView(TeamChooseMixin, ChooseView): ...


class TeamChooseResultsView(TeamChooseMixin, ChooseResultsView): ...


class TeamChooserViewSet(ChooserViewSet):
    model = Team
    choose_view_class = TeamChooseView
    choose_results_view_class = TeamChooseResultsView

    icon = "group"


team_chooser_viewset = TeamChooserViewSet("team_chooser")
