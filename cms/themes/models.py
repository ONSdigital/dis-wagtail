from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.utils.functional import cached_property
from wagtail.admin.panels import HelpPanel
from wagtail.fields import RichTextField
from wagtail.models import PanelPlaceholder

from cms.core.formatting_utils import get_document_metadata
from cms.core.models import BasePage, ListingFieldsMixin, SocialFieldsMixin
from cms.core.utils import get_content_type_for_page
from cms.taxonomy.mixins import ExclusiveTaxonomyMixin

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


class ThemeIndexPage(BasePage):  # type: ignore[django-manager-missing]
    template = "templates/pages/theme_index_page.html"
    max_count_per_parent = 1
    # TODO: for day 2, remove the following 2 attributes and uncomment the ones below to enable the Browse/Index page
    parent_page_types: ClassVar[list[str]] = []
    subpage_types: ClassVar[list[str]] = []
    # parent_page_types: ClassVar[list[str]] = ["home.HomePage"]
    # subpage_types: ClassVar[list[str]] = ["ThemePage"]
    page_description = "A container for the list of themes."
    label = "Themes"

    content_panels: ClassVar[list[Panel]] = [
        *BasePage.content_panels,
        HelpPanel(content="This is a container for articles and article series for URL structure purposes."),
    ]
    promote_panels: ClassVar[list[Panel]] = [
        PanelPlaceholder(  # this follows Page.promote_panels, sans "slug"
            "wagtail.admin.panels.MultiFieldPanel",
            [
                [
                    "seo_title",
                    "search_description",
                ],
                "For search engines",
            ],
            {},
        ),
        *ListingFieldsMixin.promote_panels,
        *SocialFieldsMixin.promote_panels,
    ]

    def clean(self) -> None:
        self.slug = "browse"
        super().clean()

    def minimal_clean(self) -> None:
        # ensure the slug is always set to "browse", even for saving drafts, where minimal_clean is used
        self.slug = "browse"
        super().minimal_clean()

    def get_formatted_child_pages(self, request: HttpRequest) -> list[dict[str, dict[str, str] | Any]]:
        formatted_items = []

        for child_page in self.get_children().live().public().specific().defer_streamfields():
            formatted_items.append(
                {
                    "featured": "false",
                    "title": {
                        "text": getattr(child_page, "listing_title", "") or child_page.title,
                        "url": child_page.get_url(request=request),
                    },
                    "description": getattr(child_page, "listing_summary", "") or getattr(child_page, "summary", ""),
                    "metadata": get_document_metadata(
                        get_content_type_for_page(child_page), child_page.specific_deferred.publication_date
                    ),
                }
            )
        return formatted_items

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        context: dict = super().get_context(request, *args, **kwargs)
        context["formatted_items"] = self.get_formatted_child_pages(request)
        return context


class ThemePage(ExclusiveTaxonomyMixin, BasePage):  # type: ignore[django-manager-missing]
    """The Theme page model."""

    template = "templates/pages/theme_page.html"
    parent_page_types: ClassVar[list[str]] = ["ThemeIndexPage", "ThemePage"]
    subpage_types: ClassVar[list[str]] = ["ThemePage"]
    page_description = "A theme page, such as 'Economy'."
    label = "Theme"

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    content_panels: ClassVar[list[Panel]] = [*BasePage.content_panels, "summary"]

    @cached_property
    def analytics_content_type(self) -> str:  # pylint: disable=invalid-overridden-method
        """Return the Google Tag Manager content type for this page, which should be "themes" for top-level theme
        pages and "sub-themes" for theme pages under other theme pages.
        """
        if isinstance(self.get_parent().specific_deferred, ThemePage):
            return "sub-themes"
        return "themes"
