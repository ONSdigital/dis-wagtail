from typing import ClassVar

from wagtail.models import PagePermissionTester

from cms.core.models import BasePage
from cms.core.permission_testers import StaticPagePermissionTester
from cms.users.models import User


class HomePage(BasePage):  # type: ignore[django-manager-missing]
    """The homepage model. Currently, only a placeholder."""

    template = "templates/pages/home_page.html"

    # Only allow creating HomePages at the root level
    parent_page_types: ClassVar[list[str]] = ["wagtailcore.Page"]

    _analytics_content_type: ClassVar[str] = "homepage"

    def permissions_for_user(self, user: User) -> PagePermissionTester:
        return StaticPagePermissionTester(user, self)
