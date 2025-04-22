from typing import TYPE_CHECKING, Any, ClassVar, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel, HelpPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index

from cms.articles.forms import PageWithHeadlineFiguresAdminForm
from cms.bundles.models import BundledPageMixin
from cms.core.blocks import HeadlineFiguresBlock
from cms.core.blocks.panels import CorrectionBlock, NoticeBlock
from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.fields import StreamField
from cms.core.forms import PageWithCorrectionsAdminForm
from cms.core.models import BasePage
from cms.taxonomy.mixins import GenericTaxonomyMixin

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.http.response import HttpResponseRedirect
    from django.template.response import TemplateResponse
    from wagtail.admin.panels import Panel

    from cms.topics.models import TopicPage

FIGURE_ID_SEPARATOR = ","


class ArticleSeriesPage(RoutablePageMixin, GenericTaxonomyMixin, BasePage):  # type: ignore[django-manager-missing]
    """The article series model."""

    parent_page_types: ClassVar[list[str]] = ["topics.TopicPage"]
    subpage_types: ClassVar[list[str]] = ["StatisticalArticlePage"]
    preview_modes: ClassVar[list[str]] = []  # Disabling the preview mode due to it being a container page.
    page_description = "A container for statistical article series."
    exclude_from_breadcrumbs = True

    content_panels: ClassVar[list["Panel"]] = [
        *Page.content_panels,
        HelpPanel(
            content=(
                "This is a container for article series. It provides the <code>/latest</code>,"
                "<code>/previous-releases</code> evergreen paths, "
                "as well as the actual statistical article pages. "
                "Add a new Statistical article page under this container."
            )
        ),
    ]

    def get_latest(self) -> Optional["StatisticalArticlePage"]:
        latest: StatisticalArticlePage | None = (
            StatisticalArticlePage.objects.live().child_of(self).order_by("-release_date").first()
        )
        return latest

    @path("")
    def index(self, request: "HttpRequest") -> "HttpResponseRedirect":
        """Redirect to /latest as this is a container page without its own content."""
        return redirect(self.get_url(request) + self.reverse_subpage("latest_release"))

    @path("latest/")
    def latest_release(self, request: "HttpRequest") -> "TemplateResponse":
        """Serves the latest statistical article page in the series."""
        latest = self.get_latest()
        if not latest:
            raise Http404
        response: TemplateResponse = latest.serve(request)
        return response

    @path("previous-releases/")
    def previous_releases(self, request: "HttpRequest") -> "TemplateResponse":
        children = StatisticalArticlePage.objects.live().child_of(self).order_by("-release_date")
        paginator = Paginator(children, per_page=settings.PREVIOUS_RELEASES_PER_PAGE)

        try:
            pages = paginator.page(request.GET.get("page", 1))
            ons_pagination_url_list = [{"url": f"?page={n}"} for n in paginator.page_range]
        except (EmptyPage, PageNotAnInteger) as e:
            raise Http404 from e

        response: TemplateResponse = self.render(
            request,
            # TODO: update to include drafts when looking at previews holistically.
            context_overrides={"pages": pages, "ons_pagination_url_list": ons_pagination_url_list},
            template="templates/pages/statistical_article_page--previous-releases.html",
        )
        return response


class StatisticalArticlePageAdminForm(PageWithHeadlineFiguresAdminForm, PageWithCorrectionsAdminForm): ...


