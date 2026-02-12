# Block type names for chart blocks in SectionContentBlock
CHART_BLOCK_TYPES: frozenset[str] = frozenset(
    {
        "line_chart",
        "bar_column_chart",
        "bar_column_confidence_interval_chart",
        "scatter_plot",
        "area_chart",
    }
)

# Block type names for table blocks in SectionContentBlock
TABLE_BLOCK_TYPES: frozenset[str] = frozenset(
    {
        "table",
    }
)
