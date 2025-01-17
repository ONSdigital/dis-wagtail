from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models
from django.forms import Media
from django.utils.functional import cached_property, classproperty
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import (
    FieldPanel,
    FieldRowPanel,
    InlinePanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)

from cms.datavis.constants import (
    HIGHCHARTS_THEMES,
    HighchartsTheme,
    LegendPosition,
)
from cms.datavis.fields import NonStrippingCharField

from .base import Visualisation

if TYPE_CHECKING:
    from wagtail.admin.panels import Panel

__all__ = ["LineChart", "BarChart", "ColumnChart"]


class Chart(Visualisation):
    supports_stacked_layout: ClassVar[bool] = False

    show_legend = models.BooleanField(verbose_name=_("show legend?"), default=False)
    legend_position = models.CharField(
        verbose_name=_("label position"),
        max_length=6,
        choices=LegendPosition.choices,
        default=LegendPosition.TOP,
    )
    show_value_labels = models.BooleanField(verbose_name=_("show value labels?"), default=False)
    theme = models.CharField(
        verbose_name=_("theme"),
        max_length=10,
        choices=HighchartsTheme.choices,
        default=HighchartsTheme.PRIMARY,
    )
    use_stacked_layout = models.BooleanField(verbose_name=_("use stacked layout?"), default=False)

    x_label = models.CharField(verbose_name=_("label"), max_length=255, blank=True)
    x_max = models.FloatField(verbose_name=_("scale cap (max)"), blank=True, null=True)
    x_min = models.FloatField(verbose_name=_("scale cap (min)"), blank=True, null=True)
    x_reversed = models.BooleanField(verbose_name=_("reverse axis?"), default=False)
    x_tick_interval = models.FloatField(verbose_name=_("tick interval"), blank=True, null=True)

    y_label = models.CharField(verbose_name=_("label"), max_length=255, blank=True)
    y_max = models.FloatField(verbose_name=_("scale cap (max)"), blank=True, null=True)
    y_min = models.FloatField(verbose_name=_("scale cap (min)"), blank=True, null=True)
    y_value_suffix = NonStrippingCharField(verbose_name=_("value suffix (optional)"), max_length=30, blank=True)
    y_tooltip_suffix = NonStrippingCharField(
        verbose_name=_("tooltip value suffix (optional)"), max_length=30, blank=True
    )
    y_reversed = models.BooleanField(verbose_name=_("reverse axis?"), default=False)
    y_tick_interval = models.FloatField(verbose_name=_("tick interval"), blank=True, null=True)

    @cached_property
    def media(self) -> Media:
        return Media(
            js=[
                "https://code.highcharts.com/highcharts.js",
                "https://code.highcharts.com/modules/data.js",
                "https://code.highcharts.com/modules/exporting.js",
                "https://code.highcharts.com/modules/export-data.js",
                "https://code.highcharts.com/modules/accessibility.js",
            ]
        )

    def get_context(self, request, **kwargs) -> dict[str, Any]:
        config = self.get_component_config(self.primary_data_source.headers, self.primary_data_source.rows)
        return super().get_context(request, config=config, **kwargs)

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
        MultiFieldPanel(
            heading=_("Legend"),
            children=[
                FieldPanel("show_legend"),
                FieldPanel("legend_position"),
            ],
        ),
    ]

    advanced_panels: ClassVar[Sequence["Panel"]] = [
        InlinePanel("annotations", heading=_("Annotations")),
        InlinePanel("additional_data_sources", heading=_("Additional data")),
    ]

    @property
    def highcharts_chart_type(self):
        raise NotImplementedError

    @classmethod
    def get_general_panels(cls):
        general_panels = list(cls.general_panels)
        if cls.supports_stacked_layout:
            general_panels.append(FieldPanel("use_stacked_layout"))
        return general_panels

    @classproperty
    def edit_handler(cls):  # pylint: disable=no-self-argument
        return TabbedInterface(
            [
                ObjectList(cls.get_general_panels(), heading=_("General")),
                ObjectList(cls.x_axis_panels, heading=_("X Axis")),
                ObjectList(cls.y_axis_panels, heading=_("Y Axis")),
                ObjectList(cls.style_panels, heading=_("Style")),
                ObjectList(cls.advanced_panels, heading=_("Advanced")),
            ]
        )

    def get_component_config(self, headers: Sequence[str], rows: Sequence[list[str | int | float]]) -> dict[str, Any]:
        config = {
            "chart": {
                "type": self.highcharts_chart_type,
            },
            "title": {"text": None},
            "colors": HIGHCHARTS_THEMES[self.theme],
            "legend": {
                "align": "left",
                "enabled": self.show_legend,
                "verticalAlign": self.legend_position,
            },
            "xAxis": self.get_x_axis_config(headers, rows),
            "yAxis": self.get_y_axis_config(headers, rows),
            "plotOptions": self.get_plot_options(),
            "navigation": {
                "enabled": False,
            },
            "annotations": self.get_annotations_config(),
            "credits": {
                "enabled": False,
            },
        }
        config["series"] = self.get_series_data(headers, rows)
        return config

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
            config["title"] = (
                {
                    "enabled": True,
                    "text": label,
                },
            )
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

    def get_plot_options(self) -> dict[str, Any]:
        return {
            self.highcharts_chart_type: {
                "borderWidth": 0,
                "animation": False,
                "pointPadding": 0.1,
                "groupPadding": 0.1,
                "dataLabels": {
                    "enabled": self.show_value_labels,
                },
            }
        }

    def get_annotations_config(self) -> list[dict[str, Any]]:
        annotations = []
        annotation_group = {
            "draggable": "",
            "labelOptions": {
                "backgroundColor": "rgba(255,255,255,0.5)",
                "verticalAlign": "top",
            },
            "labels": [],
        }
        # TODO: It's likely we'll want to support a few different style
        # options for annotations, in which case, we'd split annotations
        # into multiple groups, each with a separate 'labelOptions' value
        # to control the styling.
        for annotation in self.annotations.all():
            annotation_group["labels"].append(
                {
                    "text": annotation.label,
                    "point": {
                        "x": float(annotation.x) if annotation.x.replace(".", "").isdigit() else annotation.x,
                        "y": float(annotation.y) if annotation.y.replace(".", "").isdigit() else annotation.y,
                        "xAxis": 0,
                        "yAxis": 0,
                    },
                }
            )
        annotations.append(annotation_group)
        return annotations

    def get_series_data(self, headers: Sequence[str], rows: Sequence[list[str | int | float]]) -> list[dict[str, Any]]:
        series = []
        for i, column in enumerate(headers[1:], start=1):
            item = {"name": column}
            if rows:
                item["data"] = [r[i] for r in rows]
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
                "markers": {
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

    class Meta:
        verbose_name = _("line chart")
        verbose_name_plural = _("line charts")
        proxy = True


class BarChart(Chart):
    highcharts_chart_type = "bar"
    template = "templates/datavis/bar_chart.html"
    supports_stacked_layout = True
    is_creatable = True

    class Meta:
        verbose_name = _("bar chart")
        verbose_name_plural = _("bar charts")
        proxy = True

    @classproperty
    def edit_handler(cls):  # pylint: disable=no-self-argument
        return TabbedInterface(
            [
                ObjectList(cls.get_general_panels(), heading=_("General")),
                # Deliberately swapping X and Y axis panels to match how Highcharts
                # switches the axis around for bar charts.
                ObjectList(cls.y_axis_panels, heading=_("X Axis")),
                ObjectList(cls.x_axis_panels, heading=_("Y Axis")),
                ObjectList(cls.style_panels, heading=_("Style")),
                ObjectList(cls.advanced_panels, heading=_("Advanced")),
            ]
        )


class ColumnChart(Chart):
    highcharts_chart_type = "column"
    template = "templates/datavis/column_chart.html"
    supports_stacked_layout = True
    is_creatable = True

    class Meta:
        verbose_name = _("column chart")
        verbose_name_plural = _("column charts")
        proxy = True


class AreaChart(Chart):
    highcharts_chart_type = "area"
    template = "templates/datavis/area_chart.html"
    supports_stacked_layout = True
    is_creatable = True

    class Meta:
        verbose_name = _("area chart")
        verbose_name_plural = _("area charts")
        proxy = True
