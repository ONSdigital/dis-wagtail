import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property, classproperty
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel
from wagtail.fields import StreamField
from wagtail.models import CollectionMember, Orderable, PreviewableMixin
from wagtail.permission_policies.collections import CollectionOwnershipPermissionPolicy
from wagtail.search import index

from cms.datavis.blocks import SimpleTableBlock
from cms.datavis.constants import MarkerStyle

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from django.utils.functional import Promise
    from wagtail.admin.panels import Panel

    from .base import Visualisation


__all__ = ["DataSource", "AdditionalDataSource"]


class DataSource(  # type: ignore[django-manager-missing]
    CollectionMember, PreviewableMixin, index.Indexed, models.Model
):
    title = models.CharField(verbose_name=_("title"), max_length=255)
    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        default=uuid.uuid4,
        db_index=True,
        unique=True,
        editable=False,
    )
    table = StreamField(
        [
            (
                "table",
                SimpleTableBlock(label=_("Table")),
            )
        ],
        verbose_name=_("data"),
        blank=True,
        null=True,
        max_num=1,
    )
    data = models.JSONField(verbose_name=_("data"), null=True, editable=False)
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True, db_index=True)
    column_count = models.IntegerField(verbose_name=_("cols"), default=0, editable=False)
    last_updated_at = models.DateTimeField(verbose_name=_("last updated at"), auto_now=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
    )
    created_by.wagtail_reference_index_ignore = True  # type: ignore[attr-defined]

    preview_modes: ClassVar[list[tuple[str, "str | Promise"]]] = [
        ("line-chart", _("Line chart")),
        ("bar-chart", _("Bar chart")),
        ("bar-chart-stacked", _("Bar chart (stacked)")),
        ("column-chart", _("Column chart")),
        ("column-chart-stacked", _("Column chart (stacked)")),
        ("area-chart", _("Area chart")),
        ("area-chart-stacked", _("Area chart (stacked)")),
    ]
    default_preview_mode = "line-chart"

    class Meta:
        verbose_name = _("data source")
        verbose_name_plural = _("data sources")

    search_fields: ClassVar[list[index.SearchField]] = [
        index.AutocompleteField("title"),
        index.SearchField("title", boost=5),
        index.SearchField("uuid"),
        index.FilterField("collection"),
        index.FilterField("uuid"),
        index.FilterField("column_count"),
        index.FilterField("created_at"),
        index.FilterField("last_updated_at"),
        index.FilterField("created_by"),
    ]

    def __str__(self) -> str:
        title: str = self.title
        return title

    @classproperty
    def permission_policy(cls) -> "CollectionOwnershipPermissionPolicy":  # pylint: disable=no-self-argument
        return CollectionOwnershipPermissionPolicy(cls, owner_field_name="created_by")

    @cached_property
    def headers(self) -> Sequence[str]:
        if not self.data:
            return []
        headers: list[str] = self.data[0]
        return headers

    @cached_property
    def rows(self) -> Sequence[Sequence[str | int | float]]:
        if not self.data:
            return []
        data: list[list[str | int | float]] = self.data
        return data[1:]

    def serve_preview(self, request: "HttpRequest", mode_name: str, **kwargs: Any) -> "HttpResponse":
        visualisation = self.get_preview_visualisation(mode_name)
        response: HttpResponse = visualisation.serve_preview(request, "default", **kwargs)
        return response

    def get_preview_visualisation(self, preview_mode: str) -> "Visualisation":
        from .charts import AreaChart, BarChart, ColumnChart, LineChart  # pylint: disable=import-outside-toplevel

        if preview_mode.startswith("bar-chart"):
            datavis_class = BarChart
        elif preview_mode.startswith("column-chart"):
            datavis_class = ColumnChart
        elif preview_mode.startswith("area-chart"):
            datavis_class = AreaChart
        else:
            datavis_class = LineChart
        description = _("Preview of {title}").format(title=self.title)
        return datavis_class(
            name=description,
            title=description,
            primary_data_source=self,
            use_stacked_layout=preview_mode.endswith("-stacked"),
        )


class AdditionalDataSource(Orderable):
    visualisation = ParentalKey(
        "datavis.Visualisation",
        on_delete=models.CASCADE,
        related_name="additional_data_sources",
    )
    data_source = models.ForeignKey(  # type: ignore[var-annotated]
        DataSource, on_delete=models.CASCADE, related_name="+"
    )
    display_as = models.CharField(  # type: ignore[var-annotated]
        verbose_name=_("display as"),
        default="line",
        choices=[
            ("area", _("Area")),
            ("column", _("Columns")),
            ("line", _("Line")),
        ],
        max_length=15,
    )
    marker_style = models.CharField(  # type: ignore[var-annotated]
        verbose_name=_("marker style"),
        default="",
        choices=MarkerStyle.choices,
        blank=True,
        max_length=15,
    )
    is_downloadable = models.BooleanField(  # type: ignore[var-annotated]
        verbose_name=_("include data source in downloadables?"),
        default=False,
    )

    panels: ClassVar[Sequence["Panel"]] = [
        FieldPanel("data_source"),
        FieldRowPanel(
            [
                FieldPanel("display_as"),
                FieldPanel("marker_style"),
                FieldPanel("is_downloadable"),
            ]
        ),
    ]

    def __str__(self) -> str:
        return f"{self.data_source} (as {self.get_display_as_display()})"
