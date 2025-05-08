from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.articles.tests.factories import ArticleSeriesPageFactory, StatisticalArticlePageFactory


class ArticleSeriesPageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = ArticleSeriesPageFactory()

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    def test_default_route_redirect(self):
        StatisticalArticlePageFactory(parent=self.page)
        response = self.client.get(self.page.url)
        self.assertRedirects(response, self.page.url + "latest/")

    def test_latest_route(self):
        self.assertPageIsRoutable(self.page, "latest/")

    def test_latest_route_rendering(self):
        self.assertPageIsRenderable(self.page, "latest/", accept_404=True)

    def test_latest_route_rendering_of_article(self):
        article = StatisticalArticlePageFactory(parent=self.page)
        response = self.client.get(self.page.url + "latest/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, article.title)

    def test_previous_releases_route(self):
        self.assertPageIsRoutable(self.page, "previous-releases/")

    def test_previous_releases_route_rendering(self):
        self.assertPageIsRenderable(self.page, "previous-releases/")

    def test_previous_releases_article_list(self):
        response = self.client.get(self.page.url + "previous-releases/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "There are currently no releases")

        first_article = StatisticalArticlePageFactory(parent=self.page)
        second_article = StatisticalArticlePageFactory(parent=self.page)

        response = self.client.get(self.page.url + "previous-releases/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, first_article.title)
        self.assertContains(response, second_article.title)


class StatisticalArticlePageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = StatisticalArticlePageFactory()
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

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)

    def test_page_content(self):
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.summary)

    def test_localised_version_of_page_works(self):
        response = self.client.get("/cy" + self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Body of the page is still English
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.summary)

        # However, the page's furniture should be in Welsh
        self.assertContains(response, "Mae'r holl gynnwys ar gael o dan delerau'r")

    def test_unknown_localised_version_of_page_404(self):
        response = self.client.get("/fr" + self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_correction_routes(self):
        self.assertPageIsRoutable(self.page, "previous/v1/")
        self.assertPageIsRoutable(self.page, "previous/v2/")
        self.assertPageIsRoutable(self.page, "previous/v3/")

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

        v1_response = self.client.get(self.page.url + "previous/v1/")

        # The old version should not contain corrections
        self.assertNotContains(v1_response, "Corrections")
        self.assertNotContains(v1_response, "View superseded version")
        self.assertContains(v1_response, original_summary)

        # V2 doesn't exist yet, should return 404
        v2_response = self.client.get(self.page.url + "previous/v2/")
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
        v2_response = self.client.get(self.page.url + "previous/v2/")
        self.assertEqual(v2_response.status_code, HTTPStatus.OK)

        self.assertContains(v2_response, "Corrections")
        self.assertContains(v2_response, "First correction text")
        self.assertNotContains(v2_response, "Second correction text")

        # V3 doesn't exist yet, should return 404
        v3_response = self.client.get(self.page.url + "previous/v3/")
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
        v3_response = self.client.get(self.page.url + "previous/v3/")
        self.assertEqual(v3_response.status_code, HTTPStatus.OK)

        self.assertContains(v3_response, "Corrections")
        self.assertContains(v3_response, "First correction text")
        self.assertContains(v3_response, "Second correction text")
        self.assertNotContains(v3_response, "Third correction text")

        # Check that at this stage all other versions are still correct

        v1_response = self.client.get(self.page.url + "previous/v1/")
        self.assertNotContains(v1_response, "Corrections")
        self.assertNotContains(v1_response, "View superseded version")
        self.assertContains(v1_response, original_summary)

        v2_response = self.client.get(self.page.url + "previous/v2/")
        self.assertContains(v2_response, "Corrections")
        self.assertContains(v2_response, "First correction text")
        self.assertNotContains(v2_response, "Second correction text")

    def test_hero_rendering(self):
        response = self.client.get(self.page.url)

        # Breadcrumbs
        content = response.content.decode(encoding="utf-8")

        topic = self.page.get_parent().get_parent()
        theme = topic.get_parent()

        self.assertInHTML(
            f'<a class="ons-breadcrumbs__link" href="{topic.url}">{topic.title}</a>',
            content,
        )

        self.assertInHTML(
            f'<a class="ons-breadcrumbs__link" href="{theme.url}">{theme.title}</a>',
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
        topic = series.get_parent()
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
