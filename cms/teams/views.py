# Create TeamsViewSet
from typing import ClassVar

from wagtail.admin.viewsets.model import ModelViewSet

from .models import Team


class TeamsViewSet(ModelViewSet):
    model = Team
    # Not important for the PoC but for Beta build, we need a
    # custom admin view or disable ability to add/edit/delete.
    form_fields: ClassVar[list[str]] = ["name"]
    icon = "group"
    add_to_admin_menu = True
    menu_order = 200
    inspect_view_enabled = True


teams_viewset = TeamsViewSet("teams")
