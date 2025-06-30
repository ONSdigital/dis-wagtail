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
