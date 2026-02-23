import logging
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel, HelpPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.contrib.routable_page.models import path
from wagtail.coreutils import WAGTAIL_APPEND_SLASH, resolve_model_string
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index
from wagtailschemaorg.utils import extend

from cms.articles.enums import SortingChoices
from cms.articles.forms import StatisticalArticlePageAdminForm
from cms.articles.panels import HeadlineFiguresFieldPanel
from cms.articles.utils import serialize_correction_or_notice
from cms.bundles.mixins import BundledPageMixin
from cms.core.analytics_utils import add_table_of_contents_gtm_attributes, bool_to_yes_no, format_date_for_gtm
from cms.core.blocks.headline_figures import HeadlineFiguresItemBlock
from cms.core.blocks.panels import CorrectionBlock, NoticeBlock
from cms.core.blocks.stream_blocks import SectionStoryBlock
from cms.core.custom_date_format import ons_date_format
from cms.core.fields import StreamField
from cms.core.models import BasePage
from cms.core.models.mixins import NoTrailingSlashRoutablePageMixin
from cms.core.utils import redirect_to_parent_listing
from cms.core.widgets import date_widget
from cms.data_downloads.mixins import DataDownloadMixin
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.utils import format_datasets_as_document_list
from cms.datavis.blocks.base import BaseChartBlock
from cms.datavis.blocks.featured_charts import FeaturedChartBlock
from cms.taxonomy.mixins import GenericTaxonomyMixin

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from django.template.response import TemplateResponse
    from wagtail.admin.panels import Panel


logger = logging.getLogger(__name__)

FIGURE_ID_SEPARATOR = ","


