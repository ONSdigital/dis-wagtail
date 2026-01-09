from typing import TYPE_CHECKING, ClassVar, cast

from django.conf import settings
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.views.generic import IndexView
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.permission_policies import ModelPermissionPolicy

from .admin_forms import TeamAdminForm
from .models import Team

if TYPE_CHECKING:
    from cms.users.models import User

    from .models import TeamQuerySet


class ViewOnlyModelPermissionPolicy(ModelPermissionPolicy):
    """A permission policy that enforces view only permission at the model level, by consulting
    the standard django.contrib.auth permission model directly.
    """

    def user_has_permission(self, user: User, action: str) -> bool:
        """Ensure only view action is allowed."""
        # Note: we allow temporary management, hidden behind a flag
        if action != "view" and not settings.ALLOW_TEAM_MANAGEMENT:
            return False

        return user.has_perm(self._get_permission_name(action))


class TeamsIndexView(IndexView):
    page_title = "Preview teams"

    def get_base_queryset(self) -> TeamQuerySet:
        """Return only active teams."""
        return cast("TeamQuerySet", Team.objects.active())


class TeamsViewSet(ModelViewSet):
    model = Team
    index_view_class = TeamsIndexView
    menu_label = "Preview teams"
    icon = "group"
    add_to_admin_menu = True
    menu_order = 200
    inspect_view_enabled = True
    list_display: ClassVar[list[str]] = ["name", "identifier", "created_at", "updated_at"]
    list_filter: ClassVar[list[str]] = ["name", "identifier", "created_at", "updated_at"]
    inspect_view_fields: ClassVar[list[str]] = [
        "name",
        "identifier",
        "created_at",
        "updated_at",
        "is_active",
        "users",
    ]

    def get_form_class(self, for_update: bool = False) -> type[TeamAdminForm]:
        return TeamAdminForm

    @property
    def permission_policy(self) -> ViewOnlyModelPermissionPolicy:
        return ViewOnlyModelPermissionPolicy(self.model)


teams_viewset = TeamsViewSet("teams")


class TeamChooseMixin:
    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.label = "Name"
        return [
            title_column,
            Column("identifier"),
            DateColumn(
                "updated_at",
                label="Last Updated",
                width="12%",
            ),
        ]

    def get_object_list(self) -> TeamQuerySet:
        """Return only active teams."""
        return cast("TeamQuerySet", Team.objects.active())


class TeamChooseView(TeamChooseMixin, ChooseView): ...


class TeamChooseResultsView(TeamChooseMixin, ChooseResultsView): ...


class TeamChooserViewSet(ChooserViewSet):
    model = Team
    choose_view_class = TeamChooseView
    choose_results_view_class = TeamChooseResultsView

    icon = "group"


team_chooser_viewset = TeamChooserViewSet("team_chooser")
