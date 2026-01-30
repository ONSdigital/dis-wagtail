from datetime import timedelta
from http import HTTPStatus

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse
from django.utils.html import strip_tags
from wagtail.blocks import StreamValue
from wagtail.coreutils import get_dummy_request
from wagtail.test.utils import WagtailPageTestCase

from cms.articles.enums import SortingChoices
from cms.articles.models import ArticlesIndexPage
from cms.articles.tests.factories import (
    ArticleSeriesPageFactory,
    ArticlesIndexPageFactory,
    StatisticalArticlePageFactory,
)
from cms.core.tests.factories import ContactDetailsFactory
from cms.core.tests.utils import TranslationResetMixin, extract_response_jsonld
from cms.datasets.blocks import DatasetStoryBlock
from cms.datasets.models import Dataset
from cms.home.models import HomePage
from cms.topics.models import TopicPage
from cms.topics.tests.factories import TopicPageFactory
from cms.topics.tests.utils import post_page_add_form_to_create_topic_page


class ArticleSeriesPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.article_series_page = ArticleSeriesPageFactory(title="The Article Series")
        cls.topic_page = TopicPageFactory()
        cls.articles_index_page = ArticlesIndexPageFactory(parent=cls.topic_page)

    def test_articles_index_page_redirects_to_topic_listing(self):
        response = self.client.get(self.articles_index_page.url)
        # Should redirect (307) to the topic's articles search URL
        self.assertRedirects(response, self.topic_page.get_articles_search_url(), 307, fetch_redirect_response=False)

    def test_default_route(self):
        self.assertPageIsRoutable(self.article_series_page)

    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.article_series_page, accept_404=True)
        StatisticalArticlePageFactory(parent=self.article_series_page, title="Statistical Article")
        self.assertPageIsRenderable(self.article_series_page, accept_404=False, accept_redirect=True)

    def test_default_route_renders_latest_article(self):
        article = StatisticalArticlePageFactory(parent=self.article_series_page, title="Latest Article")
        response = self.client.get(self.article_series_page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, article.title)

    def test_previous_releases_route(self):
        self.assertPageIsRoutable(self.article_series_page, "editions")

    def test_previous_releases_route_rendering(self):
        self.assertPageIsRenderable(self.article_series_page, "editions")

    def test_previous_releases_article_list(self):
        response = self.client.get(f"{self.article_series_page.url}/editions")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "There are currently no releases")

        first_article = StatisticalArticlePageFactory(parent=self.article_series_page)
        second_article = StatisticalArticlePageFactory(parent=self.article_series_page)

        response = self.client.get(f"{self.article_series_page.url}/editions")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, first_article.title)
        self.assertContains(response, second_article.title)

    def test_previous_releases_breadcrumbs(self):
        """Test that the previous releases page includes a breadcrumb for the latest article."""
        StatisticalArticlePageFactory(parent=self.article_series_page, title="Latest Article")
        response = self.client.get(f"{self.article_series_page.url}/editions")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Check the breadcrumbs include the series page link, which serves the evergreen latest article
        self.assertContains(
            response,
            f'<a class="ons-breadcrumbs__link" href="{self.article_series_page.full_url}">'
            f"{self.article_series_page.title}</a>",
            html=True,
        )


