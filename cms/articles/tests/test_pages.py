from http import HTTPStatus

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

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)

    def test_page_content(self):
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.summary)

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
