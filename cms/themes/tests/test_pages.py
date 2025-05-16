from http import HTTPStatus

from django.urls import reverse
from wagtail.test.utils import WagtailPageTestCase

from cms.topics.tests.factories import ThemePageFactory


class ThemePageTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = ThemePageFactory()
        cls.superuser = cls.create_superuser(username="admin")

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    def test_default_route_is_renderable(self):
        self.assertPageIsRenderable(self.page)

    def test_default_route_rendering(self):
        response = self.client.get(self.page.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.page.title)
        self.assertContains(response, self.page.summary)

    def test_copy_is_not_allowed(self):
        """Test that copying a ThemePage raises a warning."""
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.client.get(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response,
            "Topic and theme pages cannot be duplicated as selected taxonomy needs to be unique for each page.",
        )

        response = self.client.post(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.client.post(
            reverse("wagtailadmin_pages:copy", args=[self.page.id]),
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(
            response,
            "Topic and theme pages cannot be duplicated as selected taxonomy needs to be unique for each page.",
        )
