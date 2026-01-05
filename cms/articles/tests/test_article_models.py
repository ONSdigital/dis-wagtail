# pylint: disable=too-many-lines
import math
from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from wagtail.blocks import StreamValue
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from cms.articles.enums import SortingChoices
from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory
from cms.core.analytics_utils import format_date_for_gtm
from cms.core.tests.factories import ContactDetailsFactory
from cms.core.tests.utils import extract_datalayer_pushed_values
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset
from cms.datasets.tests.factories import DatasetFactory
from cms.datavis.constants import CHART_BLOCK_TYPES
from cms.datavis.tests.factories import TableDataFactory
from cms.topics.models import TopicPage


class StatisticalArticlePageTestCase(WagtailTestUtils, TestCase):
    def setUp(self):
        self.page = StatisticalArticlePageFactory(
            parent__title="PSF",
            title="November 2024",
            news_headline="",
            contact_details=None,
            show_cite_this_page=False,
        )

    def test_display_title(self):
        """Test display_title returns admin title when no news_headline."""
        self.assertEqual(self.page.display_title, self.page.get_admin_display_title())
        self.assertEqual(self.page.display_title, "PSF: November 2024")
        self.assertEqual(self.page.display_title, f"{self.page.get_parent().title}: {self.page.title}")

    def test_display_title_with_news_headline(self):
        """Test display_title returns news_headline when set."""
        self.page.news_headline = "Breaking News"
        self.assertEqual(self.page.display_title, "Breaking News")

    def test_table_of_contents_with_content(self):
        """Test table_of_contents with content blocks."""
        self.page.content = [
            {"type": "section", "value": {"title": "Test Section", "content": [{"type": "rich_text", "value": "text"}]}}
        ]

        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        self.assertEqual(toc[0]["url"], "#test-section")
        self.assertEqual(toc[0]["text"], "Test Section")

    def test_table_of_contents_with_cite_this_page(self):
        """Test table_of_contents includes cite this page when enabled."""
        self.page.show_cite_this_page = True

        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        self.assertEqual(toc[0]["url"], "#cite-this-page")
        self.assertEqual(toc[0]["text"], "Cite this article")

    def test_table_of_contents_with_contact_details(self):
        """Test table_of_contents includes contact details when present."""
        self.page.contact_details = ContactDetailsFactory()
        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 1)
        self.assertEqual(
            toc[0]["url"],
            "#contact-details",
        )
        self.assertEqual(toc[0]["text"], "Contact details")

    def test_table_of_contents_with_no_content(self):
        """Test table_of_contents returns empty list when no content."""
        self.page.content = []
        self.assertListEqual(self.page.table_of_contents, [])

    def test_table_of_contents_with_multiple_sections(self):
        """Test table_of_contents with multiple content sections."""
        self.page.content = [
            {"type": "section", "value": {"title": "Section 1", "content": [{"type": "rich_text", "value": "text"}]}},
            {"type": "section", "value": {"title": "Section 2", "content": [{"type": "rich_text", "value": "text"}]}},
        ]

        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 2)
        self.assertEqual(toc[0]["text"], "Section 1")
        self.assertEqual(toc[0]["url"], "#section-1")
        self.assertEqual(toc[1]["text"], "Section 2")
        self.assertEqual(toc[1]["url"], "#section-2")

    def test_table_of_contents_attributes(self):
        """Test table_of_contents returns correct attributes."""
        self.page.content = [
            {"type": "section", "value": {"title": "Section 1", "content": [{"type": "rich_text", "value": "text"}]}},
            {"type": "section", "value": {"title": "Section 2", "content": [{"type": "rich_text", "value": "text"}]}},
        ]
        self.page.show_cite_this_page = True
        self.page.contact_details = ContactDetailsFactory()

        toc = self.page.table_of_contents
        self.assertEqual(len(toc), 4)
        expected_attribute_labels = ["Section 1", "Section 2", "Cite this article", "Contact details"]
        for idx, toc_item in enumerate(toc):
            self.assertEqual(toc_item["attributes"]["data-ga-section-title"], expected_attribute_labels[idx])
            self.assertEqual(toc_item["attributes"]["data-ga-event"], "navigation-onpage")
            self.assertEqual(toc_item["attributes"]["data-ga-navigation-type"], "table-of-contents")

    def test_is_latest(self):
        """Test is_latest returns True for most recent page."""
        self.assertTrue(self.page.is_latest)
        # now add a release, but make it older
        StatisticalArticlePageFactory(
            parent=self.page.get_parent(),
            release_date=self.page.release_date - timezone.timedelta(days=1),
        )
        self.assertTrue(self.page.is_latest)

    def test_is_latest__unhappy_path(self):
        """Test is_latest returns False when newer pages exist."""
        StatisticalArticlePageFactory(
            parent=self.page.get_parent(),
            release_date=self.page.release_date + timezone.timedelta(days=1),
        )
        self.assertFalse(self.page.is_latest)

    def test_canonical_points_to_evergreen_if_latest_article_in_series(self):
        parent_article_series = self.page.get_parent()
        self.assertTrue(self.page.is_latest)

        response = self.client.get(parent_article_series.url)

        self.assertContains(
            response, f'<link rel="canonical" href="{parent_article_series.get_full_url()}">', html=True
        )

    def test_canonical_points_to_self_if_not_latest_article(self):
        """Test that the canonical link is self referential if the article is not the latest in the series."""
        StatisticalArticlePageFactory(  # New latest article in the series
            parent=self.page.get_parent(),
            release_date=self.page.release_date + timezone.timedelta(days=1),
        )

        self.assertFalse(self.page.is_latest)

        response = self.client.get(self.page.url)

        self.assertContains(response, f'<link rel="canonical" href="{self.page.get_full_url()}">', html=True)

    def test_related_data_canonical_points_to_evergreen_if_latest_article_in_series(self):
        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[("dataset_lookup", DatasetFactory())],
        )
        self.page.save_revision().publish()

        self.assertTrue(self.page.is_latest)

        parent_article_series = self.page.get_parent()

        response = self.client.get(f"{parent_article_series.url}/related-data")

        self.assertContains(
            response, f'<link rel="canonical" href="{parent_article_series.get_full_url()}/related-data">', html=True
        )

    def test_related_data_canonical_points_to_self_if_not_latest_article_in_series(self):
        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[("dataset_lookup", DatasetFactory())],
        )
        self.page.save_revision().publish()

        StatisticalArticlePageFactory(  # New latest article in the series
            parent=self.page.get_parent(),
            release_date=self.page.release_date + timezone.timedelta(days=1),
        )
        self.assertFalse(self.page.is_latest)

        response = self.client.get(f"{self.page.url}/related-data")

        # The RequestFactory's default SERVER_NAME is 'testserver'.
        # This is what is used in the request when building canonical URLs for this specific page.
        request_factory = RequestFactory()
        request_factory_server_name = request_factory._base_environ()["SERVER_NAME"]  # pylint: disable=protected-access

        self.assertContains(
            response,
            f'<link rel="canonical" href="http://{request_factory_server_name}{self.page.url}/related-data">',
            html=True,
        )

    def test_has_equations(self):
        """Test has_equations property."""
        self.assertFalse(self.page.has_equations)
        self.page.content = [
            {
                "type": "section",
                "value": {"title": "Test Section", "content": [{"type": "equation", "value": "$$y = mx + b$$"}]},
            }
        ]
        del self.page.has_equations  # clear cached property
        self.assertTrue(self.page.has_equations)

    def test_next_date_must_be_after_release_date(self):
        """Tests the model validates next release date is after the release date."""
        self.page.next_release_date = self.page.release_date
        with self.assertRaises(ValidationError) as info:
            self.page.clean()

        self.assertListEqual(info.exception.messages, ["The next release date must be after the release date."])

    def test_clean_validates_a_min_of_two_headline_figures_are_needed(self):
        figure_one = {
            "type": "figure",
            "value": {
                "figure_id": "figurexyz",
                "title": "Figure title XYZ",
                "figure": "100 Million and more",
                "supporting_text": "Reasons to add tests and use long test strings where possible",
            },
        }
        self.page.headline_figures = [figure_one]
        self.page.headline_figures_figure_ids = "figurexyz"

        with self.assertRaisesRegex(ValidationError, "If you add headline figures, please add at least 2."):
            # Should not validate with just one
            self.page.clean()
        # Should validate with two
        self.page.headline_figures = [
            figure_one,
            {
                "type": "figure",
                "value": {
                    "figure_id": "figureabc",
                    "title": "Another figure title for completeness",
                    "figure": "100 Billion and many more",
                    "supporting_text": "Figure supporting text ABC",
                },
            },
        ]
        self.page.headline_figures_figure_ids = "figurexyz,figureabc"
        self.page.clean()

    def test_clean_validates_a_max_of_six_headline_figures_can_be_added(self):
        self.login()

        data = nested_form_data(
            {
                "title": self.page.title,
                "slug": self.page.slug,
                "summary": rich_text(self.page.summary),
                "main_points_summary": rich_text(self.page.main_points_summary),
                "release_date": self.page.release_date,
                "content": streamfield(
                    [("section", {"title": "Test", "content": streamfield([("rich_text", rich_text("text"))])})]
                ),
                "datasets": streamfield([]),
                "dataset_sorting": "AS_SHOWN",
                "corrections": streamfield([]),
                "notices": streamfield([]),
                "headline_figures": streamfield(
                    [
                        (
                            "figure",
                            {
                                "figure_id": f"figure_{i}",
                                "title": "Figure title XYZ",
                                "figure": "100 Million and more",
                                "supporting_text": "Reasons to add tests and use long test strings where possible",
                            },
                        )
                        for i in range(7)
                    ]
                ),
                "featured_chart": streamfield([]),
            }
        )
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[self.page.pk]), data, follow=True)
        self.assertContains(response, "The maximum number of items is 6")

    def test_clean_validates_correct_equations(self):
        self.login()

        latex_formula = (
            r"\begin{bmatrix}"
            r"{a_{11}}&{a_{12}}&{\cdots}&{a_{1n}}\\"
            r"{a_{21}}&{a_{22}}&{\cdots}&{a_{2n}}\\"
            r"{\vdots}&{\vdots}&{\ddots}&{\vdots}\\"
            r"{a_{m1}}&{a_{m2}}&{\cdots}&{a_{mn}}\\"
            r"\end{bmatrix}"
        )

        latex_formula_cases = (
            r"\begin{cases}"
            r"a_1x+b_1y+c_1z=d_1\\"
            r"a_2x+b_2y+c_2z=d_2\\"
            r"a_3x+b_3y+c_3z=d_3\\"
            r"\end{cases}"
        )

        data = nested_form_data(
            {
                "title": self.page.title,
                "slug": self.page.slug,
                "summary": rich_text(self.page.summary),
                "main_points_summary": rich_text(self.page.main_points_summary),
                "release_date": self.page.release_date,
                "content": streamfield(
                    [
                        (
                            "section",
                            {"title": "Test", "content": streamfield([("equation", {"equation": latex_formula})])},
                        )
                    ]
                ),
                "datasets": streamfield([]),
                "dataset_sorting": "AS_SHOWN",
                "corrections": streamfield([]),
                "notices": streamfield([]),
                "headline_figures": streamfield([]),
                "featured_chart": streamfield([]),
            }
        )
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[self.page.pk]), data, follow=True)
        self.assertNotContains(response, "The equation is not valid MathJax. Please check the syntax and try again.")

        data["content-0-value-content-0-value-equation"] = latex_formula_cases
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[self.page.pk]), data, follow=True)
        self.assertNotContains(response, "The equation is not valid MathJax. Please check the syntax and try again.")

        data["content-0-value-content-0-value-equation"] = "$$a+b=c$$"
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[self.page.pk]), data, follow=True)
        self.assertNotContains(response, "The equation is not valid MathJax. Please check the syntax and try again.")

        data["content-0-value-content-0-value-equation"] = "$$test"  # Invalid LaTeX
        response = self.client.post(reverse("wagtailadmin_pages:edit", args=[self.page.pk]), data, follow=True)
        self.assertContains(response, "The equation is not valid MathJax. Please check the syntax and try again.")

    def test_related_datasets_sorting_alphabetic(self):
        dataset_a = {"title": "a", "description": "a", "url": "https://example.com"}
        dataset_b = Dataset.objects.create(namespace="b", edition="b", version="1", title="b", description="b")
        dataset_c = Dataset.objects.create(namespace="c", edition="c", version="1", title="c", description="c")

        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("dataset_lookup", dataset_c),
                ("dataset_lookup", dataset_b),
                ("manual_link", dataset_a),
            ],
        )
        self.page.dataset_sorting = SortingChoices.ALPHABETIC
        ordered_datasets = self.page.dataset_document_list
        ordered_dataset_titles = [d["title"]["text"] for d in ordered_datasets]
        self.assertEqual(
            ordered_dataset_titles,
            sorted(ordered_dataset_titles),
            "Expect the datasets to be sorted in title alphabetic order",
        )

    def test_related_datasets_sorting_as_shown(self):
        dataset_a = {"title": "a", "description": "a", "url": "https://example.com"}
        dataset_b = Dataset.objects.create(namespace="b", edition="b", version="1", title="b", description="b")
        dataset_c = Dataset.objects.create(namespace="c", edition="c", version="1", title="c", description="c")

        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("dataset_lookup", dataset_c),
                ("dataset_lookup", dataset_b),
                ("manual_link", dataset_a),
            ],
        )
        self.page.dataset_sorting = SortingChoices.AS_SHOWN
        ordered_datasets = self.page.dataset_document_list
        ordered_dataset_titles = [d["title"]["text"] for d in ordered_datasets]
        self.assertEqual(ordered_dataset_titles, ["c", "b", "a"], "Expect the datasets to be in the given order")

    def test_parent_for_choosers(self):
        self.assertEqual(self.page.parent_for_choosers, TopicPage.objects.ancestor_of(self.page).first())

    def test_word_count_simple_content(self):
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Test",
                    "content": [
                        {"type": "rich_text", "value": "Foobar " * 100},
                    ],
                },
            }
        ]
        self.page.news_headline = "Test1"
        self.page.summary = "Test2"
        self.page.save_revision().publish()

        self.assertEqual(self.page.word_count, 103)

    def test_word_count_varied_content(self):
        words = "Foo Bar 123"
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": words,
                    "content": [
                        {"type": "rich_text", "value": f"<b>{words}</b>"},
                        {
                            "type": "quote",
                            "value": {
                                "quote": words,
                                "attribution": words,
                            },
                        },
                        {
                            "type": "related_links",
                            "value": [
                                {
                                    "page": None,
                                    "external_url": "https://example.com",
                                    "title": words,
                                    "description": words,
                                    "content_type": "ARTICLE",
                                    "release_date": None,
                                }
                            ],
                        },
                    ],
                },
            }
        ]
        self.page.news_headline = words
        self.page.summary = words
        self.page.save_revision().publish()

        # Count each place where `words` is used, plus the `-` in the quote attribution and the "Article" label
        # on the related link
        expected_word_count = (8 * len(words.split())) + 2

        self.assertEqual(self.page.word_count, expected_word_count)

    def test_word_count_no_content(self):
        self.page.content = None
        self.page.news_headline = "Test"
        self.page.summary = "Test"
        self.page.save_revision().publish()

        self.assertEqual(self.page.word_count, 2)

    def test_get_analytics_values(self):
        analytics_values = self.page.get_analytics_values(get_dummy_request())
        self.assertEqual(analytics_values.get("pageTitle"), self.page.get_full_display_title())
        self.assertEqual(analytics_values.get("contentType"), self.page.analytics_content_type)
        self.assertEqual(analytics_values.get("contentGroup"), self.page.analytics_content_group)
        self.assertEqual(analytics_values.get("contentTheme"), self.page.analytics_content_theme)
        self.assertEqual(analytics_values.get("outputSeries"), self.page.get_parent().slug)
        self.assertEqual(analytics_values.get("latestRelease"), "yes")
        self.assertEqual(analytics_values.get("releaseDate"), format_date_for_gtm(self.page.release_date))
        self.assertEqual(analytics_values.get("wordCount"), self.page.word_count)

    def test_get_analytics_values_for_latest_via_non_evergreen_url(self):
        """Test that that page analytics values contains the evergreen series URL if the page is requested from it's
        full, non-evergreen URL.
        """
        analytics_values = self.page.get_analytics_values(get_dummy_request(path=self.page.get_full_url()))
        self.assertEqual(analytics_values.get("pageURL"), self.page.get_parent().get_full_url())

    def test_get_analytics_values_for_non_latest(self):
        """Test that the analytics values do not contain the evergreen series URL if the page is not the latest."""
        series = self.page.get_parent()
        new_latest_article = StatisticalArticlePageFactory(
            parent=series, release_date=self.page.release_date + timezone.timedelta(days=1)
        )
        new_latest_article.save_revision().publish()

        analytics_values = self.page.get_analytics_values(get_dummy_request(path=self.page.get_full_url()))
        self.assertEqual(analytics_values.get("latestRelease"), "no")
        self.assertNotIn("pageURL", analytics_values.keys())


