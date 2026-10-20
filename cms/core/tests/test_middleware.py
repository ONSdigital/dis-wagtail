import uuid
from unittest import mock

from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.messages.storage.cookie import CookieStorage
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.admin.auth import permission_denied

from cms.core.middleware import (
    CloudflareWagtailCacheTagMiddleware,
    NonTrailingSlashRedirectMiddleware,
    UnauthorizedAccessLoggingMiddleware,
)
from cms.users.tests.factories import UserFactory


class TestNonTrailingSlashRedirectMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = NonTrailingSlashRedirectMiddleware(lambda req: None)

    def test_redirects_trailing_slash(self):
        """Test that URLs with trailing slash are redirected to non-trailing slash."""
        request = self.factory.get("/some-page/")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/some-page")

    def test_preserves_query_string(self):
        """Test that query parameters are preserved during redirection."""
        request = self.factory.get("/some-page/?foo=bar")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/some-page?foo=bar")

    def test_preserves_complex_query_string(self):
        """Test that complex query strings with multiple parameters are preserved."""
        request = self.factory.get("/some-page/?foo=bar&baz=qux&test=value")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/some-page?foo=bar&baz=qux&test=value")

    def test_ignores_root(self):
        """Test that the root URL is not redirected."""
        request = self.factory.get("/")
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_ignores_file_extensions(self):
        """Test that URLs with file extensions are not redirected."""
        test_cases = [
            "/static/style.css",
            "/images/logo.png",
            "/scripts/app.js",
            "/documents/report.pdf",
            "/data/export.json",
            "/assets/icon.svg",
        ]

        for url in test_cases:
            with self.subTest(url=url):
                request = self.factory.get(url)
                response = self.middleware.process_request(request)
                self.assertIsNone(response)

    def test_no_redirect_for_no_trailing_slash(self):
        """Test that URLs without trailing slash are not redirected."""
        request = self.factory.get("/some-page")
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_nested_paths_with_trailing_slash(self):
        """Test that nested paths with trailing slash are redirected correctly."""
        request = self.factory.get("/section/subsection/page/")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/section/subsection/page")

    def test_nested_paths_with_query_string(self):
        """Test that nested paths with trailing slash and query string are handled correctly."""
        request = self.factory.get("/section/subsection/page/?param=value")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/section/subsection/page?param=value")

    def test_empty_query_string_not_added(self):
        """Test that empty query strings don't result in a trailing question mark."""
        # Simulate request with empty query string
        request = self.factory.get("/some-page/")
        request.META["QUERY_STRING"] = ""
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/some-page")

    def test_file_extension_with_trailing_slash_not_redirected(self):
        """Test that files with extensions are not redirected even with trailing slash."""
        # This is an edge case - files with extensions followed by slash should be ignored
        request = self.factory.get("/file.txt/")
        response = self.middleware.process_request(request)
        # The middleware should detect the extension and not redirect
        self.assertIsNone(response)

    def test_special_characters_in_path(self):
        """Test that paths with special characters are handled correctly."""
        request = self.factory.get("/special-chars_%C3%A9_%C3%A1/")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/special-chars_%C3%A9_%C3%A1")

    def test_multiple_trailing_slashes(self):
        """Test that multiple trailing slashes are handled correctly."""
        request = self.factory.get("/some-page///")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.url, "/some-page")

    def test_different_http_methods(self):
        """Test that the middleware works with different HTTP methods."""
        affected_methods = ["GET", "HEAD"]
        unaffected_methods = ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

        for method in affected_methods:
            with self.subTest(method=method):
                request = getattr(self.factory, method.lower())("/test-page/")
                response = self.middleware.process_request(request)
                self.assertEqual(response.status_code, 308)
                self.assertEqual(response.url, "/test-page")

        for method in unaffected_methods:
            with self.subTest(method=method):
                request = getattr(self.factory, method.lower())("/test-page/")
                response = self.middleware.process_request(request)
                self.assertIsNone(response)

    def test_is_request_path_allowed(self):
        """Test the is_request_path_allowed method."""
        test_cases = [
            ("/admin/", True),
            ("/admin/some-page/", True),
            ("/django-admin/", True),
            ("/django-admin/some-page/", True),
            ("/__debug__/", True),
            ("/__debug__/some-page/", True),
            ("/some-other-path/", False),
            ("/another-path/some-page/", False),
        ]

        for path, expected in test_cases:
            with self.subTest(path=path):
                result = self.middleware.is_request_path_allowed(path)
                self.assertEqual(result, expected)


