from http import HTTPStatus

from wagtail.test.utils import WagtailPageTestCase


class HomePageTests(WagtailPageTestCase):
    def test_home_page_can_be_served(self):
        """Test that the home page can be served."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_home_page_template(self):
        response = self.client.get("/")
        self.assertContains(response, "This is a new service")
        self.assertContains(response, "All content is available under the")

    def test_welsh_home_page_can_be_served(self):
        response = self.client.get("/cy/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unsupported_language_home_page_is_not_found(self):
        response = self.client.get("/fr/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_welsh_home_page_template(self):
        response = self.client.get("/cy/")
        self.assertContains(response, "Mae'r holl gynnwys ar gael o dan delerau'r")
