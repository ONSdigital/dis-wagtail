from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Optional

from django.db import models
from django.forms import Media
from django.utils.functional import cached_property, classproperty
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel, ObjectList, TabbedInterface

from cms.core.fields import StreamField
from cms.datavis.blocks import AnnotationBlock
from cms.datavis.constants import HighchartsTheme, MarkerStyle
from cms.datavis.fields import NonStrippingCharField
from cms.datavis.utils import numberfy

from .base import Visualisation

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel


__all__ = ["AreaChart", "LineChart", "BarChart", "ColumnChart", "ScatterChart"]


class Chart(Visualisation):
    supports_stacked_layout: ClassVar[bool] = False
    supports_marker_style: ClassVar[bool] = False
    default_marker_style: ClassVar[MarkerStyle | Literal[""]] = ""

    show_legend = models.BooleanField(verbose_name=_("show legend?"), default=True)  # type: ignore[var-annotated]
    show_value_labels = models.BooleanField(  # type: ignore[var-annotated]
        verbose_name=_("show value labels?"), default=False
    )
    theme = models.CharField(  # type: ignore[var-annotated]
        verbose_name=_("theme"),
        max_length=10,
        choices=HighchartsTheme.choices,
        default=HighchartsTheme.PRIMARY,
    )
    marker_style = models.CharField(  # type: ignore[var-annotated]
        verbose_name=_("marker style"),
        default=MarkerStyle.CIRCLE,
        choices=MarkerStyle.choices,
        blank=True,
        max_length=15,
    )
    use_stacked_layout = models.BooleanField(  # type: ignore[var-annotated]
        verbose_name=_("use stacked layout?"), default=False
    )

    x_label = models.CharField(verbose_name=_("label"), max_length=255, blank=True)  # type: ignore[var-annotated]
    x_max = models.FloatField(verbose_name=_("scale cap (max)"), blank=True, null=True)  # type: ignore[var-annotated]
    x_min = models.FloatField(verbose_name=_("scale cap (min)"), blank=True, null=True)  # type: ignore[var-annotated]
    x_reversed = models.BooleanField(verbose_name=_("reverse axis?"), default=False)  # type: ignore[var-annotated]
    x_tick_interval = models.FloatField(  # type: ignore[var-annotated]
        verbose_name=_("tick interval"), blank=True, null=True
    )

    y_label = models.CharField(verbose_name=_("label"), max_length=255, blank=True)  # type: ignore[var-annotated]
    y_max = models.FloatField(verbose_name=_("scale cap (max)"), blank=True, null=True)  # type: ignore[var-annotated]
    y_min = models.FloatField(verbose_name=_("scale cap (min)"), blank=True, null=True)  # type: ignore[var-annotated]
    y_value_suffix = NonStrippingCharField(verbose_name=_("value suffix (optional)"), max_length=30, blank=True)
    y_tooltip_suffix = NonStrippingCharField(
        verbose_name=_("tooltip value suffix (optional)"), max_length=30, blank=True
    )
    y_reversed = models.BooleanField(verbose_name=_("reverse axis?"), default=False)  # type: ignore[var-annotated]
    y_tick_interval = models.FloatField(  # type: ignore[var-annotated]
        verbose_name=_("tick interval"), blank=True, null=True
    )
    annotations = StreamField(
        [("annotation", AnnotationBlock())],
        verbose_name=_("annotations"),
        blank=True,
        default=[],
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.pk and not self.marker_style:
            self.marker_style = self.default_marker_style

    @cached_property
    def media(self) -> Media:
        return Media(
            js=[
                "https://code.highcharts.com/highcharts.js",
                "https://code.highcharts.com/modules/data.js",
                "https://code.highcharts.com/modules/exporting.js",
                "https://code.highcharts.com/modules/export-data.js",
                "https://code.highcharts.com/modules/accessibility.js",
                "https://code.highcharts.com/modules/annotations.js",
            ]
        )

    def get_context(self, request: Optional["HttpRequest"] = None, **kwargs: Any) -> dict[str, Any]:
        config = self.get_component_config(self.primary_data_source.headers, self.primary_data_source.rows)
        annotations_values = self.get_annotations_values()
        return super().get_context(request, config=config, annotations_values=annotations_values, **kwargs)

    general_panels: ClassVar[Sequence["Panel"]] = [
        FieldPanel("name"),
        FieldPanel("primary_data_source"),
        MultiFieldPanel(
            heading="Descriptive text",
            children=[
                FieldPanel("title"),
                FieldPanel("subtitle"),
                FieldPanel("caption"),
            ],
        ),
    ]

    x_axis_panels: ClassVar[Sequence["Panel"]] = [
        FieldPanel("x_label"),
        FieldRowPanel(
            [
                FieldPanel("x_min"),
                FieldPanel("x_max"),
            ]
        ),
        FieldPanel("x_reversed"),
        FieldPanel("x_tick_interval"),
    ]

    y_axis_panels: ClassVar[Sequence["Panel"]] = [
        FieldPanel("y_label"),
        FieldPanel("y_value_suffix"),
        FieldPanel("y_tooltip_suffix"),
        FieldRowPanel(
            [
                FieldPanel("y_min"),
                FieldPanel("y_max"),
            ]
        ),
        FieldPanel("y_reversed"),
        FieldPanel("y_tick_interval"),
    ]

    style_panels: ClassVar[Sequence["Panel"]] = [
        FieldPanel("theme"),
        FieldPanel("show_value_labels"),
        FieldPanel("show_legend"),
    ]

    advanced_panels: ClassVar[Sequence["Panel"]] = [
        FieldPanel("annotations"),
        InlinePanel("additional_data_sources", heading=_("Additional data")),
    ]

    @property
    def highcharts_chart_type(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_general_panels(cls) -> list["Panel"]:
        general_panels = list(cls.general_panels)
        if cls.supports_stacked_layout:
            general_panels.append(FieldPanel("use_stacked_layout"))
        return general_panels

    @classmethod
    def get_style_panels(cls) -> list["Panel"]:
        style_panels = list(cls.style_panels)
        if cls.supports_marker_style:
            style_panels.insert(1, FieldPanel("marker_style"))
        return style_panels

    @classmethod
    def get_advanced_panels(cls) -> list["Panel"]:
        return list(cls.advanced_panels)

    @classmethod
    def get_x_axis_panels(cls) -> list["Panel"]:
        return list(cls.x_axis_panels)

    @classmethod
    def get_y_axis_panels(cls) -> list["Panel"]:
        return list(cls.y_axis_panels)

    @classproperty
    def edit_handler(cls) -> "Panel":  # pylint: disable=no-self-argument
        return TabbedInterface(
            [
                ObjectList(cls.get_general_panels(), heading=_("General")),
                ObjectList(cls.get_x_axis_panels(), heading=_("X Axis")),
                ObjectList(cls.get_y_axis_panels(), heading=_("Y Axis")),
                ObjectList(cls.get_style_panels(), heading=_("Style")),
                ObjectList(cls.get_advanced_panels(), heading=_("Advanced")),
            ]
        )

    def get_component_config(self, headers: Sequence[str], rows: Sequence[list[str | int | float]]) -> dict[str, Any]:
        return {
            "chart": {
                "type": self.highcharts_chart_type,
            },
            "legend": {
                "enabled": self.show_legend,
            },
            "xAxis": self.get_x_axis_config(headers, rows),
            "yAxis": self.get_y_axis_config(headers, rows),
            "series": self.get_series_data(headers, rows),
        }

    def get_x_axis_config(self, headers: Sequence[str], rows: Sequence[list[str | int | float]]) -> dict[str, Any]:
        config = {
            "type": "linear",
            "title": {
                "enabled": True,
                "text": self.x_label or headers[0],
            },
            "reversed": self.x_reversed,
            "categories": [r[0] for r in rows],
        }
        if self.x_tick_interval is not None:
            config["tickInterval"] = self.x_tick_interval
        if self.x_min is not None:
            config["min"] = self.x_min
        if self.x_max is not None:
            config["max"] = self.x_max
        return config

    def get_y_axis_config(
        self,
        headers: Sequence[str],
        rows: Sequence[list[str | int | float]],  # pylint: disable=unused-argument
    ) -> dict[str, Any]:
        config = {
            "reversed": self.y_reversed,
        }
        label = self.y_label or headers[1]
        if label:
            config["title"] = {
                "enabled": True,
                "text": label,
            }
        if self.y_tick_interval is not None:
            config["tickInterval"] = self.y_tick_interval
        if self.y_value_suffix:
            config["labels"] = {
                "format": "{value} " + self.y_value_suffix,
            }
        if self.y_min is not None:
            config["min"] = self.y_min
        if self.y_max is not None:
            config["max"] = self.y_max
        return config

    def get_annotations_values(self) -> list[dict[str, Any]]:
        annotation_values: list[dict[str, Any]] = []
        for item in self.annotations.raw_data:  # pylint: disable=no-member
            value = item["value"]
            annotation_values.append(
                {
                    "text": value["label"],
                    "xValue": numberfy(value["x_position"]),
                    "yValue": numberfy(value["y_position"]),
                }
            )
        return annotation_values

    def get_series_data(self, headers: Sequence[str], rows: Sequence[list[str | int | float]]) -> list[dict[str, Any]]:
        series = []
        for i, column in enumerate(headers[1:], start=1):
            item = {
                "name": column,
                "data": [r[i] for r in rows],
                "animation": False,
                "dataLabels": {
                    "enabled": self.show_value_labels,
                },
            }
            if self.supports_marker_style:
                item["marker"] = {
                    "enabled": bool(self.marker_style),
                    "symbol": self.marker_style or "undefined",
                }
            if self.y_tooltip_suffix:
                item["tooltip"] = {
                    "valueSuffix": self.y_tooltip_suffix,
                }
            if self.supports_stacked_layout and self.use_stacked_layout:
                item["stacking"] = "normal"

            series.append(item)
        for additional in self.additional_data_sources.all():
            item = {
                "type": additional.display_as,
                "name": additional.data_source.title,
                "data": additional.data_source.rows,
                "marker": {
                    "enabled": bool(additional.marker_style),
                    "symbol": additional.marker_style or "undefined",
                },
            }
            series.append(item)
        return series


class LineChart(Chart):
    highcharts_chart_type = "line"
    template = "templates/datavis/line_chart.html"
    is_creatable = True
    supports_marker_style = True

    class Meta:
        verbose_name = _("line chart")
        verbose_name_plural = _("line charts")
        proxy = True


class AreaChart(Chart):
    highcharts_chart_type = "area"
    template = "templates/datavis/area_chart.html"
    supports_stacked_layout = True
    supports_marker_style = True
    is_creatable = True

    class Meta:
        verbose_name = _("area chart")
        verbose_name_plural = _("area charts")
        proxy = True


class BarChart(Chart):
    highcharts_chart_type = "bar"
    template = "templates/datavis/bar_chart.html"
    supports_stacked_layout = True
    supports_marker_style = False
    is_creatable = True

    class Meta:
        verbose_name = _("bar chart")
        verbose_name_plural = _("bar charts")
        proxy = True

    @classmethod
    def get_x_axis_panels(cls) -> list["Panel"]:
        return list(cls.y_axis_panels)

    @classmethod
    def get_y_axis_panels(cls) -> list["Panel"]:
        return list(cls.x_axis_panels)


class ColumnChart(Chart):
    highcharts_chart_type = "column"
    template = "templates/datavis/column_chart.html"
    supports_stacked_layout = True
    supports_marker_style = False
    is_creatable = True

    class Meta:
        verbose_name = _("column chart")
        verbose_name_plural = _("column charts")
        proxy = True


class ScatterChart(Chart):
    highcharts_chart_type = "scatter"
    template = "templates/datavis/scatter_chart.html"
    supports_marker_style = True
    default_marker_style = MarkerStyle.CIRCLE
    is_creatable = True

    class Meta:
        verbose_name = _("statter chart")
        verbose_name_plural = _("statter charts")
        proxy = True
