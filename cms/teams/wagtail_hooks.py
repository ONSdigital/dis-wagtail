from typing import TYPE_CHECKING

from wagtail import hooks

from cms.teams.viewsets import team_chooser_viewset, teams_viewset

if TYPE_CHECKING:
    from .viewsets import TeamChooserViewSet, TeamsViewSet


@hooks.register("register_admin_viewset")
def register_teams_viewset() -> TeamsViewSet:
    """Register the teams viewset."""
    return teams_viewset


@hooks.register("register_admin_viewset")
def register_teams_chooser_viewset() -> TeamChooserViewSet:
    return team_chooser_viewset
