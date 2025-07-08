from http import HTTPStatus

from django.test.utils import override_settings
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

    @override_settings(IS_EXTERNAL_ENV=False, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True, AWS_COGNITO_LOGIN_ENABLED=True)
    def test_both_login_buttons_are_displayed(self):
        response = self.client.get("/")
        self.assertContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertContains(response, "Wagtail Core Default Login")
        self.assertContains(response, 'href="/admin/login"')
        self.assertContains(response, "Florence Login")
        self.assertContains(response, 'href="/admin/"')

    @override_settings(IS_EXTERNAL_ENV=False, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True, AWS_COGNITO_LOGIN_ENABLED=False)
    def test_only_core_login_button_is_displayed(self):
        response = self.client.get("/")
        self.assertContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertContains(response, "Wagtail Core Default Login")
        self.assertContains(response, 'href="/admin/login"')
        self.assertNotContains(response, "Florence Login")

    @override_settings(IS_EXTERNAL_ENV=False, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False, AWS_COGNITO_LOGIN_ENABLED=True)
    def test_only_cognito_login_button_is_displayed(self):
        response = self.client.get("/")
        self.assertContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertContains(response, "Florence Login")
        self.assertContains(response, 'href="/admin/"')
        self.assertNotContains(response, "Wagtail Core Default Login")

    @override_settings(IS_EXTERNAL_ENV=True, WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True, AWS_COGNITO_LOGIN_ENABLED=True)
    def test_no_buttons_in_external_environment(self):
        response = self.client.get("/")
        # The prompt and buttons should be omitted entirely
        self.assertNotContains(response, "To access the administrative interface, please use the following option(s):")
        self.assertNotContains(response, "Wagtail Core Default Login")
        self.assertNotContains(response, "Florence Login")
