from wagtail.blocks import StreamBlock

from cms.datavis.blocks.charts import (
    AreaChartBlock,
    BarColumnChartBlock,
    BarColumnConfidenceIntervalChartBlock,
    LineChartBlock,
    ScatterPlotBlock,
)


class FeaturedLineChartBlock(LineChartBlock):
    """Featured chart variant of LineChartBlock with simplified fields."""

    # Override fields to remove unwanted options for featured charts
    subtitle = None
    caption = None
    # TODO: remove download configuration options


class FeaturedBarColumnChartBlock(BarColumnChartBlock):
    """Featured chart variant of BarColumnChartBlock with simplified fields."""

    # Override fields to remove unwanted options for featured charts
    subtitle = None
    caption = None
    # TODO: remove download configuration options


class FeaturedBarColumnConfidenceIntervalChartBlock(BarColumnConfidenceIntervalChartBlock):
    """Featured chart variant of BarColumnConfidenceIntervalChartBlock with simplified fields."""

    # Override fields to remove unwanted options for featured charts
    subtitle = None
    caption = None
    # TODO: remove download configuration options


class FeaturedScatterPlotBlock(ScatterPlotBlock):
    """Featured chart variant of ScatterPlotBlock with simplified fields."""

    # Override fields to remove unwanted options for featured charts
    subtitle = None
    caption = None
    # TODO: remove download configuration options


class FeaturedAreaChartBlock(AreaChartBlock):
    """Featured chart variant of AreaChartBlock with simplified fields."""

    # Override fields to remove unwanted options for featured charts
    subtitle = None
    caption = None
    # TODO: remove download configuration options


class FeaturedChartBlock(StreamBlock):
    line_chart = FeaturedLineChartBlock(label="Line Chart")
    bar_column_chart = FeaturedBarColumnChartBlock(label="Bar/Column Chart")
    bar_column_confidence_interval_chart = FeaturedBarColumnConfidenceIntervalChartBlock(
        label="Bar/Column Chart with Confidence Intervals"
    )
    scatter_plot = FeaturedScatterPlotBlock(label="Scatter Plot")
    area_chart = FeaturedAreaChartBlock(label="Area Chart")
    # TODO: enable iframe once supported by the Design System, see
    # https://github.com/ONSdigital/design-system/pull/3641
    # iframe = ONSEmbedBlock(label="Iframe Embed")
