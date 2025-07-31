from typing import ClassVar

from django.utils.functional import cached_property

from cms.core.models import BasePage


class HomePage(BasePage):  # type: ignore[django-manager-missing]
    """The homepage model. Currently, only a placeholder."""

    template = "templates/pages/home_page.html"

    # Only allow creating HomePages at the root level
    parent_page_types: ClassVar[list[str]] = ["wagtailcore.Page"]

    gtm_content_type: ClassVar[str] = "homepage"

    @cached_property
    def cached_analytics_values(self) -> dict[str, str | bool]:
        """Return a dictionary of cachable analytics values for this page."""
        values = super().cached_analytics_values
        values["contentType"] = self.gtm_content_type
        return values