@override_settings(CMS_CLOUDFLARE_CACHE_TAG="wagtail")
class TestCloudflareWagtailCacheTagMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CloudflareWagtailCacheTagMiddleware(lambda req: None)

    def make_request(self, path: str = "/test-page/"):
        return self.factory.get(path)

    def test_adds_default_cache_tag_to_response(self):
        """Responses should get the default cache tag."""
        request = self.make_request()
        response = self.middleware.process_response(request, HttpResponse("Test content"))
        self.assertEqual(response.get("Cache-Tag"), "wagtail")

    @override_settings(CMS_CLOUDFLARE_CACHE_TAG="custom-tag")
    def test_uses_custom_cache_tag_when_configured(self):
        """Custom tag values should replace the default."""
        request = self.make_request()
        response = self.middleware.process_response(request, HttpResponse("Test content"))
        self.assertEqual(response.get("Cache-Tag"), "custom-tag")

    @override_settings(CMS_CLOUDFLARE_CACHE_TAG="")
    def test_does_not_add_header_when_cache_tag_is_empty(self):
        """Empty cache tag configuration should skip tagging."""
        request = self.make_request()
        response = self.middleware.process_response(request, HttpResponse("Test content"))
        self.assertNotIn("Cache-Tag", response)

    def test_appends_tag_to_existing_header(self):
        """Existing Cache-Tag headers should be appended to, not replaced."""
        request = self.make_request()
        response = HttpResponse("Test content")
        response["Cache-Tag"] = "existing-tag"
        result = self.middleware.process_response(request, response)
        self.assertEqual(result.get("Cache-Tag"), "existing-tag,wagtail")

    def test_does_not_duplicate_existing_tag(self):
        """If the configured tag already exists, it should not be added again."""
        request = self.make_request()
        response = HttpResponse("Test content")
        response["Cache-Tag"] = "wagtail"
        result = self.middleware.process_response(request, response)
        self.assertEqual(result.get("Cache-Tag"), "wagtail")

    def test_preserves_other_response_headers(self):
        """Middleware should preserve unrelated headers such as Content-Type."""
        request = self.make_request()
        response = HttpResponse("Test content")
        response["Content-Type"] = "application/json"
        result = self.middleware.process_response(request, response)
        self.assertEqual(result["Content-Type"], "application/json")
        self.assertEqual(result.get("Cache-Tag"), "wagtail")


class TestUnauthorizedAccessLoggingMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = UnauthorizedAccessLoggingMiddleware(lambda req: None)

    def process(self, request, response):
        self.middleware.process_request(request)
        with self.assertLogs("cms.security", level="WARNING") as logs:
            self.middleware.process_response(request, response)
        return logs.records[0]

    def assert_not_logged(self, request, response):
        self.middleware.process_request(request)
        with self.assertNoLogs("cms.security"):
            self.middleware.process_response(request, response)

    def test_logs_403_for_authenticated_user(self):
        user = UserFactory()
        request = self.factory.get("/admin/bundles/?a=1", HTTP_USER_AGENT="TestAgent", REMOTE_ADDR="10.0.0.1")
        request.user = user

        record = self.process(request, HttpResponse(status=403))

        self.assertEqual(record.getMessage(), "unauthorized access attempt")
        self.assertEqual(record.classification, "PROTECTIVE_MONITORING")
        self.assertEqual(record.auth, {"identity": str(user.pk), "identity_type": "user"})
        self.assertEqual(record.email, user.email)
        self.assertEqual(record.user_agent, "TestAgent")
        self.assertEqual(record.ip_address, "10.0.0.1")
        self.assertEqual(record.event_type, "unauthorized access attempt")
        self.assertEqual(record.http["method"], "GET")
        self.assertEqual(record.http["path"], "/admin/bundles/")
        self.assertEqual(record.http["query"], "a=1")
        self.assertEqual(record.http["status_code"], 403)
        self.assertEqual(record.http["scheme"], "http")
        self.assertEqual(record.http["port"], 80)
        self.assertIn("host", record.http)
        self.assertIsNotNone(record.http["started_at"])

    def test_logs_403_with_external_user_id(self):
        external_user_id = uuid.UUID(int=123)
        user = UserFactory(external_user_id=external_user_id)
        request = self.factory.get("/admin/bundles/?a=1", HTTP_USER_AGENT="TestAgent", REMOTE_ADDR="10.0.0.1")
        request.user = user

        record = self.process(request, HttpResponse(status=403))

        self.assertTrue(hasattr(record, "auth"))
        self.assertIn("external_user_id", record.auth)

        self.assertEqual(record.auth["external_user_id"], external_user_id)

    def test_logs_401_for_anonymous_user_without_auth(self):
        request = self.factory.get("/api/thing")
        request.user = AnonymousUser()

        record = self.process(request, HttpResponse(status=401))

        self.assertEqual(record.http["status_code"], 401)
        self.assertFalse(hasattr(record, "auth"))
        self.assertFalse(hasattr(record, "email"))

    def test_logs_403_without_user_on_request(self):
        record = self.process(self.factory.get("/anything"), HttpResponse(status=403))
        self.assertFalse(hasattr(record, "auth"))

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_omits_ip_address_in_external_env(self):
        request = self.factory.get("/anything")
        request.user = AnonymousUser()

        record = self.process(request, HttpResponse(status=403))

        self.assertFalse(hasattr(record, "ip_address"))

    def test_omits_port_when_port_is_invalid(self):
        for invalid_port in ("not-a-port", None, ""):
            with self.subTest(port=invalid_port):
                request = self.factory.get("/anything")
                request.user = AnonymousUser()

                with mock.patch.object(request, "get_port", return_value=invalid_port):
                    record = self.process(request, HttpResponse(status=403))

                self.assertEqual(record.http["status_code"], 403)
                self.assertNotIn("port", record.http)

    def test_host_value_fallback_sequence(self):
        request = self.factory.get("/anything", HTTP_HOST="example.com")
        request.user = AnonymousUser()

        record = self.process(request, HttpResponse(status=403))

        self.assertIn("host", record.http)
        self.assertEqual(record.http["host"], "example.com")

        request = self.factory.get("/anything", HTTP_HOST="example.com", SERVER_NAME="server.com")
        request.user = AnonymousUser()

        record = self.process(request, HttpResponse(status=403))

        self.assertIn("host", record.http)
        self.assertEqual(record.http["host"], "example.com")

        request = self.factory.get("/anything", SERVER_NAME="server.com")
        request.user = AnonymousUser()

        record = self.process(request, HttpResponse(status=403))

        self.assertIn("host", record.http)
        self.assertEqual(record.http["host"], "server.com")

    def test_event_type_depends_on_authentication(self):
        anonymous = self.factory.get("/x")
        anonymous.user = AnonymousUser()
        record = self.process(anonymous, HttpResponse(status=403))
        self.assertEqual(record.getMessage(), "unauthenticated access attempt")

        authenticated = self.factory.get("/x")
        authenticated.user = UserFactory()
        record = self.process(authenticated, HttpResponse(status=403))
        self.assertEqual(record.getMessage(), "unauthorized access attempt")

    def test_logs_anonymous_admin_redirect_to_login(self):
        request = self.factory.get("/admin/pages/")
        request.user = AnonymousUser()

        record = self.process(request, HttpResponseRedirect("/admin/login/?next=/admin/pages/"))

        self.assertEqual(record.http["status_code"], 302)
        self.assertEqual(record.http["path"], "/admin/pages/")

    def test_logs_authenticated_user_admin_redirect_to_login(self):
        user = UserFactory()
        request = self.factory.get("/admin/pages/")
        request.user = user

        record = self.process(request, HttpResponseRedirect("/admin/login/?next=/admin/pages/"))

        self.assertEqual(record.auth["identity"], str(user.pk))

    def test_ignores_redirect_outside_admin(self):
        request = self.factory.get("/some-page")
        request.user = AnonymousUser()
        self.assert_not_logged(request, HttpResponseRedirect("/admin/login/"))

    def test_logs_wagtail_permission_denied_redirect(self):
        user = UserFactory()
        request = self.factory.get("/admin/pages/")
        request.user = user
        request._messages = CookieStorage(request)  # pylint: disable=protected-access
        messages.error(request, "Sorry, you do not have permission to access this area.")

        record = self.process(request, HttpResponseRedirect("/admin/"))

        self.assertEqual(record.getMessage(), "unauthorized access attempt")
        self.assertEqual(record.auth["identity"], str(user.pk))

    def test_detects_real_wagtail_permission_denied_response(self):
        """Fails if Wagtail changes the permission denied message the middleware relies on."""
        request = self.factory.get("/admin/pages/")
        request.user = UserFactory()
        request._messages = CookieStorage(request)  # pylint: disable=protected-access

        response = permission_denied(request)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(UnauthorizedAccessLoggingMiddleware._is_denied(request, response))  # pylint: disable=protected-access

    def test_ignores_admin_home_redirect_without_permission_message(self):
        request = self.factory.get("/admin/pages/")
        request.user = UserFactory()
        request._messages = CookieStorage(request)  # pylint: disable=protected-access
        messages.error(request, "Something else went wrong.")
        self.assert_not_logged(request, HttpResponseRedirect("/admin/"))

    def test_ignores_admin_redirect_to_other_location(self):
        request = self.factory.get("/admin")
        request.user = AnonymousUser()
        self.assert_not_logged(request, HttpResponseRedirect("/admin/"))

    @override_settings(WAGTAILADMIN_HOME_PATH="admin")
    def test_ignores_redirect_on_path_sharing_admin_prefix(self):
        request = self.factory.get("/administrator/")
        request.user = AnonymousUser()
        self.assert_not_logged(request, HttpResponseRedirect("/admin/login/"))

    def test_ignores_login_page_redirect(self):
        for path in ("/admin/login/", "/admin/password_reset/"):
            with self.subTest(path=path):
                request = self.factory.get(path)
                request.user = AnonymousUser()
                self.assert_not_logged(request, HttpResponseRedirect("/admin/login/"))

    def test_ignores_successful_response(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        self.assert_not_logged(request, HttpResponse(status=200))

    def test_end_to_end_anonymous_admin_access(self):
        with self.assertLogs("cms.security", level="WARNING") as logs:
            response = self.client.get("/admin/pages/")

        self.assertEqual(response.status_code, 302)
        record = logs.records[0]
        self.assertEqual(record.getMessage(), "unauthenticated access attempt")

    def test_end_to_end_user_without_admin_access(self):
        user = UserFactory()
        self.client.force_login(user)
        with self.assertLogs("cms.security", level="WARNING") as logs:
            response = self.client.get("/admin/pages/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(logs.records[0].auth["identity"], str(user.pk))

    def test_end_to_end_forbidden_bundle_access(self):
        user = UserFactory()
        user.user_permissions.add(Permission.objects.get(codename="access_admin"))
        self.client.force_login(user)
        with self.assertLogs("cms.security", level="WARNING") as logs:
            response = self.client.get(reverse("bundle:add"), headers={"x-requested-with": "XMLHttpRequest"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(logs.records[0].event_type, "unauthorized access attempt")
