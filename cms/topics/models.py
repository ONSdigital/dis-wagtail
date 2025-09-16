from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import OuterRef, Subquery
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page, PagePermissionTester
from wagtail.search import index

from cms.articles.models import ArticleSeriesPage, StatisticalArticlePage
from cms.bundles.mixins import BundledPageMixin
from cms.core.analytics_utils import add_table_of_contents_gtm_attributes
from cms.core.fields import StreamField
from cms.core.formatting_utils import get_formatted_pages_list
from cms.core.models import BasePage
from cms.core.query import order_by_pk_position
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.utils import format_datasets_as_document_list
from cms.methodology.models import MethodologyPage
from cms.taxonomy.mixins import ExclusiveTaxonomyMixin
from cms.topics.blocks import ExploreMoreStoryBlock, TimeSeriesPageStoryBlock, TopicHeadlineFigureBlock
from cms.topics.forms import TopicPageAdminForm
from cms.topics.utils import format_time_series_as_document_list
from cms.topics.viewsets import (
    FeaturedSeriesPageChooserWidget,
    HighlightedArticlePageChooserWidget,
    HighlightedMethodologyPageChooserWidget,
)

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel

    from cms.users.models import User

MAX_ITEMS_PER_SECTION = 3


class TopicPageRelatedArticle(Orderable):
    parent = ParentalKey("TopicPage", on_delete=models.CASCADE, related_name="related_articles")
    page = models.ForeignKey[Page](
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
        help_text="Select an internal Wagtail page. If you want to link to an external page, use the fields below.",
    )
    external_url: models.URLField = models.URLField(
        blank=True,
        verbose_name="URL",
        help_text="URL of the external page. Leave blank if you selected an internal page.",
    )
    title: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Populate when adding an external link. "
            "When choosing a page, you can leave it blank to use the page’s own title."
        ),
    )

    panels: ClassVar[list["Panel"]] = [
        MultiFieldPanel(
            [
                FieldPanel(
                    "page",
                    widget=HighlightedArticlePageChooserWidget(linked_fields={"topic_page_id": "#id_topic_page_id"}),
                ),
            ],
            heading="Internal Link",
        ),
        MultiFieldPanel(
            [
                FieldPanel("external_url"),
                FieldPanel("title"),
            ],
            heading="External Link",
        ),
    ]

    def clean(self) -> None:
        super().clean()
        if self.page_id and self.external_url:
            raise ValidationError("Please select either an internal page or provide an external URL, not both.")
        if not self.page_id and not self.external_url:
            raise ValidationError("You must select an internal page or provide an external URL.")
        if self.external_url and not self.title:
            raise ValidationError({"title": "This field is required when providing an external URL."})


