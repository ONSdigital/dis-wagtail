from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.utils.functional import cached_property
from wagtail.fields import RichTextField

from cms.core.models import BasePage
from cms.taxonomy.mixins import ExclusiveTaxonomyMixin

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel


class ThemePage(ExclusiveTaxonomyMixin, BasePage):  # type: ignore[django-manager-missing]
    """The Theme page model."""

    template = "templates/pages/theme_page.html"
    parent_page_types: ClassVar[list[str]] = ["home.HomePage", "ThemePage"]
    subpage_types: ClassVar[list[str]] = ["ThemePage", "topics.TopicPage"]
    page_description = "A theme page, such as 'Economy'."
    label = "Theme"

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    content_panels: ClassVar[list["Panel"]] = [*BasePage.content_panels, "summary"]

    @cached_property
    def cached_analytics_values(self) -> dict[str, str | bool]:
        """Return a dictionary of cachable analytics values for this page."""
        values = super().cached_analytics_values

        values["contentTheme"] = self.slug
        return values

    @cached_property
    def gtm_content_type(self) -> str:
        """Return the Google Tag Manager content type for this page."""
        if isinstance(self.get_parent().specific_deferred, ThemePage):
            return "sub-themes"
        return "themes"
