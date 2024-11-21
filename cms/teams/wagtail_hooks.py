from wagtail import hooks

from cms.teams.views import TeamsViewSet, teams_viewset


@hooks.register("register_admin_viewset")
def register_teams_viewset() -> TeamsViewSet:
    """Register the teams viewset."""
    return teams_viewset
