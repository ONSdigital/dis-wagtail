from typing import TYPE_CHECKING

from django.conf import settings
from wagtail import hooks

from .viewsets import user_chooser_viewset

if TYPE_CHECKING:
    from .viewsets import UserChooserViewSet

# fmt: off
if getattr(settings, "ENABLE_DJANGO_DEFENDER", False):
    from django.urls import reverse  # pylint: disable=ungrouped-imports
    from wagtail.admin.menu import MenuItem  # pylint: disable=ungrouped-imports

    if TYPE_CHECKING:
        from django.http import HttpRequest


    class DjangoAdminMenuItem(MenuItem):
        """Custom menu item visible only to superusers."""
        def is_shown(self, request: HttpRequest) -> bool:
            return request.user.is_superuser

    @hooks.register("register_settings_menu_item")
    def register_locked_accounts_menu_item() -> MenuItem:
        """Register shortcut to access django-defender's blocked list view within Django admin."""
        return DjangoAdminMenuItem(
            "Locked accounts",
            reverse("defender_blocks_view"),
            icon_name="lock",
            order=601,
        )
# fmt: on


@hooks.register("register_admin_viewset")
def register_viewset() -> UserChooserViewSet:
    return user_chooser_viewset
