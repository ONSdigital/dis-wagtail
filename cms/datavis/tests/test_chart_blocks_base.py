from typing import Any, ClassVar
from unittest.mock import Mock
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.test import SimpleTestCase, TestCase
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.data_downloads.utils import get_csv_download_filename
from cms.datavis.blocks.base import BaseChartBlock, BaseVisualisationBlock
from cms.datavis.blocks.charts import LineChartBlock
from cms.datavis.blocks.utils import get_approximate_file_size_in_kb
from cms.datavis.tests.factories import TableDataFactory


class BaseVisualisationBlockTestCase(SimpleTestCase, WagtailTestUtils):
    block_type: ClassVar[type[BaseVisualisationBlock]]
    raw_data: dict[str, Any]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block = cls.block_type()

    def setUp(self):
        super().setUp()
        self.raw_data = {
            "figure_number": "Figure 1",
            "title": "Test Chart",
            "subtitle": "Test Subtitle",
            "caption": "Test Caption",
            "audio_description": "Test Audio Description",
        }

    def get_value(self, raw_data: dict[str, Any] | None = None):
        if raw_data is None:
            raw_data = self.raw_data
        return self.block.to_python(raw_data)

    def _test_generic_properties(self):
        """Test attributes that are common to all chart blocks."""
        value = self.get_value()
        pairs = [
            # `value` dict key, expected value
            ("figure_number", "Figure 1"),
            ("title", "Test Chart"),
            ("subtitle", "Test Subtitle"),
            ("audio_description", "Test Audio Description"),
            ("caption", "Test Caption"),
        ]

        for key, expected in pairs:
            with self.subTest(key=key):
                self.assertEqual(expected, value[key])


class BaseChartBlockTestCase(BaseVisualisationBlockTestCase):
    block_type: ClassVar[type[BaseChartBlock]]

    def setUp(self):
        super().setUp()
        self.raw_data.update(
            {
                "table": TableDataFactory(),
                "theme": "primary",
                "show_legend": True,
                "show_data_labels": False,
                "use_stacked_layout": False,
                "show_markers": True,
                "x_axis": {
                    "title": "",
                    "min": None,
                    "max": None,
                    "tick_interval_mobile": None,
                    "tick_interval_desktop": None,
                },
                "y_axis": {
                    "title": "",
                    "min": None,
                    "max": None,
                    "tick_interval_mobile": None,
                    "tick_interval_desktop": None,
                    "value_suffix": "",
                    "tooltip_suffix": "",
                },
                "annotations": [{"type": "point", "value": {"label": "Peak", "x_position": 2, "y_position": 140}}],
            }
        )

    def get_component_config(self, raw_data: dict[str, Any] | None = None):
        value = self.get_value(raw_data)
        return self.block.get_component_config(value)

    def _test_generic_properties(self):
        """Test attributes that are common to all chart blocks."""
        value = self.get_value()
        pairs = [
            # `value` dict key, expected value
            ("figure_number", "Figure 1"),
            ("title", "Test Chart"),
            ("subtitle", "Test Subtitle"),
            ("audio_description", "Test Audio Description"),
            ("caption", "Test Caption"),
        ]
        if "theme" in self.block.child_blocks:
            pairs.append(("theme", self.raw_data["theme"]))
        for key, expected in pairs:
            with self.subTest(key=key):
                self.assertEqual(expected, value[key])

        with self.subTest("table"):
            # Test the table_data in the table object is the same.
            # We can't test the whole table object as it is a StructValue, and
            # contains other fields to do with SimpleTable configuration.
            self.assertEqual(self.raw_data["table"]["table_data"], value["table"]["table_data"])

    def _test_get_component_config(self):
        config = self.get_component_config()

        # Test basic structure
        self.assertIn("legend", config)
        self.assertIn("xAxis", config)
        self.assertIn("yAxis", config)
        self.assertIn("series", config)


