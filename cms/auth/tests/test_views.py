from unittest import mock

from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware import csrf
from django.middleware.csrf import CsrfViewMiddleware
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils

from cms.auth.views import ONSLogoutView, extend_session


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

        # cookies present in response but expired deletion marker
        for name in ("access", "id"):
            morsel = res.cookies.get(name)
            self.assertIsNotNone(morsel)
            self.assertEqual(morsel.value, "")
            self.assertEqual(int(morsel["max-age"]), 0)

        # storage was used iterator exhausted during the view
        self.assertTrue(storage.used)

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False, LOGOUT_REDIRECT_URL="/")
    def test_cookies_not_deleted_when_flag_off(self):
        url = reverse("wagtailadmin_logout")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(response.cookies.get("access"))
        self.assertIsNone(response.cookies.get("id"))


@override_settings(ROOT_URLCONF="cms.urls")
class ExtendSessionTests(WagtailTestUtils, TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.superuser = self.create_superuser(username="admin")
        self.client.force_login(self.superuser)

    def _make_request(self):
        """Build a POST /extend-session/ request that passes CSRF and auth
        without depending on urlconf import order.
        """
        rf = RequestFactory()
        token = csrf._get_new_csrf_string()  # pylint: disable=protected-access
        request = rf.post(
            "/admin/extend-session/",
            HTTP_X_CSRFTOKEN=token,
        )
        # attach session
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()

        # attach CSRF cookie
        request.COOKIES["csrftoken"] = token
        CsrfViewMiddleware(lambda r: None).process_view(request, extend_session, (), {})

        # authenticated super-user
        request.user = self.superuser
        return request, token

    def test_post_extends_session(self):
        request, _ = self._make_request()

        response = extend_session(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"status": "success", "message": "Session extended."},
        )
        # the session expiry should now be non-zero
        self.assertTrue(request.session.get_expiry_age() > 0)

    def test_get_not_allowed(self):
        rf = RequestFactory()
        request = rf.get("/admin/extend-session/")

        # attach a live session
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()

        # authenticated super-user
        request.user = self.superuser

        # call the view directly
        response = extend_session(request)

        self.assertEqual(response.status_code, 405)

    def test_post_as_anonymous_redirects_to_login(self):
        """Anonymous POST should be bounced by @login_required and
        redirected to the Wagtail login page (302).
        """
        self.client.logout()  # make the client anonymous
        url = reverse("extend_session")

        token = csrf._get_new_csrf_string()  # pylint: disable=protected-access
        self.client.cookies["csrftoken"] = token

        res = self.client.post(url, HTTP_X_CSRFTOKEN=token, follow=False)

        # login_required returns 302 to LOGIN_URL / WAGTAILADMIN_LOGIN_URL
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.url)