class StatisticalArticlePageRenderTestCase(WagtailTestUtils, TestCase):
    def setUp(self):
        self.basic_page = StatisticalArticlePageFactory(
            parent__title="PSF",
            title="November 2024",
            news_headline="",
            contact_details=None,
            show_cite_this_page=False,
            next_release_date=None,
        )
        self.basic_page_url = self.basic_page.url

        # a page with more of the fields filled in
        self.page = StatisticalArticlePageFactory(
            parent=self.basic_page.get_parent(),
            title="August 2024",
            news_headline="Breaking News!",
            release_date=datetime(2024, 8, 15),
        )
        self.page.headline_figures = [
            {
                "type": "figure",
                "value": {
                    "figure_id": "figurexyz",
                    "title": "Figure title XYZ",
                    "figure": "XYZ",
                    "supporting_text": "Figure supporting text XYZ",
                },
            },
            {
                "type": "figure",
                "value": {
                    "figure_id": "figureabc",
                    "title": "Figure title ABC",
                    "figure": "ABC",
                    "supporting_text": "Figure supporting text ABC",
                },
            },
        ]
        self.page.headline_figures_figure_ids = "figurexyz,figureabc"
        self.page.save_revision().publish()
        self.page_url = self.page.url
        self.formatted_date = date_format(self.page.release_date, settings.DATE_FORMAT)
        self.user = self.create_superuser("admin")

    def test_display_title(self):
        """Check how the title is displayed on the front-end, with/without news headline."""
        response = self.client.get(self.basic_page_url)
        self.assertContains(response, "PSF: November 2024")

        # Set an SEO title so that the display title is also not included in the schema org properties
        self.page.seo_title = "SEO Title"
        self.page.save_revision().publish()

        response = self.client.get(self.page_url)
        self.assertNotContains(response, self.page.get_admin_display_title())
        self.assertContains(response, "Breaking News!")

    def test_full_display_title(self):
        self.assertEqual(self.basic_page.display_title, "PSF: November 2024")

        self.basic_page.title = "Lorem Ipsum"
        self.basic_page.save_revision()

        # The page object shows the newer title
        self.assertEqual(self.basic_page.display_title, "PSF: Lorem Ipsum")

        # However, the live page will show the old title until it is published
        response = self.client.get(self.basic_page_url)

        self.assertNotContains(response, "PSF: Lorem Ipsum")
        self.assertContains(response, "PSF: November 2024")

        self.basic_page.save_revision().publish()

        response = self.client.get(self.basic_page_url)

        self.assertContains(response, "PSF: Lorem Ipsum")
        self.assertNotContains(response, "PSF: November 2024")

    def test_next_release_date(self):
        """Checks that when no next release date, the template shows 'To be announced'."""
        response = self.client.get(self.basic_page_url)
        self.assertContains(response, "To be announced")

        response = self.client.get(self.page_url)
        self.assertNotContains(response, "To be announced")
        self.assertContains(response, self.formatted_date)

    def test_cite_this_page_is_shown_when_ticked(self):
        """Test for the cite this page block."""
        expected = (
            f"Office for National Statistics (ONS), released {self.formatted_date}, "
            f'ONS website, statistical article, <a href="{self.page.full_url}">Breaking News!</a>'
        )
        response = self.client.get(self.page_url)
        self.assertContains(response, expected)

    def test_cite_this_page_is_not_shown_when_unticked(self):
        """Test for the cite this page block not present in the template."""
        expected = (
            f"Office for National Statistics (ONS), released {self.formatted_date}, ONS website, statistical article"
        )

        response = self.client.get(self.basic_page_url)
        self.assertNotContains(response, expected)

    def test_breadcrumb_doesnt_contains_series_url(self):
        response = self.client.get(self.basic_page_url)
        # confirm that current breadcrumb is there
        article_series = self.basic_page.get_parent()
        self.assertNotContains(
            response,
            f'<a class="ons-breadcrumbs__link" href="{article_series.full_url}">{article_series.title}</a>',
            html=True,
        )

        # confirm that current breadcrumb points to the parent page
        topics_page = article_series.get_parent()
        self.assertContains(
            response,
            f'<a class="ons-breadcrumbs__link" href="{topics_page.full_url}">{topics_page.title}</a>',
            html=True,
        )

    def test_pagination_is_not_shown(self):
        response = self.client.get(self.basic_page_url)
        expected = 'class="ons-pagination__link"'
        self.assertNotContains(response, expected)

    def test_get_headline_figure(self):
        """Test get_headline_figure returns the correct figure."""
        # Test with a valid figure_id
        figure = self.page.get_headline_figure("figurexyz")
        self.assertEqual(figure["title"], "Figure title XYZ")
        self.assertEqual(figure["figure"], "XYZ")
        self.assertEqual(figure["supporting_text"], "Figure supporting text XYZ")

        # Test with an invalid figure_id
        figure = self.page.get_headline_figure("invalid_id")
        self.assertEqual(figure, {})

    def test_get_chart_from_content(self):
        """Test get_chart returns the correct chart from content sections."""
        table_data = TableDataFactory(
            table_data=[
                ["", "Series 1", "Series 2"],
                ["2020", "100", "150"],
                ["2021", "120", "180"],
            ]
        )

        # Create a StreamValue with chart blocks
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Line Chart",
                                "subtitle": "Line chart subtitle",
                                "audio_description": "Chart showing trend over time",
                                "table": table_data,
                                "theme": "primary",
                                "show_legend": True,
                                "x_axis": {"title": "Year"},
                                "y_axis": {"title": "Value"},
                            },
                            "id": "test-chart-id-1",
                        },
                        {
                            "type": "bar_column_chart",
                            "value": {
                                "title": "Test Bar Chart",
                                "subtitle": "Bar chart subtitle",
                                "audio_description": "Chart showing comparison",
                                "table": table_data,
                                "theme": "secondary",
                                "show_legend": False,
                                "x_axis": {"title": "Category"},
                                "y_axis": {"title": "Amount"},
                            },
                            "id": "test-chart-id-2",
                        },
                    ],
                },
            }
        ]
        self.page.save_revision().publish()

        # Test retrieving the line chart
        chart = self.page.get_chart("test-chart-id-1")
        self.assertEqual(chart["title"], "Test Line Chart")
        self.assertEqual(chart["subtitle"], "Line chart subtitle")
        self.assertEqual(chart["theme"], "primary")

        # Test retrieving the bar chart
        chart = self.page.get_chart("test-chart-id-2")
        self.assertEqual(chart["title"], "Test Bar Chart")
        self.assertEqual(chart["theme"], "secondary")
        self.assertEqual(chart["show_legend"], False)

    def test_get_chart_not_found(self):
        """Test get_chart returns empty dict when chart_id is not found."""
        table_data = TableDataFactory()

        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Chart Section",
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "title": "Test Chart",
                                "audio_description": "Test description",
                                "table": table_data,
                                "theme": "primary",
                                "show_legend": True,
                                "x_axis": {"title": ""},
                                "y_axis": {"title": ""},
                            },
                            "id": "known-chart-id",
                        }
                    ],
                },
            }
        ]
        self.page.save_revision().publish()

        # Test with invalid chart_id
        chart = self.page.get_chart("unknown-chart-id")
        self.assertEqual(chart, {})

    def test_get_chart_with_no_content(self):
        """Test get_chart returns empty dict when page has no content."""
        self.page.content = []
        self.page.save_revision().publish()

        chart = self.page.get_chart("any-chart-id")
        self.assertEqual(chart, {})

    def test_get_chart_with_multiple_chart_types(self):
        """Test get_chart works with all chart types."""
        table_data = TableDataFactory()

        chart_types = [
            "line_chart",
            "bar_column_chart",
            "bar_column_confidence_interval_chart",
            "scatter_plot",
            "area_chart",
        ]

        content_blocks = []
        for i, chart_type in enumerate(chart_types):
            content_blocks.append(
                {
                    "type": chart_type,
                    "value": {
                        "title": f"Chart {i}",
                        "audio_description": f"Description {i}",
                        "table": table_data,
                        "theme": "primary",
                        "show_legend": True,
                        "x_axis": {"title": ""},
                        "y_axis": {"title": ""},
                    },
                    "id": f"chart-id-{i}",
                }
            )

        self.page.content = [
            {
                "type": "section",
                "value": {
                    "title": "Multiple Charts Section",
                    "content": content_blocks,
                },
            }
        ]
        self.page.save_revision().publish()

        # Test that each chart can be retrieved
        for i in range(len(chart_types)):
            chart = self.page.get_chart(f"chart-id-{i}")
            self.assertEqual(chart["title"], f"Chart {i}")
            self.assertEqual(chart["audio_description"], f"Description {i}")

    def test_headline_figures_shown(self):
        """Test that the headline figures are shown in the template."""
        response = self.client.get(self.page_url)
        self.assertContains(response, "Figure title XYZ")
        self.assertContains(response, "Figure title ABC")
        self.assertContains(response, "XYZ")
        self.assertContains(response, "ABC")
        self.assertContains(response, "Figure supporting text XYZ")
        self.assertContains(response, "Figure supporting text ABC")

    def test_figures_used_by_ancestors(self):
        """Test that the figures used by ancestors are returned correctly."""
        topic = TopicPage.objects.ancestor_of(self.page).first()
        topic.headline_figures.extend(
            [
                (
                    "figure",
                    {
                        "series": self.page.get_parent(),
                        "figure_id": "figurexyz",
                    },
                ),
                (
                    "figure",
                    {
                        "series": self.page.get_parent(),
                        "figure_id": "figureabc",
                    },
                ),
            ]
        )
        topic.save_revision().publish()

        self.assertEqual(self.page.figures_used_by_ancestor, ["figurexyz", "figureabc"])

    def test_cannot_be_deleted_if_ancestor_uses_headline_figures(self):
        """Test that the page cannot be deleted if an ancestor uses the headline figures."""
        self.client.force_login(self.user)
        topic = TopicPage.objects.ancestor_of(self.page).first()
        topic.headline_figures.extend(
            [
                (
                    "figure",
                    {
                        "series": self.page.get_parent(),
                        "figure_id": "figurexyz",
                    },
                ),
                (
                    "figure",
                    {
                        "series": self.page.get_parent(),
                        "figure_id": "figureabc",
                    },
                ),
            ]
        )
        topic.save_revision().publish()

        # Try deleting page
        page_delete_url = reverse("wagtailadmin_pages:delete", args=[self.page.id])
        response = self.client.post(page_delete_url)

        self.assertRedirects(response, page_delete_url, 302)

        response = self.client.post(page_delete_url, follow=True)

        self.assertContains(
            response,
            "This page cannot be deleted because it contains headline figures that are referenced elsewhere.",
        )

        # Try deleting parent page
        parent_page_delete_url = reverse("wagtailadmin_pages:delete", args=[self.page.get_parent().id])
        response = self.client.post(parent_page_delete_url)

        self.assertRedirects(response, parent_page_delete_url, 302)

        response = self.client.post(parent_page_delete_url, follow=True)

        self.assertContains(
            response,
            "This page cannot be deleted because one or more of its children contain headline figures",
        )

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_load_in_external_env(self):
        """Test the page loads in external env."""
        response = self.client.get(self.basic_page_url)
        self.assertEqual(response.status_code, 200)

    def test_page_gtm_attributes(self):
        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

        datalayer_values = extract_datalayer_pushed_values(response.text)
        self.assertEqual(datalayer_values["product"], "wagtail")
        self.assertEqual(datalayer_values["gtm.allowlist"], ["google", "hjtc", "lcl"])
        self.assertEqual(datalayer_values["gtm.blocklist"], ["customScripts", "sp", "adm", "awct", "k", "d", "j"])
        self.assertEqual(datalayer_values["contentType"], self.page.analytics_content_type)
        self.assertEqual(datalayer_values["contentGroup"], self.page.analytics_content_group)
        self.assertEqual(datalayer_values["contentTheme"], self.page.analytics_content_theme)
        for key, value in self.page.get_analytics_values(get_dummy_request(path=self.page_url)).items():
            self.assertIn(key, datalayer_values)
            self.assertEqual(datalayer_values[key], value)