class ArticlesIndexPage(BasePage):  # type: ignore[django-manager-missing]
    max_count_per_parent = 1
    parent_page_types: ClassVar[list[str]] = ["topics.TopicPage"]
    page_description = "A container for statistical article series. Used for URL structure purposes."
    preview_modes: ClassVar[list[str]] = []  # Disabling the preview mode as this redirects away

    content_panels: ClassVar[list[Panel]] = [
        *Page.content_panels,
        HelpPanel(content="This is a container for articles and article series for URL structure purposes."),
    ]
    # disables the "Promote" tab as we control the slug, and the page redirects
    promote_panels: ClassVar[list[Panel]] = []

    def clean(self) -> None:
        self.slug = "articles"
        super().clean()

    def minimal_clean(self) -> None:
        # ensure the slug is always set to "articles", even for saving drafts, where minimal_clean is used
        self.slug = "articles"
        super().minimal_clean()

    def serve(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Redirects article series index page requests to the parent topic's articles search URL.
        return redirect_to_parent_listing(page=self, request=request, listing_url_method_name="get_articles_search_url")


class ArticleSeriesPage(  # type: ignore[django-manager-missing]
    NoTrailingSlashRoutablePageMixin,
    GenericTaxonomyMixin,
    BasePage,
):
    """The article series model."""

    parent_page_types: ClassVar[list[str]] = ["ArticlesIndexPage"]
    subpage_types: ClassVar[list[str]] = ["StatisticalArticlePage"]
    preview_modes: ClassVar[list[str]] = []  # Disabling the preview mode due to it being a container page.
    page_description = "A container for statistical articles in a series."
    exclude_from_breadcrumbs = True

    content_panels: ClassVar[list[Panel]] = [
        *Page.content_panels,
        HelpPanel(
            content=(
                "<p>This is a container for article series.</p>"
                "<p>It provides the following evergreen paths: <br>- <code>series-slug/</code> "
                "(for the latest article in series. Previously <code>series-slug/latest</code>)<br>"
                "- <code>series-slug/editions</code> (previously <code>series-slug/previous-releases</code>)</br>"
                "as well as the actual statistical article pages.</p>"
                "<p>Add a new Statistical article page under this container.</p>"
            )
        ),
    ]

    def get_latest(self) -> StatisticalArticlePage | None:
        latest: StatisticalArticlePage | None = (
            StatisticalArticlePage.objects.live().child_of(self).order_by("-release_date").first()
        )
        return latest

    @path("")
    def latest_article(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Serves the latest statistical article page in the series."""
        if not (latest := self.get_latest()):
            raise Http404

        return latest.serve(request, *args, serve_as_edition=True, **kwargs)

    @path("related-data/")
    def latest_article_related_data(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Serves the related data for the latest statistical article page in the series."""
        if not (latest := self.get_latest()):
            raise Http404

        request.is_for_subpage = True  # type: ignore[attr-defined]
        response: HttpResponse = latest.related_data(request, *args, **kwargs)
        return response

    @path("editions/")
    def previous_releases(self, request: HttpRequest) -> TemplateResponse:
        children = StatisticalArticlePage.objects.live().child_of(self).order_by("-release_date")
        paginator = Paginator(children, per_page=settings.PREVIOUS_RELEASES_PER_PAGE)

        try:
            pages = paginator.page(request.GET.get("page", 1))
            ons_pagination_url_list = [{"url": f"?page={n}"} for n in paginator.page_range]
        except (EmptyPage, PageNotAnInteger) as e:
            raise Http404 from e

        request.is_for_subpage = True  # type: ignore[attr-defined]
        response: TemplateResponse = self.render(
            request,
            # TODO: update to include drafts when looking at previews holistically.
            context_overrides={"pages": pages, "ons_pagination_url_list": ons_pagination_url_list},
            template="templates/pages/statistical_article_page--previous-releases.html",
        )
        return response

    @path("editions/<str:slug>/")
    def release(self, request: HttpRequest, slug: str, **kwargs: Any) -> HttpResponse:
        if not (edition := StatisticalArticlePage.objects.live().child_of(self).filter(slug=slug).first()):
            raise Http404
        response: HttpResponse = edition.serve(request, serve_as_edition=True, **kwargs)
        return response

    @path("editions/<str:slug>/related-data/")
    def release_related_data(self, request: HttpRequest, slug: str) -> HttpResponse:
        response: HttpResponse = self.release(request, slug, related_data=True)
        return response

    @path("editions/<str:slug>/versions/<int:version>/")
    def release_with_versions(self, request: HttpRequest, slug: str, version: int) -> HttpResponse:
        response: HttpResponse = self.release(request, slug, version=version)
        return response

    @path("editions/<str:slug>/download-chart/<str:chart_id>/")
    def download_chart(self, request: HttpRequest, slug: str, chart_id: str) -> HttpResponse:
        if not (edition := StatisticalArticlePage.objects.live().child_of(self).filter(slug=slug).first()):
            raise Http404
        response: HttpResponse = edition.download_chart(request, chart_id)
        return response

    @path("editions/<str:slug>/versions/<int:version>/download-chart/<str:chart_id>/")
    def download_chart_with_version(self, request: HttpRequest, slug: str, version: int, chart_id: str) -> HttpResponse:
        response: HttpResponse = self.release(request, slug, version=version, chart_id=chart_id)
        return response

    @path("editions/<str:slug>/download-table/<str:table_id>/")
    def download_table(self, request: HttpRequest, slug: str, table_id: str) -> HttpResponse:
        if not (edition := StatisticalArticlePage.objects.live().child_of(self).filter(slug=slug).first()):
            raise Http404
        response: HttpResponse = edition.download_table(request, table_id)
        return response

    @path("editions/<str:slug>/versions/<int:version>/download-table/<str:table_id>/")
    def download_table_with_version(self, request: HttpRequest, slug: str, version: int, table_id: str) -> HttpResponse:
        response: HttpResponse = self.release(request, slug, version=version, table_id=table_id)
        return response


# pylint: disable=too-many-public-methods
class StatisticalArticlePage(  # type: ignore[django-manager-missing]
    DataDownloadMixin,
    BundledPageMixin,
    NoTrailingSlashRoutablePageMixin,
    BasePage,
):
    """The statistical article page model.

    Previously known as statistical bulletin, statistical analysis article, analysis page.
    """

    base_form_class = StatisticalArticlePageAdminForm

    schema_org_type = "Article"

    parent_page_types: ClassVar[list[str]] = ["ArticleSeriesPage"]
    subpage_types: ClassVar[list[str]] = []
    search_index_content_type: ClassVar[str] = "statistical_article"
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

    content_panels: ClassVar[list[Panel]] = [
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

    corrections_and_notices_panels: ClassVar[list[Panel]] = [
        FieldPanel("corrections", icon="warning"),
        FieldPanel("notices", icon="info-circle"),
    ]

    related_data_panels: ClassVar[list[Panel]] = [
        "dataset_sorting",
        FieldPanel("datasets", icon="table"),
    ]

    additional_panel_tabs: ClassVar[list[tuple[list[Panel], str]]] = [
        (related_data_panels, "Related data"),
        (corrections_and_notices_panels, "Corrections and notices"),
    ]

    promote_panels: ClassVar[list[Panel]] = [
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

    _analytics_content_type = "articles"

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
                            "headline_figures": f"Figure ID {headline_figure} cannot "
                            "be removed as it is referenced in a topic page.",
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
        add_table_of_contents_gtm_attributes(items)
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

        # using this rather than inline import to placate pyright complaining about cyclic imports
        topic_page_class = resolve_model_string("topics.TopicPage")
        topic = topic_page_class.objects.ancestor_of(self).first().specific_deferred
        return [
            figure.value["figure_id"]
            for figure in topic.headline_figures
            if figure.value["series"].id == series.id
            and figure.value["figure_id"] in self.headline_figures_figure_ids_list
        ]

    @property
    def figures_used_by_ancestor_with_no_fallback(self) -> set[str]:
        """Returns the set of figure IDs used by the ancestor topic page, for which there are no values to fall back on
        from the previous to latest article in the series.
        """
        if not self.is_latest:
            # Figures are only ever used from the latest article in the series
            return set()

        figures_in_use = set(self.figures_used_by_ancestor)
        if not figures_in_use:
            return set()

        articles_headline_figures = (
            StatisticalArticlePage.objects.sibling_of(self)
            .live()
            .order_by("-release_date")
            .values_list("headline_figures", flat=True)
        )
        if len(articles_headline_figures) <= 1:
            # This is the only article in the series, so all figures in use have no fallback
            return figures_in_use

        previous_to_latest_figures = articles_headline_figures[1]
        previous_figure_ids = {figure.value["figure_id"] for figure in previous_to_latest_figures}
        return figures_in_use - previous_figure_ids

    @cached_property
    def related_data_display_title(self) -> str:
        return _("All data related to %(article_title)s") % {"article_title": self.title}

    @cached_property
    def dataset_document_list(self) -> list[dict[str, Any]]:
        dataset_documents = format_datasets_as_document_list(self.datasets)
        if self.dataset_sorting == SortingChoices.ALPHABETIC:
            dataset_documents = sorted(dataset_documents, key=lambda d: d["title"]["text"])
        return dataset_documents

    @cached_property
    def parent_for_choosers(self) -> Page:
        """Used in the bundle page chooser.

        Return the Topic page as the parent because the chooser already includes the
        series title as part of the admin display title.
        """
        topic_page_class = resolve_model_string("topics.TopicPage")
        return topic_page_class.objects.ancestor_of(self).first().specific_deferred

    def get_serialized_corrections_and_notices(
        self, request: HttpRequest
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Returns a list of corrections and notices for the page."""
        base_url = self.get_url(request) or ""
        if not WAGTAIL_APPEND_SLASH:
            # Add the trailing slash as this will be concatenated
            base_url += "/"
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

    def as_featured_article_macro_data(self, request: HttpRequest) -> dict[str, Any]:
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

            if isinstance(block_instance, BaseChartBlock):
                data["chart"] = block_instance.get_component_config(block_value)

        elif self.listing_image:
            data["image"] = {
                "src": self.listing_image.get_rendition("width-1252").url,
            }

        return data

    def ld_entity(self) -> dict[str, object]:
        """Add statistical article specific schema properties to JSON LD."""
        # TODO pass through request to this, once wagtailschemaorg supports it
        # https://github.com/neon-jungle/wagtail-schema.org/issues/29
        properties = {
            "url": self.get_full_url(),
            "headline": self.seo_title or self.listing_title or self.get_full_display_title(),
            "description": self.search_description or self.listing_summary or strip_tags(self.summary),
            "datePublished": self.release_date.isoformat(),
            "license": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
            "author": {
                "@type": "Person" if self.contact_details else "Organization",
                "name": self.contact_details.name if self.contact_details else settings.ONS_ORGANISATION_NAME,
            },
            "publisher": {
                "@type": "Organization",
                "name": settings.ONS_ORGANISATION_NAME,
                "url": settings.ONS_WEBSITE_BASE_URL,
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": self.get_full_url(),
            },
        }
        return cast(dict[str, object], extend(super().ld_entity(), properties))

    def get_canonical_url(self, request: HttpRequest) -> str:
        """Get the article page canonical URL for the given request.
        If the article is the latest in the series, this will be the evergreen series URL.
        Otherwise, it will be the default canonical page URL.
        """
        canonical_page = self.alias_of.specific_deferred if self.alias_of_id else self

        if canonical_page.is_latest:
            if getattr(request, "is_for_subpage", False) and getattr(request, "canonical_url", False):
                # Special case for sub-routes of latest article in a series
                url = request.canonical_url  # type: ignore[attr-defined]
                return cast(str, url)
            return cast(str, canonical_page.get_parent().specific_deferred.get_full_url(request=request))

        return super().get_canonical_url(request=request)

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        """Adds additional context to the page."""
        context: dict = super().get_context(request)

        corrections, notices = self.get_serialized_corrections_and_notices(request)
        context["corrections_and_notices"] = corrections + notices
        context["has_corrections"] = bool(corrections)
        context["has_notices"] = bool(notices)

        return context

    @property
    def preview_modes(self) -> list[tuple[str, str]]:
        return [
            ("default", "Article Page"),
            ("related_data", "Related Data Page"),
            ("featured_article", "Featured Article"),
        ]

    def serve_preview(self, request: HttpRequest, mode_name: str) -> TemplateResponse:
        match mode_name:
            case "related_data":
                return cast("TemplateResponse", self.related_data(request))
            case "featured_article":
                # using this rather than inline import to placate pyright complaining about cyclic imports
                topic_page_class = resolve_model_string("topics.TopicPage")
                topic_page = topic_page_class.objects.ancestor_of(self).first()
                return cast("TemplateResponse", topic_page.serve(request, featured_item=self))
        return cast("TemplateResponse", super().serve_preview(request, mode_name))

    @path("versions/<int:version>/")
    def previous_version(self, request: HttpRequest, version: int, **kwargs: Any) -> TemplateResponse | HttpResponse:
        if version <= 0 or not self.corrections:
            raise Http404

        # Find correction by version
        for correction in self.corrections:
            if correction.value["version_id"] == version:
                break
        else:
            raise Http404

        # NB: Little validation is done on previous_version, as it's assumed handled on save
        revision = get_object_or_404(self.revisions, pk=correction.value["previous_version"])

        page = revision.as_object()

        chart_id = kwargs.pop("chart_id", None)
        table_id = kwargs.pop("table_id", None)

        if chart_id:
            download_response: HttpResponse = page.download_chart(request, chart_id)
            return download_response

        if table_id:
            download_response = page.download_table(request, table_id)
            return download_response

        # Get corrections and notices for this specific version
        corrections, notices = page.get_serialized_corrections_and_notices(request)

        response: TemplateResponse = self.render(
            request,
            context_overrides={
                "page": page,
                "latest_version_url": self.get_url(request),
                "no_index": True,
                # Override the context with the corrections and notices for this version
                "corrections_and_notices": corrections + notices,
                "has_corrections": bool(corrections),
                "has_notices": bool(notices),
                # Used by chart blocks to build versioned download URLs
                "superseded_version": version,
            },
        )

        return response

    @path("related-data/")
    def related_data(self, request: HttpRequest) -> TemplateResponse:
        if not self.dataset_document_list:
            raise Http404

        request.is_for_subpage = True  # type: ignore[attr-defined]

        canonical_page = self.alias_of.specific_deferred if self.alias_of_id else self
        if canonical_page.is_latest:
            request.canonical_url = (  # type: ignore[attr-defined]
                canonical_page.get_parent().specific_deferred.get_full_url(request) + "/related-data"
            )
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

    def get_url_parts(self, request: HttpRequest | None = None) -> tuple[int, str | None, str | None] | None:
        url_parts = super().get_url_parts(request=request)
        if url_parts is None:
            return None

        site_id: int = url_parts[0]
        root_url: str | None = url_parts[1]
        page_path: str | None = url_parts[2]

        if not (root_url and page_path):
            return site_id, root_url, page_path

        # inject the "edition" slug before the page slug in the path
        # works in conjunction with ArticleSeriesPage.release()
        split = page_path.strip("/").split("/")
        split.insert(-1, "editions")
        page_path = "/".join(["", *split, ""])

        if not WAGTAIL_APPEND_SLASH and page_path != "/":
            page_path = page_path.rstrip("/")

        return site_id, root_url, page_path

    def serve(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle the page serving with the /editions/ virtual slug.

        Note: if you add routes to the page model, coordinate with ArticleSeriesPage paths.
        """
        serve_as_edition = kwargs.pop("serve_as_edition", False)
        if not serve_as_edition:
            # if for some reason we're getting the non-editioned path
            # redirect to the path with the /edition/ slug
            page_url = self.get_url(request=request)
            if not page_url:
                raise Http404
            if page_url != request.path:
                return redirect(page_url)

        if kwargs.pop("related_data", None):
            view, _view_args, view_kwargs = self.resolve_subpage("/related-data/")
            serve_kwargs = {**kwargs, **view_kwargs}
            return cast("HttpResponse", super().serve(request, view=view, args=args, kwargs=serve_kwargs))

        if version := kwargs.pop("version", None):
            view, _view_args, view_kwargs = self.resolve_subpage(f"/versions/{version}/")
            serve_kwargs = {**kwargs, **view_kwargs}
            return cast("HttpResponse", super().serve(request, view=view, args=args, kwargs=serve_kwargs))

        if version == 0:
            raise Http404

        return cast("HttpResponse", super().serve(request, *args, **kwargs))

    @cached_property
    def cached_analytics_values(self) -> dict[str, str | bool]:
        parent_series = self.get_parent()

        values = {
            "pageTitle": self.display_title,
            "outputSeries": parent_series.slug,
            "outputEdition": self.slug,
            "releaseDate": format_date_for_gtm(self.release_date),
            "latestRelease": bool_to_yes_no(self.is_latest),
            "wordCount": self.word_count,
        }

        if self.next_release_date:
            values["nextReleaseDate"] = format_date_for_gtm(self.next_release_date)
        return super().cached_analytics_values | values

    def get_analytics_values(self, request: HttpRequest) -> dict[str, str | bool]:
        values = self.cached_analytics_values
        if self.is_latest and request.path == self.get_url(request):
            # If this is the latest release, but the request path is the full page URL, not the evergreen latest,
            # then include the evergreen latest URL (the parent series URL) in the analytics values.
            values["pageURL"] = self.get_parent().specific_deferred.get_full_url(request)
        return values

    @cached_property
    def word_count(self) -> int:
        """Returns the total word count for the article page's display title, summary and content."""
        # Render the content as HTML and get the text without HTML tags so we can count words
        html_content = self.content.render_as_block()
        soup_content = BeautifulSoup(str(html_content), "html.parser")
        stripped_content = soup_content.get_text()
        content_word_count = len(str(stripped_content).split())

        title_word_count = len(self.display_title.split())
        summary_word_count = len(strip_tags(self.summary).split())

        return title_word_count + summary_word_count + content_word_count
