from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
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
