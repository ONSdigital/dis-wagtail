from typing import TYPE_CHECKING, ClassVar, Union

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import PublishingPanel
from wagtail.contrib.settings.models import register_setting
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin

from cms.core.fields import StreamField
from cms.core.models import BaseSiteSetting
from cms.navigation.blocks import ColumnBlock, HighlightsBlock
from cms.navigation.forms import MainMenuAdminForm

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


class MainMenu(DraftStateMixin, RevisionMixin, PreviewableMixin, models.Model):
    base_form_class = MainMenuAdminForm

    highlights = StreamField(
        [("highlight", HighlightsBlock())],
        blank=True,
        max_num=3,
        help_text=_("Up to 3 highlights. Each highlight must have either a page or a URL."),
    )
    columns = StreamField(
        [("column", ColumnBlock())],
        blank=True,
        max_num=3,
        help_text=_("Up to 3 columns. Each column contains sections with links."),
    )

    _revisions = GenericRelation("wagtailcore.Revision", related_query_name="main_menu")

    @property
    def revisions(self):  # type: ignore[no-untyped-def]
        return self._revisions

    panels: ClassVar[list[Union[str, "Panel"]]] = [
        "highlights",
        "columns",
        PublishingPanel(),
    ]

    def get_preview_template(self, request: "HttpRequest", mode_name: str) -> str:
        return "templates/components/navigation/main_menu_preview.html"

    def __str__(self) -> str:
        return "Main Menu"


@register_setting(icon="list-ul")
class NavigationSettings(BaseSiteSetting):
    main_menu = models.ForeignKey(
        MainMenu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=_("Select the main menu to display on the site."),
    )

    panels: ClassVar[list[str]] = ["main_menu"]