class BuildChartDownloadUrlTests(SimpleTestCase):
    """Tests for BaseChartBlock._build_chart_download_url static method."""

    def test_builds_url_without_version(self):
        page = Mock()
        page.url = "/topics/economy/articles/gdp"
        url = BaseChartBlock._build_chart_download_url(page, "chart-123")  # pylint: disable=protected-access
        self.assertEqual(url, "/topics/economy/articles/gdp/download-chart/chart-123")

    def test_builds_url_with_superseded_version(self):
        page = Mock()
        page.url = "/topics/economy/articles/gdp"
        url = BaseChartBlock._build_chart_download_url(  # pylint: disable=protected-access
            page, "chart-456", superseded_version=2
        )
        self.assertEqual(url, "/topics/economy/articles/gdp/versions/2/download-chart/chart-456")

    def test_handles_trailing_slash_in_page_url(self):
        page = Mock()
        page.url = "/topics/economy/articles/gdp/"
        url = BaseChartBlock._build_chart_download_url(page, "chart-789")  # pylint: disable=protected-access
        # Should not have double slashes
        self.assertNotIn("//", url.replace("://", ""))
        self.assertEqual(url, "/topics/economy/articles/gdp/download-chart/chart-789")


class GetDownloadConfigTests(TestCase):
    """Tests for BaseChartBlock.get_download_config method."""

    def setUp(self):
        self.block = LineChartBlock()
        self.raw_data = {
            "title": "Test Chart Title That Is Quite Long Indeed",
            "subtitle": "Subtitle",
            "audio_description": "Description",
            "table": TableDataFactory(),
            "theme": "primary",
            "show_legend": True,
            "x_axis": {"title": ""},
            "y_axis": {"title": ""},
        }

    def test_download_config_without_context(self):
        """Without parent_context, only image download should be present."""
        value = self.block.to_python(self.raw_data)
        config = self.block.get_download_config(value)

        self.assertIn("title", config)
        self.assertIn("itemsList", config)
        self.assertEqual(len(config["itemsList"]), 1)
        self.assertIn("image", config["itemsList"][0]["text"])

    def test_download_config_with_context_includes_csv(self):
        """With parent_context and block_id, CSV download should be included."""
        value = self.block.to_python(self.raw_data)
        page = Mock()
        page.url = "/articles/test/"

        config = self.block.get_download_config(
            value,
            parent_context={"page": page},
            block_id="test-block-id",
            rows=[["a", "b"], ["1", "2"]],
        )

        self.assertEqual(len(config["itemsList"]), 2)
        csv_item = config["itemsList"][1]
        self.assertIn("CSV", csv_item["text"])
        self.assertIn("KB", csv_item["text"])  # Should include file size
        self.assertEqual(csv_item["url"], "/articles/test/download-chart/test-block-id")

    def test_download_config_with_superseded_version(self):
        """With superseded_version, CSV URL should include version path."""
        value = self.block.to_python(self.raw_data)
        page = Mock()
        page.url = "/articles/test/"

        config = self.block.get_download_config(
            value,
            parent_context={"page": page, "superseded_version": 1},
            block_id="test-block-id",
        )

        csv_item = config["itemsList"][1]
        self.assertEqual(csv_item["url"], "/articles/test/versions/1/download-chart/test-block-id")

    def test_download_config_in_preview_mode_uses_admin_url(self):
        """In preview mode, CSV URL should use the admin revision download URL."""
        value = self.block.to_python(self.raw_data)
        page = Mock()
        page.pk = 123
        page.url = "/articles/test/"
        page.latest_revision_id = 456
        request = Mock()
        request.is_preview = True
        request.resolver_match = None  # No revision_id in URL, so falls back to latest_revision_id

        config = self.block.get_download_config(
            value,
            parent_context={"page": page, "request": request},
            block_id="test-block-id",
        )

        csv_item = config["itemsList"][1]
        # Should use the admin URL for revision chart download
        self.assertEqual(csv_item["url"], "/admin/data-downloads/pages/123/revisions/456/download-chart/test-block-id/")

    def test_download_config_in_preview_mode_without_revision_uses_hash(self):
        """In preview mode without revision info, CSV URL should fall back to '#'."""
        value = self.block.to_python(self.raw_data)
        page = Mock(spec=["pk", "url"])  # No latest_revision_id
        page.pk = 123
        page.url = "/articles/test/"
        request = Mock()
        request.is_preview = True
        request.resolver_match = None

        config = self.block.get_download_config(
            value,
            parent_context={"page": page, "request": request},
            block_id="test-block-id",
        )

        csv_item = config["itemsList"][1]
        self.assertEqual(csv_item["url"], "#")

    def test_download_config_not_in_preview_mode_uses_real_url(self):
        """When not in preview mode, CSV URL should be the actual download URL."""
        value = self.block.to_python(self.raw_data)
        page = Mock()
        page.url = "/articles/test/"
        request = Mock()
        request.is_preview = False

        config = self.block.get_download_config(
            value,
            parent_context={"page": page, "request": request},
            block_id="test-block-id",
        )

        csv_item = config["itemsList"][1]
        self.assertEqual(csv_item["url"], "/articles/test/download-chart/test-block-id")

    def test_download_config_csv_download_data_attributes_in_config(self):
        """Verify expected CSV download link GTM data attributes are present in download config data."""
        page = StatisticalArticlePageFactory()
        value = self.block.to_python(self.raw_data)
        context = {
            "block_id": "test-block-id",
            "page": page,
            "request": get_dummy_request(),
        }

        rows = [["a", "b"], ["1", "2"]]

        config = self.block.get_download_config(
            value,
            parent_context=context,
            block_id="test-block-id",
            rows=rows,
        )

        # CSV item is at index 1 (image download is at index 0)
        csv_item = config["itemsList"][1]
        expected_url = f"{page.url.rstrip('/')}/download-chart/test-block-id"
        expected_file_size_with_unit = get_approximate_file_size_in_kb(rows)
        expected_file_size = str(len(bytes(str(rows), "utf-8")) / 1024)
        expected_link_text = f"Download CSV ({expected_file_size_with_unit})"

        expected_attributes = {
            "data-ga-event": "file-download",
            "data-ga-file-extension": "csv",
            "data-ga-file-name": get_csv_download_filename(title=self.raw_data.get("title"), fallback_stem="chart"),
            "data-ga-link-text": expected_link_text,
            "data-ga-link-url": urlparse(expected_url).path,
            "data-ga-link-domain": urlparse(expected_url).hostname,
            "data-ga-chart-title": self.raw_data.get("title"),
            "data-ga-chart-type": "line",
            "data-ga-file-size": expected_file_size,
        }

        self.assertEqual(csv_item["attributes"], expected_attributes)

    def test_download_config_csv_download_data_attributes_in_rendered_html(self):
        """Verify GTM data attributes are rendered correctly in the CSV download HTML."""
        page = StatisticalArticlePageFactory()
        page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart section",
                    "content": [{"type": "line_chart", "value": self.raw_data, "id": "test-block-id"}],
                },
            }
        ]
        value = self.block.to_python(self.raw_data)
        page.save_revision().publish()

        response = self.client.get(page.url)
        soup = BeautifulSoup(response.content, "html.parser")
        download_csv_link = soup.find("a", href=f"{page.url.rstrip('/')}/download-chart/test-block-id")
        download_csv_list_item = download_csv_link.find_parent(class_="ons-list__item")

        expected_file_size = len(bytes(str(value["table"].rows), "utf-8")) / 1024

        self.assertEqual(download_csv_list_item.get("data-ga-link-text"), download_csv_list_item.get_text(strip=True))
        self.assertEqual(download_csv_list_item.get("data-ga-event"), "file-download")
        self.assertEqual(download_csv_list_item.get("data-ga-file-extension"), "csv")
        self.assertEqual(
            download_csv_list_item.get("data-ga-file-name"),
            get_csv_download_filename(title=self.raw_data.get("title"), fallback_stem="chart"),
        )
        self.assertEqual(download_csv_list_item.get("data-ga-link-url"), urlparse(download_csv_link.get("href")).path)
        self.assertEqual(
            download_csv_list_item.get("data-ga-link-domain"), urlparse(download_csv_link.get("href")).hostname
        )
        self.assertEqual(download_csv_list_item.get("data-ga-chart-title"), self.raw_data.get("title"))
        self.assertEqual(download_csv_list_item.get("data-ga-chart-type"), "line")
        self.assertEqual(download_csv_list_item.get("data-ga-file-size"), str(expected_file_size))
