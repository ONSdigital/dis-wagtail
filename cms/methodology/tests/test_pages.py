from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.methodology.tests.factories import MethodologyPageFactory, MethodologyRelatedPageFactory


class MethodologyPageTest(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = MethodologyPageFactory()
        cls.user = cls.create_superuser("admin")

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

        parent_page = self.page.get_parent()

        add_sibling_url = reverse("wagtailadmin_pages:add", args=["methodology", "methodologypage", parent_page.id])

        response = self.client.get(add_sibling_url, follow=True)

        content = response.content.decode(encoding="utf-8")

        date_placeholder = "YYYY-MM-DD"

        self.assertInHTML(
            (
                '<input type="text" name="publication_date" autocomplete="off"'
                f'placeholder="{date_placeholder}" required="" id="id_publication_date">'
            ),
            content,
        )

        self.assertInHTML(
            (
                '<input type="text" name="last_revised_date" autocomplete="off"'
                f'placeholder="{date_placeholder}" id="id_last_revised_date">'
            ),
            content,
        )
