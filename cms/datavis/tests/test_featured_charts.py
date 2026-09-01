from django.test import SimpleTestCase, override_settings
from wagtail.blocks import StreamValue

from cms.datavis.blocks.featured_charts import FeaturedChartBlock, FeaturedIframeBlock


@override_settings(
    IFRAME_VISUALISATION_ALLOWED_DOMAINS=["example.com"],
    IFRAME_VISUALISATION_PATH_PREFIXES=["/visualisations"],
)
class FeaturedChartBlockTestCase(SimpleTestCase):
    def setUp(self):
        self.block = FeaturedChartBlock()
        self.iframe_data = {
            "title": "",
            "accessible_label": "Bar chart of GDP per region",
            "audio_description": "GDP is highest in London and lowest in the North East.",
            "iframe_source_url": "/visualisations/dvc/123",
        }

    def test_all_featured_chart_types_are_available(self):
        self.assertEqual(
            list(self.block.child_blocks),
            [
                "line_chart",
                "bar_column_chart",
                "bar_column_confidence_interval_chart",
                "scatter_plot",
                "area_chart",
                "iframe",
            ],
        )
        self.assertEqual(self.block.child_blocks["iframe"].label, "Iframe Visualisation")

    def test_iframe_has_the_fields_supported_by_featured_charts(self):
        iframe_block = self.block.child_blocks["iframe"]

        self.assertIsInstance(iframe_block, FeaturedIframeBlock)
        self.assertEqual(
            list(iframe_block.child_blocks),
            ["title", "accessible_label", "audio_description", "iframe_source_url"],
        )
        self.assertFalse(iframe_block.child_blocks["title"].required)
        self.assertEqual(iframe_block.child_blocks["title"].label, "Featured chart title")
        self.assertIn("should not duplicate the article title", iframe_block.child_blocks["title"].field.help_text)
        self.assertTrue(iframe_block.child_blocks["accessible_label"].required)
        self.assertTrue(iframe_block.child_blocks["audio_description"].required)
        self.assertTrue(iframe_block.child_blocks["iframe_source_url"].required)

    def test_iframe_data_is_valid(self):
        iframe_block = self.block.child_blocks["iframe"]
        value = iframe_block.to_python(self.iframe_data)

        self.assertIsInstance(value, dict)
        iframe_block.clean(value)

    def test_iframe_is_detected_for_content_scripts(self):
        value = StreamValue(self.block, [("iframe", self.iframe_data)])

        self.assertTrue(self.block.has_iframe_visualisations(value))

    def test_non_iframe_featured_chart_is_not_detected_for_content_scripts(self):
        value = StreamValue(
            self.block,
            [
                (
                    "line_chart",
                    {
                        "title": "Test chart",
                        "audio_description": "A line chart.",
                        "table": {"table_data": '{"data": [["", "Series"], ["2025", "1"]]}'},
                        "theme": "primary",
                        "show_legend": True,
                        "show_markers": False,
                        "x_axis": {"title": ""},
                        "y_axis": {"title": ""},
                    },
                )
            ],
        )

        self.assertFalse(self.block.has_iframe_visualisations(value))

    def test_iframe_renders_with_figure_and_accessibility_configuration(self):
        iframe_block = self.block.child_blocks["iframe"]
        rendered = iframe_block.render(self.iframe_data, context={"block_id": "featured-iframe"})

        self.assertIn('id="featured-iframe"', rendered)
        self.assertIn('data-url="/visualisations/dvc/123"', rendered)
        self.assertIn('data-title="Bar chart of GDP per region"', rendered)
        self.assertIn('title="Bar chart of GDP per region"', rendered)
