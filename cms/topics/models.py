from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField

from cms.core.models import BasePage

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel


class TopicPage(BasePage):  # type: ignore[django-manager-missing]
    """The Topic page model."""

    template = "templates/pages/topic_page.html"
    parent_page_types: ClassVar[list[str]] = ["themes.ThemePage"]
    subpage_types: ClassVar[list[str]] = ["articles.ArticleSeries", "methodology.MethodologyPage"]
    page_description = _("A specific topic page. e.g. 'Public sector finance' or 'Inflation and price indices'.")

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    content_panels: ClassVar[list["Panel"]] = [*BasePage.content_panels, FieldPanel("summary")]