class StatisticalArticlePageFeaturedArticleTestCase(WagtailTestUtils, TestCase):
    def setUp(self):
        self.page = StatisticalArticlePageFactory(
            parent__title="PSF",
            title="November 2024",
            news_headline="",
            contact_details=None,
            show_cite_this_page=False,
            release_date=datetime(2024, 11, 1),
            main_points_summary="Test main points summary",
        )

    def test_as_featured_article_macro_data(self):
        request = RequestFactory().get("/")
        data = self.page.as_featured_article_macro_data(request)

        self.assertEqual(data["title"]["text"], self.page.display_title)
        self.assertIn("url", data["title"])
        parsed = urlparse(data["title"]["url"])
        self.assertEqual(parsed.netloc, "", "URL should be relative")
        self.assertEqual(parsed.path, self.page.url)

        self.assertEqual(data["metadata"]["text"], "Article")
        self.assertEqual(data["metadata"]["date"]["prefix"], "Release date")
        self.assertEqual(data["metadata"]["date"]["showPrefix"], True)
        self.assertEqual(data["metadata"]["date"]["short"], "1 November 2024")
        self.assertEqual(data["metadata"]["date"]["iso"], "2024-11-01")

        self.assertEqual(data["description"], "Test main points summary")

    def test_as_featured_article_macro_data_with_chart(self):
        """Test that a chart is used when available."""
        table_data = TableDataFactory(
            table_data=[
                ["", "Series 0"],
                ["2004", "100"],
                ["2005", "120"],
            ]
        )

        chart_data = {
            "type": "line_chart",
            "value": {
                "title": "Test Chart",
                "table": table_data,
                "theme": "primary",
                "show_legend": True,
                "x_axis": {"title": ""},
                "y_axis": {"title": ""},
            },
        }

        self.page.featured_chart = [chart_data]
        self.page.save()

        request = RequestFactory().get("/")
        data = self.page.as_featured_article_macro_data(request)

        self.assertEqual(data["chart"]["chartType"], "line")
        self.assertEqual(data["chart"]["title"], "Test Chart")
        self.assertEqual(data["chart"]["theme"], "primary")
        self.assertEqual(data["chart"]["headingLevel"], 3)

        self.assertNotIn("image", data)

    def test_as_featured_article_macro_data_without_chart(self):
        """Test that a listing image is used when there is no chart."""
        request = RequestFactory().get("/")
        data = self.page.as_featured_article_macro_data(request)

        self.assertNotIn("chart", data)

        self.assertEqual(data["image"]["src"], self.page.listing_image.get_rendition("width-1252").url)
        self.assertNotIn("alt", data["image"])


