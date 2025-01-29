from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField

from cms.core.models import BasePage, ExclusiveTaxonomyMixin

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel


class ThemePage(BasePage, ExclusiveTaxonomyMixin):  # type: ignore[django-manager-missing]
    """The Theme page model."""

    template = "templates/pages/theme_page.html"
    parent_page_types: ClassVar[list[str]] = ["home.HomePage", "ThemePage"]
    subpage_types: ClassVar[list[str]] = ["ThemePage", "topics.TopicPage"]
    page_description = _("A theme page, such as 'Economy'.")

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    content_panels: ClassVar[list["Panel"]] = [*BasePage.content_panels, FieldPanel("summary")]

    taxonomy_panels: ClassVar[list["Panel"]] = ExclusiveTaxonomyMixin.taxonomy_panels
