from typing import TYPE_CHECKING, ClassVar

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from wagtail.admin.panels import PublishingPanel
from wagtail.contrib.settings.models import register_setting
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin, TranslatableMixin

from cms.core.fields import StreamField
from cms.core.models import BaseSiteSetting
from cms.navigation.blocks import LinksColumn, MainMenuColumnBlock, MainMenuHighlightsBlock
from cms.navigation.forms import FooterMenuAdminForm, MainMenuAdminForm

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


class MainMenu(TranslatableMixin, DraftStateMixin, RevisionMixin, PreviewableMixin, models.Model):
    base_form_class = MainMenuAdminForm

    highlights = StreamField(
        [("highlight", MainMenuHighlightsBlock())],
        blank=True,
        max_num=3,
        help_text="Up to 3 highlights. Each highlight must have either a page or a URL.",
    )
    columns = StreamField(
        [("column", MainMenuColumnBlock())],
        blank=True,
        max_num=3,
        help_text="Up to 3 columns. Each column contains sections with links.",
    )

    _revisions = GenericRelation("wagtailcore.Revision", related_query_name="main_menu")

    @property
    def revisions(self):  # type: ignore[no-untyped-def]
        return self._revisions

    @property
    def name(self) -> str:
        return f"{self} ({self.locale})"  # To avoid ambiguity, we include the locale

    panels: ClassVar[list[str | Panel]] = [
        "highlights",
        "columns",
        PublishingPanel(),
    ]

    def get_preview_template(self, request: HttpRequest, mode_name: str) -> str:
        return "templates/components/navigation/main_menu_preview.html"

    def __str__(self) -> str:
        return "Main Menu"


class FooterMenu(TranslatableMixin, DraftStateMixin, RevisionMixin, PreviewableMixin, models.Model):
    base_form_class = FooterMenuAdminForm

    columns = StreamField(
        [("column", LinksColumn())],
        blank=True,
        max_num=3,
        help_text="Up to 3 columns. Each column contains a title with links.",
    )
    _revisions = GenericRelation("wagtailcore.Revision", related_query_name="footer_menu")

    @property
    def revisions(self):  # type: ignore[no-untyped-def]
        return self._revisions

    @property
    def name(self) -> str:
        return f"{self} ({self.locale})"  # To avoid ambiguity, we include the locale

    panels: ClassVar[list] = [
        "columns",
        PublishingPanel(),
    ]

    def get_preview_template(self, request: HttpRequest, mode_name: str) -> str:
        return "templates/components/navigation/footer_menu_preview.html"

    def __str__(self) -> str:
        return "Footer Menu"


@register_setting(icon="list-ul")
class NavigationSettings(BaseSiteSetting):
    main_menu = models.ForeignKey(
        MainMenu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Select the main menu to display on the site.",
    )

    footer_menu = models.ForeignKey(
        FooterMenu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Select the footer menu to display on the site.",
    )

    panels: ClassVar[list] = ["main_menu", "footer_menu"]
