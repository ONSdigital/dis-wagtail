import copy
import hashlib
from typing import TYPE_CHECKING, ClassVar, Optional

from django.contrib.admin.utils import quote, unquote
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import View
from wagtail.admin.ui.tables import Column, TitleColumn
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView, ChosenResponseMixin, ChosenViewMixin
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.coreutils import resolve_model_string

from cms.articles.models import ArticleSeriesPage

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.query import PageQuerySet


__all__ = ["SeriesWithHeadlineFiguresPageChooserViewSet", "series_with_headline_figures_chooser_viewset"]


def get_signature(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf8")).hexdigest()


class SpecialTitleColumn(TitleColumn):
    def get_link_url(self, instance, parent_context):
        """Extends the core chooser title column to pass on the headline figure id to the ChosenView."""
        url = super().get_link_url(instance, parent_context)
        figure_id = instance.headline_figure["figure_id"]
        separator = "&" if "?" in url else "?"
        params = {"figure_id": figure_id, "sig": get_signature(f"{quote(instance.pk)} - {figure_id!s}")}
        url += f"{separator}{urlencode(params)}"
        return url


class HeadlineFigureColumn(Column):
    def __init__(
        self,
        name,
        key,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.key = key

    def get_cell_context_data(self, instance, parent_context):
        context = super().get_cell_context_data(instance, parent_context)
        value = self.get_value(instance)
        context["value"] = value.get(self.key, "")
        return context


class SeriesWithHeadlineFiguresChooserMixin:
    model_class: ArticleSeriesPage

    def get_queryset(self) -> "PageQuerySet[ArticleSeriesPage]":
        topic_page_id = self.request.GET.get("topic_page_id")
        if not topic_page_id:
            return ArticleSeriesPage.objects.none()

        series_pages = ArticleSeriesPage.objects.all().only("path", "depth", "title", "pk").order_by("path")

        # using this rather than inline import to placate pyright complaining about cyclic imports
        topic_page_model = resolve_model_string("topics.TopicPage")
        try:
            series_pages = series_pages.child_of(topic_page_model.objects.get(pk=topic_page_id))
        except topic_page_model.DoesNotExist:
            series_pages = series_pages.none()

        return series_pages

    def get_object_list(self, objects: Optional["PageQuerySet[ArticleSeriesPage]"] = None) -> "list[ArticleSeriesPage]":
        if objects is None:
            objects = self.get_queryset()

        filtered_series = []
        for series_page in objects:
            latest_article = series_page.get_latest()
            if latest_article and latest_article.headline_figures.raw_data:
                for figure in latest_article.headline_figures[0].value:
                    page = copy.deepcopy(series_page)
                    page.headline_figure = dict(figure)
                    filtered_series.append(page)

        return filtered_series

    def get_results_page(self, request: "HttpRequest") -> "list[ArticleSeriesPage]":
        """Overrides the parent to apply the filtering on the queryset.

        Our get_object_list() returns a list of pages with duplicates (depending on the headline figures count),
        rather than a queryset as expected by filter_object_list().
        """
        objects = self.get_queryset()
        objects = self.filter_object_list(objects)
        objects = self.get_object_list(objects=objects)

        paginator = Paginator(objects, per_page=self.per_page)
        try:
            return paginator.page(request.GET.get("p", 1))
        except InvalidPage as e:
            raise Http404 from e

    @property
    def title_column(self) -> SpecialTitleColumn:
        """Mirrors the base title_column, just instantiates our TitleColumn subclass."""
        return SpecialTitleColumn(
            "title",
            label=_("Title"),
            accessor=str,
            get_url=(
                lambda obj: self.append_preserved_url_parameters(reverse(self.chosen_url_name, args=(quote(obj.pk),)))
            ),
            link_attrs={"data-chooser-modal-choice": True},
        )

    @property
    def columns(self) -> list["Column"]:
        return [
            self.title_column,  # type: ignore[attr-defined]
            HeadlineFigureColumn("figure_id", "figure_id", label=_("Figure ID"), accessor="headline_figure"),
            HeadlineFigureColumn("figure_title", "title", label=_("Figuire title"), accessor="headline_figure"),
            HeadlineFigureColumn("figure", "figure", label=_("Figure"), accessor="headline_figure"),
            HeadlineFigureColumn(
                "figure_text", "supporting_text", label=_("Supporting text"), accessor="headline_figure"
            ),
        ]


class SeriesWithHeadlineFiguresChooseView(SeriesWithHeadlineFiguresChooserMixin, ChooseView): ...


class SeriesWithHeadlineFiguresChooseResultsView(SeriesWithHeadlineFiguresChooserMixin, ChooseResultsView): ...


class SeriesWithHeadlineFiguresChosenResponseMixin(ChosenResponseMixin):
    def get_chosen_response_data(self, item):
        response_data = super().get_chosen_response_data(item)
        response_data["figure_id"] = item._figure_id  # pylint: disable=protected-access

        return response_data


class SeriesWithHeadlineFiguresChosenViewMixin(ChosenViewMixin):
    def get(self, request, pk):
        try:
            item = self.get_object(unquote(pk))
        except ObjectDoesNotExist as e:
            raise Http404 from e

        # check that the passed figure_id is correct (in that it was passed from the chooser and not tampered with)
        figure_id = request.GET.get("figure_id", "")
        signature = request.GET.get("sig", "")

        if signature != get_signature(f"{quote(item.pk)} - {figure_id!s}"):
            raise Http404

        item._figure_id = figure_id  # pylint: disable=protected-access

        return self.get_chosen_response(item)


class SeriesWithHeadlineChosenView(
    SeriesWithHeadlineFiguresChosenViewMixin, SeriesWithHeadlineFiguresChosenResponseMixin, View
):
    pass


class SeriesWithHeadlineFiguresPageChooserViewSet(ChooserViewSet):
    model = ArticleSeriesPage
    choose_view_class = SeriesWithHeadlineFiguresChooseView
    choose_results_view_class = SeriesWithHeadlineFiguresChooseResultsView
    chosen_view_class = SeriesWithHeadlineChosenView
    register_widget = False
    choose_one_text = _("Choose Article Series page")
    choose_another_text = _("Choose another Article Series page")
    edit_item_text = _("Edit Article Series page")
    preserve_url_parameters: ClassVar[list[str]] = ["multiple", "topic_page_id"]


series_with_headline_figures_chooser_viewset = SeriesWithHeadlineFiguresPageChooserViewSet(
    "topic_series_with_headline_figures_chooser"
)