class PreviousReleasesWithoutPaginationTestCase(TestCase):
    # PREVIOUS_RELEASES_PER_PAGE is default value 10
    total_batch: int = 9

    @classmethod
    def setUpTestData(cls):
        cls.article_series = ArticleSeriesPageFactory(title="Article Series")
        cls.articles = StatisticalArticlePageFactory.create_batch(9, parent=cls.article_series)
        cls.previous_releases_url = (
            f"{cls.article_series.url}/{cls.article_series.reverse_subpage('previous_releases')}"
        )

    def test_breadcrumb_does_contains_series_url(self):
        response = self.client.get(self.previous_releases_url)
        parent_page = self.article_series.get_parent()
        # confirm that current breadcrumb is there and that current breadcrumb points to the parent page
        # TODO currently this test points to the article page not to the series page
        # f'<a class="ons-breadcrumbs__link" href="{self.article_series.url}">{self.article_series.title}</a>',

        self.assertContains(
            response,
            f'<a class="ons-breadcrumbs__link" href="{parent_page.full_url}">{parent_page.title}</a>',
            html=True,
        )

    def test_page_content(self):
        response = self.client.get(self.previous_releases_url)
        for article in self.articles:
            with self.subTest(article=article):
                self.assertContains(response, article.get_admin_display_title())
                self.assertContains(response, article.url)
        self.assertContains(response, 'class="ons-document-list__item"', count=self.total_batch)
        self.assertContains(response, "Latest release", count=1)

    def test_pagination_is_not_shown(self):
        response = self.client.get(self.previous_releases_url)
        self.assertNotContains(response, 'class="ons-pagination__link"')


