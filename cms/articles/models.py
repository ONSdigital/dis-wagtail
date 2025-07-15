from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

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

from cms.articles.enums import SortingChoices
from cms.articles.forms import StatisticalArticlePageAdminForm
from cms.articles.panels import HeadlineFiguresFieldPanel
from cms.articles.utils import serialize_correction_or_notice
from cms.bundles.mixins import BundledPageMixin
from cms.core.blocks.headline_figures import HeadlineFiguresItemBlock
from cms.core.blocks.panels import CorrectionBlock, NoticeBlock
from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.custom_date_format import ons_date_format
from cms.core.fields import StreamField
from cms.core.models import BasePage
from cms.core.widgets import date_widget
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.utils import format_datasets_as_document_list
from cms.datavis.blocks.base import BaseVisualisationBlock
from cms.datavis.blocks.featured_charts import FeaturedChartBlock
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


class StatisticalArticlePage(BundledPageMixin, RoutablePageMixin, BasePage):  # type: ignore[django-manager-missing] # pylint: disable=too-many-public-methods
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
    headline_figures = StreamField([("figure", HeadlineFiguresItemBlock())], blank=True, max_num=6)
    headline_figures_figure_ids = models.CharField(
        max_length=128,
        blank=True,
        editable=False,
    )
    content = StreamField(SectionStoryBlock())

    show_cite_this_page = models.BooleanField(default=True)

    corrections = StreamField([("correction", CorrectionBlock())], blank=True, null=True)
    notices = StreamField([("notice", NoticeBlock())], blank=True, null=True)

    dataset_sorting = models.CharField(choices=SortingChoices.choices, default=SortingChoices.AS_SHOWN, max_length=32)
    datasets = StreamField(DatasetStoryBlock(), blank=True, default=list)

    featured_chart = StreamField(FeaturedChartBlock(), blank=True, max_num=1)

    content_panels: ClassVar[list["Panel"]] = [
        *BundledPageMixin.panels,
        MultiFieldPanel(
            [
                TitleFieldPanel(
                    "title",
                    heading="Release Edition",
                    placeholder="Release Edition *",
                    help_text="e.g. 'November 2024'.",
                ),
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
            heading="Edition",
        ),
        FieldPanel("summary", required_on_save=True),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel(
                            "release_date", date_widget, help_text="The actual release date", required_on_save=True
                        ),
                        FieldPanel(
                            "next_release_date",
                            date_widget,
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
                FieldPanel("main_points_summary", required_on_save=True),
            ],
            heading="Metadata",
            icon="cog",
        ),
        HeadlineFiguresFieldPanel("headline_figures", icon="data-analysis"),
        FieldPanel("content", icon="list-ul", required_on_save=True),
    ]

    corrections_and_notices_panels: ClassVar[list["Panel"]] = [
        FieldPanel("corrections", icon="warning"),
        FieldPanel("notices", icon="info-circle"),
    ]

    related_data_panels: ClassVar[list["Panel"]] = [
        "dataset_sorting",
        FieldPanel("datasets", icon="table"),
    ]

    additional_panel_tabs: ClassVar[list[tuple[list["Panel"], str]]] = [
        (related_data_panels, "Related data"),
        (corrections_and_notices_panels, "Corrections and notices"),
    ]

    promote_panels: ClassVar[list["Panel"]] = [
        *BasePage.promote_panels,
        FieldPanel(
            "featured_chart",
            help_text="Configure a chart for when this article is featured on a topic page.",
            icon="chart-line",
        ),
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

        if self.headline_figures and len(self.headline_figures) == 1:
            # Check if headline_figures has 1 item (we can't use min_num because we allow 0)
            raise ValidationError({"headline_figures": "If you add headline figures, please add at least 2."})

        if self.headline_figures and len(self.headline_figures) > 0:
            figure_ids = [figure.value["figure_id"] for figure in self.headline_figures]  # pylint: disable=not-an-iterable
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

        # At this stage we can override the figure ids to account for deleted ones
        self.update_headline_figures_figure_ids(figure_ids)

    def get_admin_display_title(self) -> str:
        """Changes the admin display title to include the parent title."""
        return self.get_full_display_title(self.draft_title)

    def get_full_display_title(self, title: str | None = None) -> str:
        """Returns the full display title for the page, including the parent series title."""
        return f"{self.get_parent().title}: {title or self.title}"

    def get_headline_figure(self, figure_id: str) -> dict[str, str]:
        if not self.headline_figures:
            return {}

        for figure in self.headline_figures:
            if figure.value["figure_id"] == figure_id:
                return dict(figure.value)

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
            id_list = self.headline_figures_figure_ids_list
            id_list.append(figure_id)
            self.headline_figures_figure_ids = FIGURE_ID_SEPARATOR.join(id_list)

    def update_headline_figures_figure_ids(self, figure_ids: list[str]) -> None:
        """Updates the list of headline figures."""
        self.headline_figures_figure_ids = FIGURE_ID_SEPARATOR.join(figure_ids)

    @property
    def display_title(self) -> str:
        """Returns the page display title. If the news headline is set, it takes precedence over the series+title."""
        return self.news_headline.strip() or self.get_full_display_title()

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

        page = revision.as_object()

        # Get corrections and notices for this specific version
        corrections, notices = page.get_serialized_corrections_and_notices(request)

        response: TemplateResponse = self.render(
            request,
            context_overrides={
                "page": page,
                "latest_version_url": self.get_url(request),
                # Override the context with the corrections and notices for this version
                "corrections_and_notices": corrections + notices,
                "has_corrections": bool(corrections),
                "has_notices": bool(notices),
            },
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
        if not series:
            return []
        topic: TopicPage = series.get_parent().specific
        return [
            figure.value["figure_id"] for figure in topic.headline_figures if figure.value["series"].id == series.id
        ]

    @cached_property
    def related_data_display_title(self) -> str:
        return f"{_('All data related to')} {self.title}"

    @cached_property
    def dataset_document_list(self) -> list[dict[str, Any]]:
        dataset_documents = format_datasets_as_document_list(self.datasets)
        if self.dataset_sorting == SortingChoices.ALPHABETIC:
            dataset_documents = sorted(dataset_documents, key=lambda d: d["title"]["text"])
        return dataset_documents

    @path("related-data/")
    def related_data(self, request: "HttpRequest") -> "TemplateResponse":
        if not self.dataset_document_list:
            raise Http404
        paginator = Paginator(self.dataset_document_list, per_page=settings.RELATED_DATASETS_PER_PAGE)

        try:
            paginated_datasets = paginator.page(request.GET.get("page", 1))
            ons_pagination_url_list = [{"url": f"?page={n}"} for n in paginator.page_range]
        except (EmptyPage, PageNotAnInteger) as e:
            raise Http404 from e

        response: TemplateResponse = self.render(
            request,
            context_overrides={
                "paginated_datasets": paginated_datasets,
                "ons_pagination_url_list": ons_pagination_url_list,
            },
            template="templates/pages/statistical_article_page--related_data.html",
        )
        return response

    def as_featured_article_macro_data(self, request: "HttpRequest") -> dict[str, Any]:
        """Returns data formatted for the onsFeaturedArticle Nunjucks/Jinja2 macro."""
        data = {
            "title": {
                "url": self.get_url(request),
                "text": self.listing_title or self.display_title,
            },
            "metadata": {
                "text": self.label,
            },
            "description": self.main_points_summary,
        }

        if self.release_date:
            data["metadata"]["date"] = {
                "prefix": _("Release date"),
                "showPrefix": True,
                "iso": self.release_date.isoformat(),
                "short": ons_date_format(self.release_date, "DATE_FORMAT"),
            }

        if self.featured_chart:
            chart_block = self.featured_chart[0]  # pylint: disable=unsubscriptable-object
            block_instance = chart_block.block
            block_value = chart_block.value

            if isinstance(block_instance, BaseVisualisationBlock):
                data["chart"] = block_instance.get_component_config(block_value)

        elif self.listing_image:
            data["image"] = {
                "src": self.listing_image.get_rendition("width-1252").url,
            }

        return data

    @property
    def preview_modes(self) -> list[tuple[str, str]]:
        return [
            ("default", "Article Page"),
            ("related_data", "Related Data Page"),
            ("featured_article", "Featured Article"),
        ]

    def serve_preview(self, request: "HttpRequest", mode_name: str) -> "TemplateResponse":
        match mode_name:
            case "related_data":
                return cast("TemplateResponse", self.related_data(request))
            case "featured_article":
                from cms.topics.models import TopicPage  # pylint: disable=import-outside-toplevel

                topic_page = TopicPage.objects.ancestor_of(self).first()
                return cast("TemplateResponse", topic_page.serve(request, featured_item=self))
        return cast("TemplateResponse", super().serve_preview(request, mode_name))

    def get_serialized_corrections_and_notices(
        self, request: "HttpRequest"
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Returns a list of corrections and notices for the page."""
        base_url = self.get_url(request)
        corrections = (
            [
                serialize_correction_or_notice(
                    correction,
                    superseded_url=base_url
                    + self.reverse_subpage("previous_version", args=[correction.value["version_id"]]),
                )
                for correction in self.corrections  # pylint: disable=not-an-iterable
            ]
            if self.corrections
            else []
        )
        notices = (
            [serialize_correction_or_notice(notice) for notice in self.notices] if self.notices else []  # pylint: disable=not-an-iterable
        )
        return corrections, notices

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Adds additional context to the page."""
        context: dict = super().get_context(request)

        corrections, notices = self.get_serialized_corrections_and_notices(request)
        context["corrections_and_notices"] = corrections + notices
        context["has_corrections"] = bool(corrections)
        context["has_notices"] = bool(notices)

        return context