class StatisticalArticlePage(BundledPageMixin, RoutablePageMixin, BasePage):  # type: ignore[django-manager-missing]
    """The statistical article page model.

    Previously known as statistical bulletin, statistical analysis article, analysis page.
    """

    base_form_class = StatisticalArticlePageAdminForm

    parent_page_types: ClassVar[list[str]] = ["ArticleSeriesPage"]
    subpage_types: ClassVar[list[str]] = []
    search_index_content_type: ClassVar[str] = "bulletin"
    template = "templates/pages/statistical_article_page.html"
    label = _("Article")  # type: ignore[assignment]

    # Fields
    news_headline = models.CharField(max_length=255, blank=True)
    summary = RichTextField(features=settings.RICH_TEXT_BASIC)

    main_points_summary = RichTextField(
        features=settings.RICH_TEXT_BASIC, help_text="Used when featured on a topic page."
    )

    # Fields: dates
    release_date = models.DateField()
    next_release_date = models.DateField(blank=True, null=True)

    contact_details = models.ForeignKey(
        "core.ContactDetails",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # Fields: accredited/census. A bit of "about the data".
    is_accredited = models.BooleanField(
        "Accredited Official Statistics",
        default=False,
        help_text=(
            "If ticked, will display an information block about the data being accredited official statistics "
            "and include the accredited logo."
        ),
    )
    is_census = models.BooleanField(
        "Census",
        default=False,
        help_text="If ticked, will display an information block about the data being related to the Census.",
    )

    # Fields: content
    headline_figures = StreamField([("figures", HeadlineFiguresBlock())], blank=True, max_num=1)
    headline_figures_figure_ids = models.CharField(
        max_length=128,
        blank=True,
        editable=False,
    )
    content = StreamField(SectionStoryBlock())

    show_cite_this_page = models.BooleanField(default=True)

    corrections = StreamField([("correction", CorrectionBlock())], blank=True, null=True)
    notices = StreamField([("notice", NoticeBlock())], blank=True, null=True)

    content_panels: ClassVar[list["Panel"]] = [
        *BundledPageMixin.panels,
        MultiFieldPanel(
            [
                TitleFieldPanel("title", help_text="Also known as the release edition. e.g. 'November 2024'."),
                FieldPanel(
                    "news_headline",
                    help_text=(
                        "Use this as a news headline. When populated, replaces the title displayed on the page. "
                        "Note: the page slug is powered by the title field. "
                        "You can change the slug in the 'Promote' tab."
                    ),
                    icon="news",
                ),
            ],
            heading="Title",
        ),
        "summary",
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("release_date", help_text="The actual release date"),
                        FieldPanel(
                            "next_release_date",
                            help_text="If no next date is chosen, 'To be announced' will be displayed.",
                        ),
                    ],
                    heading="Dates",
                ),
                FieldRowPanel(
                    ["is_accredited", "is_census"],
                    heading="About the data",
                ),
                "contact_details",
                "show_cite_this_page",
                "main_points_summary",
            ],
            heading="Metadata",
            icon="cog",
        ),
        FieldPanel("headline_figures", icon="data-analysis"),
        FieldPanel("content", icon="list-ul"),
    ]

    corrections_and_notices_panels: ClassVar[list["Panel"]] = [
        FieldPanel("corrections", icon="warning"),
        FieldPanel("notices", icon="info-circle"),
    ]

    additional_panel_tabs: ClassVar[list[tuple[list["Panel"], str]]] = [
        (corrections_and_notices_panels, "Corrections and notices")
    ]

    search_fields: ClassVar[list[index.BaseField]] = [
        *BasePage.search_fields,
        index.SearchField("summary"),
        index.SearchField("headline_figures"),
        index.SearchField("content"),
        index.SearchField("get_admin_display_title", boost=2),
        index.AutocompleteField("get_admin_display_title"),
        index.SearchField("news_headline"),
        index.AutocompleteField("news_headline"),
    ]

    def clean(self) -> None:
        """Additional validation on save."""
        super().clean()

        if self.next_release_date and self.next_release_date <= self.release_date:
            raise ValidationError({"next_release_date": "The next release date must be after the release date."})

        if self.headline_figures and len(self.headline_figures) > 0:
            figure_ids = [figure["figure_id"] for figure in self.headline_figures[0].value]  # pylint: disable=unsubscriptable-object
        else:
            figure_ids = []

        figure_ids_set = set(figure_ids)
        existing_figure_ids_set = set(self.headline_figures_figure_ids_list)

        # Check if the provided figure IDs have been registered by our custom form
        if any(item not in existing_figure_ids_set for item in figure_ids_set):
            # This means someone tampered with the figure ID
            raise ValidationError({"headline_figures": "Invalid figure ID(s) provided."})

        if self.pk and self.is_latest:
            for headline_figure in self.figures_used_by_ancestor:
                if headline_figure not in figure_ids:
                    raise ValidationError(
                        {
                            "headline_figures": f"Figure ID {
                                headline_figure
                            } cannot be removed as it is referenced in a topic page.",
                        }
                    )

        # At this stage we can ovveride the figure ids to account for deleted ones
        self.update_headline_figures_figure_ids(figure_ids)

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        return context

    def get_admin_display_title(self) -> str:
        """Changes the admin display title to include the parent title."""
        return f"{self.get_parent().title}: {self.draft_title or self.title}"

    def get_headline_figure(self, figure_id: str) -> dict[str, str]:
        if not self.headline_figures:
            return {}

        for figure in self.headline_figures[0].value:  # pylint: disable=unsubscriptable-object
            if figure["figure_id"] == figure_id:
                return dict(figure)

        return {}

    @property
    def headline_figures_figure_ids_list(self) -> list[str]:
        """Returns a list of figure IDs from the headline figures."""
        if self.headline_figures_figure_ids:
            return self.headline_figures_figure_ids.split(FIGURE_ID_SEPARATOR)
        return []

    def add_headline_figures_figure_id(self, figure_id: str) -> None:
        """Adds a figure ID to the list of headline figures."""
        if figure_id not in self.headline_figures_figure_ids_list:
            self.headline_figures_figure_ids_list.append(figure_id)
            self.headline_figures_figure_ids = FIGURE_ID_SEPARATOR.join(self.headline_figures_figure_ids_list)

    def update_headline_figures_figure_ids(self, figure_ids: list[str]) -> None:
        """Updates the list of headline figures."""
        self.headline_figures_figure_ids = FIGURE_ID_SEPARATOR.join(figure_ids)

    @property
    def display_title(self) -> str:
        """Returns the page display title. If the news headline is set, it takes precedence over the series+title."""
        return self.news_headline.strip() or self.get_admin_display_title()

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = []
        for block in self.content:  # pylint: disable=not-an-iterable,useless-suppression
            if hasattr(block.block, "to_table_of_contents_items"):
                items += block.block.to_table_of_contents_items(block.value)
        if self.show_cite_this_page:
            items += [{"url": "#cite-this-page", "text": _("Cite this article")}]
        if self.contact_details_id:
            items += [{"url": "#contact-details", "text": _("Contact details")}]
        return items

    @property
    def is_latest(self) -> bool:
        """Returns True if the statistical article page is latest in its series based on the release date."""
        latest_id = (
            StatisticalArticlePage.objects.sibling_of(self)
            .live()
            .order_by("-release_date")
            .values_list("id", flat=True)
            .first()
        )
        return bool(self.pk == latest_id)  # to placate mypy

    @path("previous/v<int:version>/")
    def previous_version(self, request: "HttpRequest", version: int) -> "TemplateResponse":
        if version <= 0 or not self.corrections:
            raise Http404

        # Find correction by version
        for correction in self.corrections:  # pylint: disable=not-an-iterable
            if correction.value["version_id"] == version:
                break
        else:
            raise Http404

        # NB: Little validation is done on previous_version, as it's assumed handled on save
        revision = get_object_or_404(self.revisions, pk=correction.value["previous_version"])

        response: TemplateResponse = self.render(
            request, context_overrides={"page": revision.as_object(), "latest_version_url": self.get_url(request)}
        )

        return response

    @property
    def topic_ids(self) -> list[str]:
        """Returns a list of topic IDs associated with the parent article series page."""
        return list(self.get_parent().specific_deferred.topics.values_list("topic_id", flat=True))

    @property
    def figures_used_by_ancestor(self) -> list[str]:
        """Returns a list of figure IDs used by the ancestor topic page."""
        series = self.get_parent()
        topic: TopicPage = series.get_parent().specific
        return [figure.value["figure"] for figure in topic.headline_figures if figure.value["series"].id == series.id]
