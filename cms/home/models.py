from typing import ClassVar

from cms.core.models import BasePage


class HomePage(BasePage):  # type: ignore[django-manager-missing]
    template = "templates/pages/home_page.html"

    # Only allow creating HomePages at the root level
    parent_page_types: ClassVar[list[str]] = ["wagtailcore.Page"]