@override_settings(PREVIOUS_RELEASES_PER_PAGE=3)
class PreviousReleasesWithPaginationPagesTestCase(TestCase):
    total_batch = 13
    test_previous_releases_per_page = 3
    total_pages = math.ceil(total_batch / test_previous_releases_per_page)

    @classmethod
    def setUpTestData(cls):
        cls.article_series = ArticleSeriesPageFactory(title="Article Series")
        cls.articles = StatisticalArticlePageFactory.create_batch(cls.total_batch, parent=cls.article_series)
        cls.previous_releases_base_url = (
            f"{cls.article_series.url}/{cls.article_series.reverse_subpage('previous_releases')}"
        )

    def assert_pagination(self, page_number, expected_contains, expected_not_contains):
        # Request the page at the given number
        response = self.client.get(f"{self.previous_releases_base_url}?page={page_number}")
        # Check for strings we expect to be present in the HTML response
        for snippet in expected_contains:
            with self.subTest(snippet=snippet):
                self.assertContains(response, snippet)
        # Check for strings we expect not to be present in the HTML response
        for snippet in expected_not_contains:
            with self.subTest(snippet=snippet):
                self.assertNotContains(response, snippet)

    def test_pagination_variants(self):
        # Define different test scenarios with expected visible/ not-visible pagination elements
        scenarios = {
            1: {  # First page
                "expected_contains": [
                    f'class="ons-pagination__position">Page 1 of {self.total_pages}',
                    'class="ons-pagination__item ons-pagination__item--current"',
                    f'aria-label="Last page ({self.total_pages})"',
                    'class="ons-pagination__item ons-pagination__item--next"',
                    'aria-label="Next page (2)"',
                ],
                "expected_not_contains": [
                    'aria-label="First page"',
                    'class="ons-pagination__item ons-pagination__item--previous"',
                    'aria-label="Previous page"',
                ],
            },
            3: {  # Middle page
                "expected_contains": [
                    f'class="ons-pagination__position">Page 3 of {self.total_pages}',
                    'aria-label="First page"',
                    'class="ons-pagination__item ons-pagination__item--previous"',
                    'aria-label="Page 2"',
                    'class="ons-pagination__item ons-pagination__item--current"',
                    f'aria-label="Last page ({self.total_pages})"',
                    'class="ons-pagination__item ons-pagination__item--next"',
                    'aria-label="Page 4"',
                ],
                "expected_not_contains": [],
            },
            5: {  # Last page
                "expected_contains": [
                    f'class="ons-pagination__position">Page 5 of {self.total_pages}',
                    'aria-label="First page"',
                    'class="ons-pagination__item ons-pagination__item--previous"',
                    'aria-label="Previous page (4)"',
                    'class="ons-pagination__item ons-pagination__item--current"',
                    'aria-current="true"',
                ],
                "expected_not_contains": [
                    f'aria-label="Last page ({self.total_pages})"',
                    'class="ons-pagination__item ons-pagination__item--next"',
                    'aria-label="Next page"',
                ],
            },
        }
        # Iterate through each scenario and run the pagination assertion
        for page, data in scenarios.items():
            with self.subTest(page=page):  # Helps identify which page scenario fails
                self.assert_pagination(page, data["expected_contains"], data["expected_not_contains"])


class ChartBlockTypesTestCase(TestCase):
    """Test case to sense-check computed constant value."""

    def test_known_type_in_chart_block_types(self):
        self.assertIn("line_chart", CHART_BLOCK_TYPES)
        self.assertIn("area_chart", CHART_BLOCK_TYPES)

    def test_known_non_chart_type_not_in_chart_block_types(self):
        self.assertNotIn("rich_text", CHART_BLOCK_TYPES)
