from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.home.models import HomePage
from cms.methodology.models import MethodologyIndexPage
from cms.methodology.tests.factories import (
    MethodologyIndexPageFactory,
    MethodologyPageFactory,
    MethodologyRelatedPageFactory,
)
from cms.topics.tests.factories import TopicPageFactory
from cms.topics.tests.utils import post_page_add_form_to_create_topic_page


class MethodologyPageTest(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = MethodologyPageFactory()
        cls.user = cls.create_superuser("admin")
        cls.topic_page = TopicPageFactory()
        cls.methodology_index_page = MethodologyIndexPageFactory(parent=cls.topic_page)

    def test_methodology_index_page_redirects_to_topic_listing(self):
        response = self.client.get(self.methodology_index_page.url)
        self.assertRedirects(
            response, self.topic_page.get_methodologies_search_url(), 307, fetch_redirect_response=False
        )

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)

    def test_methodology_page_template(self):
        """Test that the methodology page template is correct."""
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.page.title)
        self.assertContains(response, "Save or print this page")
        self.assertContains(response, "Cite this methodology")

    def test_methodology_page_uses_correct_toc_class(self):
        """Test that the methodology page uses the correct table of contents class."""
        response = self.client.get(self.page.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ons-js-table-of-contents-container")
        self.assertNotContains(response, "ons-js-toc-container")

    def test_related_publications(self):
        response = self.client.get(self.page.url)
        self.assertNotContains(response, "Related publications")

        related = MethodologyRelatedPageFactory(parent=self.page)

        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Related publications")
        self.assertContains(response, related.page.url)
        self.assertContains(response, related.page.display_title)

    def test_date_placeholder(self):
        """Test that the date input field displays date placeholder."""
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("wagtailadmin_pages:add", args=["methodology", "methodologypage", self.page.get_parent().id])
        )

        date_placeholder = "YYYY-MM-DD"

        self.assertContains(
            response,
            (
                '<input type="text" name="publication_date" autocomplete="off"'
                f'placeholder="{date_placeholder}" required="" id="id_publication_date">'
            ),
            html=True,
        )

        self.assertContains(
            response,
            (
                '<input type="text" name="last_revised_date" autocomplete="off"'
                f'placeholder="{date_placeholder}" id="id_last_revised_date">'
            ),
            html=True,
        )


class MethodologyIndexPageTest(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home_page = HomePage.objects.first()
        cls.user = cls.create_superuser("admin")

    def setUp(self):
        self.client.force_login(self.user)

    def test_methodology_index_created_after_topic_page_creation(self):
        self.assertEqual(MethodologyIndexPage.objects.count(), 0)

        post_page_add_form_to_create_topic_page(self.client, self.home_page.pk)

        self.assertEqual(MethodologyIndexPage.objects.count(), 2)
        self.assertEqual(
            set(MethodologyIndexPage.objects.values_list("locale__language_code", flat=True)), {"en-gb", "cy"}
        )