class StatisticalArticlePageTests(TranslationResetMixin, WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.series = ArticleSeriesPageFactory()
        cls.page = StatisticalArticlePageFactory(parent=cls.series, summary="This is the summary")
        # TODO: Fix the factory to generate headline_figures correctly
        cls.page.headline_figures = [
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
        cls.page.headline_figures_figure_ids = "figurexyz,figureabc"
        cls.page.save_revision().publish()
        cls.user = cls.create_superuser("admin")

    def setUp(self):
        self.dummy_request = get_dummy_request()

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)

    def test_page_content(self):
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.summary)

        self.assertContains(response, "Save or print this page")
        self.assertContains(response, "Sections in this page")
        self.assertContains(response, "Contents")
        self.assertContains(response, "Cite this article")

    def test_correction_routes(self):
        self.assertPageIsRoutable(self.page, "versions/1")
        self.assertPageIsRoutable(self.page, "versions/2")
        self.assertPageIsRoutable(self.page, "versions/3")

    def test_can_add_correction(self):  # pylint: disable=too-many-statements # noqa
        response = self.client.get(self.page.url)
        self.assertNotContains(response, "Corrections")
        self.assertNotContains(response, "Notices")
        self.assertNotContains(response, "View superseded version")

        self.page.save_revision().publish()

        original_revision_id = self.page.get_latest_revision().id

        original_summary = self.page.summary

        self.page.summary = "Corrected summary"

        first_correction = {
            "version_id": 1,
            "previous_version": original_revision_id,
            "when": "2025-01-11",
            "frozen": True,
            "text": "First correction text",
        }

        self.page.corrections = [
            (
                "correction",
                first_correction,
            )
        ]

        self.page.save_revision().publish()

        second_revision_id = self.page.get_latest_revision().id

        response = self.client.get(self.page.url)

        self.assertContains(response, "Corrections")
        self.assertContains(response, "First correction text")
        self.assertNotContains(response, "Notices")
        self.assertContains(response, "View superseded version")
        self.assertNotContains(response, original_summary)
        self.assertContains(response, "Corrected summary")

        v1_response = self.client.get(f"{self.page.url}/versions/1")

        # The old version should not contain corrections
        self.assertNotContains(v1_response, "Corrections")
        self.assertNotContains(v1_response, "View superseded version")
        self.assertContains(v1_response, original_summary)

        # V2 doesn't exist yet, should return 404
        v2_response = self.client.get(f"{self.page.url}/versions/2")
        self.assertEqual(v2_response.status_code, HTTPStatus.NOT_FOUND)

        second_correction = {
            "version_id": 2,
            "previous_version": second_revision_id,
            "when": "2025-01-12",
            "frozen": True,
            "text": "Second correction text",
        }

        self.page.summary = "Second corrected summary"

        self.page.corrections = [
            (
                "correction",
                second_correction,
            ),
            (
                "correction",
                first_correction,
            ),
        ]

        self.page.save_revision().publish()

        third_revision_id = self.page.get_latest_revision().id

        response = self.client.get(self.page.url)

        self.assertContains(response, "Corrections")
        self.assertContains(response, "First correction text")
        self.assertContains(response, "Second correction text")
        self.assertContains(response, "Second corrected summary")

        # V2 now exists
        v2_response = self.client.get(f"{self.page.url}/versions/2")
        self.assertEqual(v2_response.status_code, HTTPStatus.OK)

        self.assertContains(v2_response, "Corrections")
        self.assertContains(v2_response, "First correction text")
        self.assertNotContains(v2_response, "Second correction text")

        # V3 doesn't exist yet, should return 404
        v3_response = self.client.get(f"{self.page.url}/versions/3")
        self.assertEqual(v3_response.status_code, HTTPStatus.NOT_FOUND)

        third_correction = {
            "version_id": 3,
            "previous_version": third_revision_id,
            "when": "2025-01-13",
            "frozen": True,
            "text": "Third correction text",
        }

        self.page.summary = "Third corrected summary"

        self.page.corrections = [
            (
                "correction",
                third_correction,
            ),
            (
                "correction",
                second_correction,
            ),
            (
                "correction",
                first_correction,
            ),
        ]

        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(response, "Corrections")
        self.assertContains(response, "First correction text")
        self.assertContains(response, "Second correction text")
        self.assertContains(response, "Third correction text")
        self.assertContains(response, "Third corrected summary")

        # V3 now exists
        v3_response = self.client.get(f"{self.page.url}/versions/3")
        self.assertEqual(v3_response.status_code, HTTPStatus.OK)

        self.assertContains(v3_response, "Corrections")
        self.assertContains(v3_response, "First correction text")
        self.assertContains(v3_response, "Second correction text")
        self.assertNotContains(v3_response, "Third correction text")

        # Check that at this stage all other versions are still correct
        v1_response = self.client.get(f"{self.page.url}/versions/1")
        self.assertNotContains(v1_response, "Corrections")
        self.assertNotContains(v1_response, "View superseded version")
        self.assertContains(v1_response, original_summary)

        v2_response = self.client.get(f"{self.page.url}/versions/2")
        self.assertContains(v2_response, "Corrections")
        self.assertContains(v2_response, "First correction text")
        self.assertNotContains(v2_response, "Second correction text")

    def test_superseeded_version_uses_correct_title(self):
        """Test that the superseded version uses the correct title."""
        old_title = self.page.title

        self.page.save_revision().publish()

        original_revision_id = self.page.get_latest_revision().id

        self.page.title = "New title"

        first_correction = {
            "version_id": 1,
            "previous_version": original_revision_id,
            "when": "2025-01-11",
            "frozen": True,
            "text": "Foobar correction text",
        }

        self.page.corrections = [
            (
                "correction",
                first_correction,
            )
        ]

        self.page.save_revision().publish()

        live_response = self.client.get(self.page.url)
        self.assertContains(live_response, "New title")
        self.assertNotContains(live_response, old_title)

        v1_response = self.client.get(f"{self.page.url}/versions/1")

        self.assertNotContains(v1_response, "New title")
        self.assertContains(v1_response, old_title)

    def test_correction_toc_rendering(self):
        self.page.content = [
            {
                "type": "section",
                "value": {"title": "Precorrection title", "content": [{"type": "rich_text", "value": "text"}]},
            }
        ]
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(response, "Precorrection title")

        page_content = response.content.decode(encoding="utf-8")

        self.assertInHTML(
            '<a class="ons-list__link" href="#precorrection-title">Precorrection title</a>',
            page_content,
        )

        original_revision_id = self.page.get_latest_revision().id

        first_correction = {
            "version_id": 1,
            "previous_version": original_revision_id,
            "when": "2025-01-11",
            "frozen": True,
            "text": "Foobar correction text",
        }

        self.page.corrections = [
            (
                "correction",
                first_correction,
            )
        ]

        self.page.content = [
            {
                "type": "section",
                "value": {"title": "Postcorrection title", "content": [{"type": "rich_text", "value": "text"}]},
            }
        ]

        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(response, "Postcorrection title")
        self.assertNotContains(response, "Precorrection title")

        page_content = response.content.decode(encoding="utf-8")

        self.assertInHTML(
            '<a class="ons-list__link" href="#postcorrection-title">Postcorrection title</a>',
            page_content,
        )

        v1_response = self.client.get(f"{self.page.url}/versions/1")

        page_content = v1_response.content.decode(encoding="utf-8")

        self.assertInHTML(
            '<a class="ons-list__link" href="#precorrection-title">Precorrection title</a>',
            page_content,
        )

        self.assertNotInHTML(
            '<a class="ons-list__link" href="#postcorrection-title">Postcorrection title</a>',
            page_content,
        )

    def test_hero_rendering(self):
        response = self.client.get(self.page.url)

        # Breadcrumbs
        content = response.content.decode(encoding="utf-8")

        topic = self.page.get_parent().get_parent()
        theme = topic.get_parent()

        self.assertInHTML(
            f'<a class="ons-breadcrumbs__link" href="{topic.full_url}">{topic.title}</a>',
            content,
        )

        self.assertInHTML(
            f'<a class="ons-breadcrumbs__link" href="{theme.full_url}">{theme.title}</a>',
            content,
        )

        # Census
        self.assertNotContains(response, "ons-hero__census-logo")

        self.page.is_census = True
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)
        self.assertContains(response, "ons-hero__census-logo")

        # Accreditation badge
        self.assertNotContains(response, "ons-hero__badge")

        self.page.is_accredited = True
        self.page.save_revision().publish()
        response = self.client.get(self.page.url)

        self.assertContains(response, "ons-hero__badge")

        # Release dates
        self.page.release_date = "2025-01-01"
        self.page.next_release_date = None
        self.page.save_revision().publish()
        response = self.client.get(self.page.url)
        content = response.content.decode(encoding="utf-8")

        self.assertInHTML(
            '<dd class="ons-description-list__value ons-grid__col ons-col-6@xs@l">1 January 2025</dd>',
            content,
        )
        self.assertInHTML(
            '<dd class="ons-description-list__value ons-grid__col ons-col-6@xs@l">To be announced</dd>',
            content,
        )

        self.page.next_release_date = "2025-02-03"
        self.page.save_revision().publish()
        response = self.client.get(self.page.url)
        content = response.content.decode(encoding="utf-8")

        self.assertInHTML(
            '<dd class="ons-description-list__value ons-grid__col ons-col-6@xs@l">1 January 2025</dd>',
            content,
        )
        self.assertInHTML(
            '<dd class="ons-description-list__value ons-grid__col ons-col-6@xs@l">3 February 2025</dd>',
            content,
        )
        self.assertNotInHTML(
            '<dd class="ons-description-list__value ons-grid__col ons-col-6@xs@l">To be announced</dd>',
            content,
        )

    def test_prepopulated_content(self):
        self.client.force_login(self.user)
        parent_page = self.page.get_parent()
        add_sibling_url = reverse("wagtailadmin_pages:add_subpage", args=[parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(
            response, "This page has been prepopulated with the content from the latest page in the series."
        )

        self.assertContains(response, self.page.summary)
        self.assertContains(response, self.page.contact_details)
        self.assertContains(response, self.page.search_description)
        self.assertContains(response, self.page.headline_figures[0].value["title"])
        self.assertContains(response, self.page.headline_figures[0].value["supporting_text"])

    def test_headline_figures_removal_validation(self):
        series = self.page.get_parent()
        topic = TopicPage.objects.ancestor_of(series).first()
        topic.headline_figures.extend(
            [
                (
                    "figure",
                    {
                        "series": series,
                        "figure_id": "figurexyz",
                    },
                ),
                (
                    "figure",
                    {
                        "series": series,
                        "figure_id": "figureabc",
                    },
                ),
            ]
        )

        topic.save_revision().publish()

        self.page.headline_figures = []

        with self.assertRaisesRegex(
            ValidationError, "Figure ID figurexyz cannot be removed as it is referenced in a topic page."
        ):
            # We've removed the figures while they are referenced by the topic
            self.page.clean()

    def test_correct_template_used_for_edit_page(self):
        """Test that the edit page uses the correct template."""
        self.client.force_login(self.user)
        edit_url = reverse("wagtailadmin_pages:edit", args=[self.page.id])
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(
            response,
            "wagtailadmin/panels/headline_figures/figures_used_by_ancestor_data.html",
            "Template required by Headline Figures functionality was not used",
        )

    def test_related_data_route(self):
        self.assertPageIsRoutable(self.page, "/related-data")

    def test_related_data_page(self):
        lookup_dataset = Dataset.objects.create(
            namespace="LOOKUP",
            edition="lookup_edition",
            version=1,
            title="test lookup",
            description="lookup description",
        )
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("dataset_lookup", lookup_dataset),
                ("manual_link", manual_dataset),
            ],
        )
        self.page.save_revision().publish()
        response = self.client.get(f"{self.page.url}/related-data")
        content = response.content.decode(encoding="utf-8")

        self.assertIn(self.page.related_data_display_title, content)
        self.assertIn(lookup_dataset.title, content)
        self.assertIn(lookup_dataset.description, content)
        self.assertIn(lookup_dataset.url_path, content)
        self.assertIn(manual_dataset["title"], content)
        self.assertIn(manual_dataset["description"], content)
        self.assertIn(manual_dataset["url"], content)

    def test_empty_related_data_page(self):
        response = self.client.get(f"{self.page.url}/related-data")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_related_data_link_present(self):
        """Test that the related data link and ToC is rendered when there is related data for the article."""
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("manual_link", manual_dataset),
            ],
        )
        self.page.save_revision().publish()
        response = self.client.get(self.page.url)
        content = response.content.decode(encoding="utf-8")

        self.assertIn("Explore Data", content)
        self.assertIn("View data used in this article", content)

    def test_related_data_link_not_present(self):
        """Test that the related data link is not rendered when there is no related data for the article."""
        response = self.client.get(self.page.url)
        content = response.content.decode(encoding="utf-8")

        self.assertNotIn("Explore Data", content)
        self.assertNotIn("View data used in this article", content)

    def test_related_data_page_single_page(self):
        """Test that pagination is not shown when the content fits on a single page."""
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("manual_link", manual_dataset),
            ],
        )
        self.page.save_revision().publish()
        response = self.client.get(f"{self.page.url}/related-data")
        content = response.content.decode(encoding="utf-8")

        self.assertNotIn('class="ons-pagination__item ons-pagination__item--previous"', content)
        self.assertNotIn('class="ons-pagination__item ons-pagination__item--current"', content)
        self.assertNotIn('class="ons-pagination__item ons-pagination__item--next"', content)

    @override_settings(RELATED_DATASETS_PER_PAGE=1)
    def test_related_data_page_with_pagination(self):
        """Test that pagination is shown when there is more than one page."""
        manual_datasets = [
            {"title": "test1", "description": "test", "url": "https://example.com/1"},
            {"title": "test2", "description": "test", "url": "https://example.com/2"},
            {"title": "test3", "description": "test", "url": "https://example.com/3"},
            {"title": "test4", "description": "test", "url": "https://example.com/4"},
        ]
        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[("manual_link", dataset) for dataset in manual_datasets],
        )
        self.page.save_revision().publish()
        response = self.client.get(f"{self.page.url}/related-data?page=2")
        content = response.content.decode(encoding="utf-8")

        self.assertIn('class="ons-pagination__item ons-pagination__item--previous"', content)
        self.assertIn('class="ons-pagination__item ons-pagination__item--current"', content)
        self.assertIn('class="ons-pagination__item ons-pagination__item--next"', content)
        self.assertIn('class="ons-pagination__position">Page 2 of 4', content)

    def test_prepopulated_datasets(self):
        lookup_dataset = Dataset.objects.create(
            namespace="LOOKUP",
            edition="lookup_edition",
            version=1,
            title="test lookup",
            description="lookup description",
        )
        manual_dataset = {"title": "test manual", "description": "manual description", "url": "https://example.com"}

        self.page.datasets = StreamValue(
            DatasetStoryBlock(),
            stream_data=[
                ("dataset_lookup", lookup_dataset),
                ("manual_link", manual_dataset),
            ],
        )
        self.page.dataset_sorting = SortingChoices.ALPHABETIC
        self.page.save_revision().publish()

        self.client.force_login(self.user)
        parent_page = self.page.get_parent()
        add_sibling_url = reverse("wagtailadmin_pages:add_subpage", args=[parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(
            response, "This page has been prepopulated with the content from the latest page in the series."
        )

        new_page = response.context_data["form"].instance

        self.assertEqual(new_page.datasets, self.page.datasets)
        self.assertEqual(new_page.dataset_sorting, self.page.dataset_sorting)

    def test_latest_page_canonical_url(self):
        """Test that articles have the correct canonical series evergreen URL."""
        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response, f'<link rel="canonical" href="{self.series.get_full_url(request=self.dummy_request)}" />'
        )

    def test_non_latest_page_canonical_url(self):
        """Test that once an article page is not the latest, the canonical URL becomes the page's own full URL."""
        # Create new, later article in the series
        StatisticalArticlePageFactory(parent=self.series, release_date=self.page.release_date + timedelta(days=1))
        self.assertFalse(self.page.is_latest)

        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(
            response, f'<link rel="canonical" href="{self.page.get_full_url(request=self.dummy_request)}" />'
        )

    def test_corrected_article_versions_are_marked_no_index(self):
        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertNotContains(response, "Corrections")
        self.assertNotContains(response, "Notices")
        self.assertNotContains(response, "View superseded version")
        self.assertNotContains(response, '<meta name="robots" content="noindex" />')

        self.page.save_revision().publish()

        original_revision_id = self.page.get_latest_revision().id

        self.page.summary = "Corrected summary"

        first_correction = {
            "version_id": 1,
            "previous_version": original_revision_id,
            "when": "2025-01-11",
            "frozen": True,
            "text": "First correction text",
        }

        self.page.corrections = [
            (
                "correction",
                first_correction,
            )
        ]

        self.page.save_revision().publish()

        v1_response = self.client.get(self.page.get_url(request=self.dummy_request) + "/versions/1")
        self.assertContains(v1_response, '<meta name="robots" content="noindex" />')

    def test_schema_org_data(self):
        """Test that the page has the correct schema.org markup."""
        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        actual_jsonld = extract_response_jsonld(response.content, self)

        self.assertEqual(actual_jsonld["@context"], "http://schema.org")
        self.assertEqual(actual_jsonld["@type"], "Article")
        self.assertEqual(actual_jsonld["headline"], self.page.get_full_display_title())
        self.assertEqual(actual_jsonld["url"], self.page.get_full_url(self.dummy_request))
        self.assertEqual(actual_jsonld["@id"], self.page.get_full_url(self.dummy_request))
        self.assertEqual(actual_jsonld["description"], strip_tags(self.page.summary))
        self.assertEqual(actual_jsonld["datePublished"], self.page.release_date.isoformat())
        self.assertIn("breadcrumb", actual_jsonld)
        self.assertEqual(actual_jsonld["author"]["@type"], "Person")
        self.assertEqual(actual_jsonld["author"]["name"], self.page.contact_details.name)

        self.assertEqual(actual_jsonld["publisher"]["@type"], "Organization")
        self.assertEqual(actual_jsonld["publisher"]["name"], "Office for National Statistics")
        self.assertEqual(actual_jsonld["publisher"]["url"], settings.ONS_WEBSITE_BASE_URL)

        self.assertEqual(actual_jsonld["mainEntityOfPage"]["@type"], "WebPage")
        self.assertEqual(actual_jsonld["mainEntityOfPage"]["@id"], self.page.get_full_url(self.dummy_request))

    def test_schema_org_contact_falls_back_to_org_name(self):
        """Test that the schema.org contact defaults to the organisation name and type."""
        self.page.contact_details = None
        self.page.save_revision().publish()

        response = self.client.get(self.page.get_url(request=self.dummy_request))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        actual_jsonld = extract_response_jsonld(response.content, self)

        self.assertEqual(actual_jsonld["author"]["name"], settings.ONS_ORGANISATION_NAME)
        self.assertEqual(actual_jsonld["author"]["@type"], "Organization")

    def test_schema_org_headline(self):
        """Test the schema.org headline uses the seo_title by default,
        falling back to listing_title and then page title.
        """
        headline_cases = [
            {
                "seo_title": "SEO Title",
                "listing_title": "Listing Title",
                "expected_headline": "SEO Title",
            },
            {
                "seo_title": "",
                "listing_title": "Listing Title",
                "expected_headline": "Listing Title",
            },
            {
                "seo_title": "",
                "listing_title": "",
                "expected_headline": self.page.get_full_display_title(),
            },
        ]

        for headline_case in headline_cases:
            with self.subTest(headline_case=headline_case):
                self.page.seo_title = headline_case["seo_title"]
                self.page.listing_title = headline_case["listing_title"]
                self.page.save_revision().publish()

                response = self.client.get(self.page.get_url(request=self.dummy_request))
                self.assertEqual(response.status_code, HTTPStatus.OK)
                actual_jsonld = extract_response_jsonld(response.content, self)

                self.assertEqual(actual_jsonld["headline"], headline_case["expected_headline"])

    def test_schema_org_description(self):
        """Test the schema.org headline uses the search_description by default,
        falling back to listing_summary and then page summary (stripped on html tags).
        """
        description_cases = [
            {
                "search_description": "Search description",
                "listing_summary": "Listing summary",
                "expected_description": "Search description",
            },
            {
                "search_description": "",
                "listing_summary": "Listing summary",
                "expected_description": "Listing summary",
            },
            {
                "search_description": "",
                "listing_summary": "",
                "expected_description": strip_tags(self.page.summary),
            },
        ]

        for description_case in description_cases:
            with self.subTest(description_case=description_case):
                self.page.search_description = description_case["search_description"]
                self.page.listing_summary = description_case["listing_summary"]
                self.page.save_revision().publish()

                response = self.client.get(self.page.get_url(request=self.dummy_request))
                self.assertEqual(response.status_code, HTTPStatus.OK)
                actual_jsonld = extract_response_jsonld(response.content, self)

                self.assertEqual(actual_jsonld["description"], description_case["expected_description"])

    def test_chart_block_with_footnotes(self):
        self.page.content = [
            {
                "type": "section",
                "value": {
                    "content": [
                        {
                            "type": "line_chart",
                            "value": {
                                "annotations": [],
                                "audio_description": "desc",
                                "caption": "",
                                "footnotes": "This is a lovely footnote",
                                "options": [],
                                "show_legend": True,
                                "show_markers": False,
                                "subtitle": "subtitle",
                                "table": {
                                    "table_data": '{"data": [["Foo","Bar"],["1234","1337"],["",""],["",""],["",""]]}',
                                    "table_type": "table",
                                },
                                "theme": "primary",
                                "title": "line chart",
                                "x_axis": {"tick_interval_desktop": None, "tick_interval_mobile": None, "title": ""},
                                "y_axis": {
                                    "custom_reference_line": None,
                                    "end_on_tick": True,
                                    "max": None,
                                    "min": None,
                                    "start_on_tick": True,
                                    "tick_interval_desktop": None,
                                    "tick_interval_mobile": None,
                                    "title": "",
                                },
                            },
                        },
                    ],
                    "title": "section",
                },
            }
        ]
        self.page.save_revision().publish()
        response = self.client.get(self.page.url)
        self.assertContains(response, "Footnotes")
        self.assertContains(response, "This is a lovely footnote")
        self.assertContains(response, "Foo")
        self.assertContains(response, "Bar")
        self.assertContains(response, "1234")
        self.assertContains(response, "1337")

    def test_contact_details_mailto_link(self):
        """Test that the contact details email is rendered as a mailto protocol link."""
        contact_details = ContactDetailsFactory(email="test@example.com")
        self.page.contact_details = contact_details
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(
            response,
            f'<a href="mailto:{self.page.contact_details.email}">{self.page.contact_details.email}</a>',
            html=True,
        )

    def test_contact_details_tel_link(self):
        """Test that the contact details phone number is rendered as a tel protocol link."""
        contact_details = ContactDetailsFactory(phone="01234567890")
        self.page.contact_details = contact_details
        self.page.save_revision().publish()

        response = self.client.get(self.page.url)

        self.assertContains(
            response,
            f'<a href="tel:{self.page.contact_details.phone}">{self.page.contact_details.phone}</a>',
            html=True,
        )

    def test_article_page_uses_correct_toc_class(self):
        """Test that the article page uses the correct table of contents class."""
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ons-js-table-of-contents-container")
        self.assertNotContains(response, "ons-js-toc-container")


class GeneralPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = HomePage.objects.first()
        cls.user = cls.create_superuser("admin")

    def setUp(self):
        self.client.force_login(self.user)

    def test_date_placeholder_on_article_edit_form(self):
        """Test that the date input field displays date placeholder."""
        page = StatisticalArticlePageFactory()
        response = self.client.get(reverse("wagtailadmin_pages:add_subpage", args=[page.get_parent().id]), follow=True)

        date_placeholder = "YYYY-MM-DD"

        self.assertContains(
            response,
            (
                f'<input type="text" name="release_date" autocomplete="off" placeholder="{date_placeholder}"'
                'aria-describedby="panel-child-content-child-metadata-child-dates-child-release_date-helptext"'
                'required="" id="id_release_date">'
            ),
            html=True,
        )

        self.assertContains(
            response,
            (
                f'<input type="text" name="next_release_date" autocomplete="off" placeholder="{date_placeholder}"'
                ' aria-describedby="panel-child-content-child-metadata-child-dates-child-next_release_date-helptext"'
                'id="id_next_release_date">'
            ),
            html=True,
        )

    def test_articles_index_created_after_topic_page_creation(self):
        self.assertEqual(ArticlesIndexPage.objects.count(), 0)

        post_page_add_form_to_create_topic_page(self.client, self.home_page.pk)

        self.assertEqual(ArticlesIndexPage.objects.count(), 2)
        self.assertEqual(
            set(ArticlesIndexPage.objects.values_list("locale__language_code", flat=True)), {"en-gb", "cy"}
        )
