from unittest import mock

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware import csrf
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.auth.views import ONSLogoutView


class ONSLogoutViewTests(TestCase, WagtailTestUtils):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

    def setUp(self):
        self.factory = RequestFactory()
        self.client.force_login(self.superuser)

    # Helper attach a working session and message storage
    def _prep_request(self, req):
        # give the request a session
        SessionMiddleware(lambda r: None).process_request(req)
        req.session.save()

        # attach a real FallbackStorage
        storage = FallbackStorage(req)
        req._messages = storage  # pylint: disable=protected-access
        return storage

    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        ACCESS_TOKEN_COOKIE_NAME="access",
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_cookies_deleted_and_messages_cleared(self):
        req = self.factory.get("/logout/")
        req.user = mock.Mock(is_authenticated=True)
        req.COOKIES = {"access": "123", "id": "456"}

        storage = self._prep_request(req)

        # seed with a dummy message
        messages.add_message(req, messages.INFO, "dummy")

        res = ONSLogoutView.as_view()(req)

        # cookies present in response but expired (deletion marker)
        for name in ("access", "id"):
            morsel = res.cookies.get(name)
            self.assertIsNotNone(morsel)
            self.assertEqual(morsel.value, "")
            self.assertEqual(int(morsel["max-age"]), 0)

        # storage was used (iterator exhausted) during the view
        self.assertTrue(storage.used)

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False, LOGOUT_REDIRECT_URL="/")
    def test_cookies_not_deleted_when_flag_off(self):
        url = reverse("wagtailadmin_logout")
        response = self.client.post(url)  # self.client is already logged in
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(response.cookies.get("access"))
        self.assertIsNone(response.cookies.get("id"))


@override_settings(ROOT_URLCONF="cms.urls")  # make sure project URLs are loaded
class ExtendSessionTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        # user login
        self.user = get_user_model().objects.create(username="u1")
        self.client.force_login(self.user)

    def test_post_extends_session(self):
        # canonical URL will be "/<admin-prefix>/extend-session/"
        url = reverse("extend_session")

        # create a brand-new token and add it to the cookie jar
        token = csrf._get_new_csrf_string()  # pylint: disable=protected-access
        self.client.cookies["csrftoken"] = token

        # POST and follow redirects
        res = self.client.post(url, follow=True, HTTP_X_CSRFTOKEN=token)

        # final response is the JSON payload from extend_session
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(res.content, {"status": "success", "message": "Session extended."})

        # session expiry refreshed
        self.assertTrue(self.client.session.get_expiry_age() > 0)

    def test_get_not_allowed(self):
        url = reverse("extend_session")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 405)