class TopicPageRelatedMethodology(Orderable):
    parent = ParentalKey("TopicPage", on_delete=models.CASCADE, related_name="related_methodologies")
    page = models.ForeignKey[Page](
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels: ClassVar[list[FieldPanel]] = [
        FieldPanel(
            "page", widget=HighlightedMethodologyPageChooserWidget(linked_fields={"topic_page_id": "#id_topic_page_id"})
        )
    ]


class TopicPagePermissionTester(PagePermissionTester):
    def can_add_subpage(self) -> bool:
        """Overrides the core can_add_subpage to consider max_count_per_parent.

        TODO: remove when https://github.com/wagtail/wagtail/issues/13286 is fixed
        """
        if not self.user.is_active:
            return False
        if (specific_class := self.page.specific_class) is None:
            return False
        creatable_subpage_models = [
            page_model
            for page_model in specific_class.creatable_subpage_models()
            if page_model.can_create_at(self.page)
        ]
        if specific_class is None or not creatable_subpage_models:
            return False
        return self.user.is_superuser or ("add" in self.permissions)


class TopicPage(BundledPageMixin, ExclusiveTaxonomyMixin, BasePage):  # type: ignore[django-manager-missing]
    """The Topic page model."""

    base_form_class = TopicPageAdminForm
    template = "templates/pages/topic_page.html"
    parent_page_types: ClassVar[list[str]] = ["home.HomePage"]
    subpage_types: ClassVar[list[str]] = ["articles.ArticlesIndexPage", "methodology.MethodologyIndexPage"]
    page_description = "A specific topic page. e.g. 'Public sector finance' or 'Inflation and price indices'."
    label = _("Topic")  # type: ignore[assignment]

    summary = RichTextField(features=settings.RICH_TEXT_BASIC)
    featured_series = models.ForeignKey(
        "articles.ArticleSeriesPage",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="featured_on_topic",
    )
    explore_more = StreamField(ExploreMoreStoryBlock(), blank=True)

    headline_figures = StreamField(
        [("figure", TopicHeadlineFigureBlock())],
        blank=True,
        max_num=6,
        help_text="Optional. If populating, it needs at least two headline figures.",
    )

    datasets = StreamField(DatasetStoryBlock(), blank=True, default=list, max_num=MAX_ITEMS_PER_SECTION)
    time_series = StreamField(TimeSeriesPageStoryBlock(), blank=True, default=list, max_num=MAX_ITEMS_PER_SECTION)

    content_panels: ClassVar[list["Panel"]] = [
        *BundledPageMixin.panels,
        *BasePage.content_panels,
        FieldPanel("summary", required_on_save=True),
        FieldPanel("headline_figures"),
        FieldPanel(
            "featured_series",
            heading="Featured",
            widget=FeaturedSeriesPageChooserWidget(linked_fields={"topic_page_id": "#id_topic_page_id"}),
        ),
        InlinePanel(
            "related_articles",
            heading="Highlighted articles",
            help_text=(
                f"Choose up to {MAX_ITEMS_PER_SECTION} articles to highlight. "
                "The 'Related articles' section will be topped up automatically."
            ),
            max_num=MAX_ITEMS_PER_SECTION,
        ),
        FieldPanel(
            "datasets",
            heading="Datasets",
            help_text=f"Select up to {MAX_ITEMS_PER_SECTION} datasets related to this topic.",
            icon="doc-full",
        ),
        FieldPanel(
            "time_series",
            help_text=f"Add up to {MAX_ITEMS_PER_SECTION} time series pages related to this topic.",
            icon="chart-line",
        ),
        InlinePanel(
            "related_methodologies",
            heading="Highlighted methods and quality information",
            help_text=(
                f"Choose up to {MAX_ITEMS_PER_SECTION} methodologies to highlight. "
                "The 'Methods and quality information' section will be topped up automatically."
            ),
            max_num=MAX_ITEMS_PER_SECTION,
        ),
        FieldPanel("explore_more", heading="Explore more"),
    ]

    search_fields: ClassVar[list[index.BaseField]] = [*BasePage.search_fields, index.SearchField("summary")]

    _analytics_content_type: ClassVar[str] = "topics"

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Additional context for the template."""
        context: dict = super().get_context(request, *args, **kwargs)
        context["table_of_contents"] = self.table_of_contents
        context["featured_item"] = kwargs.get("featured_item", self.latest_article_in_featured_series)
        context["formatted_articles"] = get_formatted_pages_list(self.processed_articles, request=request)
        context["formatted_methodologies"] = get_formatted_pages_list(self.processed_methodologies, request=request)
        context["search_page_urls"] = self.get_search_page_urls()
        return context

    @cached_property
    def latest_article_in_featured_series(self) -> StatisticalArticlePage | None:
        """Returns the latest article in the featured series."""
        if self.featured_series:
            article: StatisticalArticlePage = (
                StatisticalArticlePage.objects.child_of(self.featured_series)
                .live()
                .public()
                .order_by("-release_date")
                .first()
            )
            return article
        return None

    @cached_property
    def processed_articles(self) -> list[dict]:
        """Returns a list of dictionaries representing related articles.
        Each dict has 'internal_page' pointing to a Page (or None for external) and optional 'title'.
        Manually added articles (both internal and external) are prioritised.
        """
        manual_articles = []
        highlighted_page_pks = []

        for related in self.related_articles.select_related("page").all():
            if not related.page:
                if related.external_url:
                    manual_articles.append(
                        {
                            "url": related.external_url,
                            "title": related.title,
                            "description": "",
                            "is_external": True,
                        }
                    )
                continue

            page = related.page.specific_deferred  # type: ignore[attr-defined]

            if not page.live or page.get_view_restrictions().exists():
                continue

            article_dict = {"internal_page": page}
            if related.title:
                article_dict["title"] = related.title

            manual_articles.append(article_dict)
            highlighted_page_pks.append(page.pk)

        num_manual_articles = len(manual_articles)
        if num_manual_articles >= MAX_ITEMS_PER_SECTION:
            return manual_articles[:MAX_ITEMS_PER_SECTION]

        # Find latest article that is a descendant of a given article series page
        newest_qs = (
            StatisticalArticlePage.objects.live()
            .public()
            .filter(path__startswith=OuterRef("path"), depth__gte=OuterRef("depth"))
            .order_by("-release_date")
        )

        # Get latest article per series
        latest_by_series = (
            ArticleSeriesPage.objects.descendant_of(self)
            .annotate(latest_child_page=Subquery(newest_qs.values("pk")[:1]))
            .values_list("latest_child_page", flat=True)
        )

        remaining_slots = MAX_ITEMS_PER_SECTION - num_manual_articles

        # Get the latest articles under this topic page (topic page -> articles index -> article series page ->
        # latest stats article page), excluding those already highlighted
        latest_articles = list(
            StatisticalArticlePage.objects.filter(pk__in=latest_by_series)
            .exclude(pk__in=highlighted_page_pks)
            .live()
            .public()
            .defer_streamfields()
            .order_by("-release_date")
        )

        # Exclude those that are descendants of this topic page
        descendant_series_pks = set(ArticleSeriesPage.objects.descendant_of(self).values_list("pk", flat=True))

        # Get all other article series across the CMS that are tagged with this topic of this topic page
        all_article_series = (
            ArticleSeriesPage.objects.live()
            .public()
            .filter(topics__topic_id=self.topic_id)
            .exclude(pk__in=descendant_series_pks)
        )

        # Get latest article per series
        all_article_latest_by_series = all_article_series.annotate(
            latest_child_page=Subquery(newest_qs.values("pk")[:1])
        ).values_list("latest_child_page", flat=True)

        # Get the latest articles, excluding those already highlighted
        all_latest_articles = list(
            StatisticalArticlePage.objects.filter(pk__in=all_article_latest_by_series)
            .filter(locale=self.locale)  # Ensure articles are in the same locale as the topic page
            .exclude(pk__in=highlighted_page_pks)
            .live()
            .public()
            .defer_streamfields()
            .order_by("-release_date")
        )

        # Combine articles under this topic page and across the CMS, then order by release_date descending
        combined_articles = latest_articles + all_latest_articles
        combined_articles.sort(key=lambda page: page.release_date, reverse=True)

        # Convert to dict format
        auto_articles = [{"internal_page": page} for page in combined_articles[:remaining_slots]]

        return manual_articles + auto_articles

    @cached_property
    def processed_methodologies(self) -> list[dict]:
        """Returns a list of dictionaries representing methodologies relevant for this topic.
        Each dict has 'internal_page' pointing to a MethodologyPage.
        TODO: extend when Taxonomy is in.
        """
        # check if any methodologies were highlighted. if so, fetch in the order they were added.
        highlighted_page_pks = tuple(
            page_id for page_id in self.related_methodologies.values_list("page_id", flat=True)
        )
        highlighted_pages = list(
            order_by_pk_position(
                MethodologyPage.objects.live().public().defer_streamfields(),
                pks=highlighted_page_pks,
                exclude_non_matches=True,
            )
        )

        num_highlighted_pages = len(highlighted_pages)
        if num_highlighted_pages >= MAX_ITEMS_PER_SECTION:
            return [{"internal_page": page} for page in highlighted_pages]

        remaining_slots = MAX_ITEMS_PER_SECTION - num_highlighted_pages

        # Methodology pages under this topic page (descendants)/ (methodology index -> methodology page)
        # that are not already highlighted
        under_topic_page_methodology_pages = list(
            MethodologyPage.objects.descendant_of(self)
            .exclude(pk__in=highlighted_page_pks)
            .live()
            .public()
            .order_by("-last_revised_date")
        )

        # Methodology pages across the CMS tagged with this topic as the current topic page,
        # but not descendants of this topic page and not already highlighted
        descendant_methodology_pks = set(MethodologyPage.objects.descendant_of(self).values_list("pk", flat=True))
        across_cms_methodology_pages = list(
            MethodologyPage.objects.live()
            .filter(locale=self.locale)  # Ensure articles are in the same locale as the topic page
            .public()
            .filter(topics__topic_id=self.topic_id)
            .exclude(pk__in=descendant_methodology_pks)
            .exclude(pk__in=highlighted_page_pks)
            .order_by("-last_revised_date")
        )

        # Combine and sort by last_revised_date
        combined_auto_pages = under_topic_page_methodology_pages + across_cms_methodology_pages
        combined_auto_pages.sort(key=lambda page: page.last_revised_date, reverse=True)

        # Only fill up to the remaining slots
        auto_methodologies = [{"internal_page": page} for page in combined_auto_pages[:remaining_slots]]

        return [{"internal_page": page} for page in highlighted_pages] + auto_methodologies

    @cached_property
    def table_of_contents(self) -> list[dict[str, str | object]]:
        """Table of contents formatted to Design System specs."""
        items = []
        if self.latest_article_in_featured_series:
            items += [{"url": "#featured", "text": _("Featured")}]
        if self.processed_articles:  # pylint: disable=not-an-iterable,useless-suppression
            items += [{"url": "#related-articles", "text": _("Related articles")}]
        if self.processed_methodologies:
            items += [{"url": "#related-methods", "text": _("Methods and quality information")}]
        if self.explore_more:
            items += [{"url": "#explore-more", "text": _("Explore more")}]
        if self.dataset_document_list:
            items += [{"url": "#data", "text": _("Data")}]
        if self.time_series_document_list:
            items += [{"url": "#time-series", "text": _("Time series")}]
        add_table_of_contents_gtm_attributes(items)
        return items

    @cached_property
    def dataset_document_list(self) -> list[dict[str, Any]]:
        return format_datasets_as_document_list(self.datasets)

    @cached_property
    def time_series_document_list(self) -> list[dict[str, Any]]:
        return format_time_series_as_document_list(self.time_series)

    def clean(self) -> None:
        super().clean()

        # Check if headline_figures has 1 item (we can't use min_num because we allow 0)
        if self.headline_figures:
            if len(self.headline_figures) == 1:
                raise ValidationError({"headline_figures": "If you add headline figures, please add at least 2."})

            figure_ids = [figure.value["figure_id"] for figure in self.headline_figures]  # pylint: disable=not-an-iterable
            if len(figure_ids) != len(set(figure_ids)):
                raise ValidationError({"headline_figures": "Duplicate headline figures are not allowed."})

    def permissions_for_user(self, user: "User") -> PagePermissionTester:
        """Overrides the core permissions_for_user to use our permission tester.

        TopicPagePermissionTester.can_add_subpage() takes into account max_count / max_count_per_parent.
        TODO: replaces when https://github.com/wagtail/wagtail/issues/13286 is fixed.
        """
        return TopicPagePermissionTester(user, self)

    def get_search_page_urls(self) -> dict[str, str] | None:
        """Returns a dictionary of links to search pages related to the taxonomy topic,
        or None if the topic or base ONS URL is missing.

        Supported keys:
            - 'related_articles'
            - 'related_methodologies'
            - 'related_data'
            - 'related_time_series'

        Note:
            'related_articles' and 'related_methodologies' are only included
            if there exist live pages tagged by the same topic as the topic page.

        """
        if not (topic := self.topic):
            return None

        links: dict[str, str] = {}

        if self.processed_articles:
            links["related_articles"] = f"{settings.ONS_WEBSITE_BASE_URL}/{topic.slug_path}/publications"

        if self.processed_methodologies:
            links["related_methodologies"] = (
                f"{settings.ONS_WEBSITE_BASE_URL}/{topic.slug_path}/topicspecificmethodology"
            )

        if self.datasets:
            links["related_data"] = f"{settings.ONS_WEBSITE_BASE_URL}/{topic.slug_path}/datalist?filter=datasets"

        if self.time_series:
            links["related_time_series"] = f"{settings.ONS_WEBSITE_BASE_URL}/timeseriestool?topic={topic.slug_path}"

        return links
