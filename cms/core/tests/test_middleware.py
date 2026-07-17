from unittest.mock import Mock

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from cms.core.middleware import CloudflareWagtailCacheTagMiddleware, NonTrailingSlashRedirectMiddleware


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


class TestCloudflareWagtailCacheTagMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CloudflareWagtailCacheTagMiddleware(lambda req: None)

    def make_wagtail_request(self, path: str = "/test-page/"):
        request = self.factory.get(path)
        request.resolver_match = Mock(
            func=Mock(__module__="wagtail.core.views.serve"),
            view_name="wagtail_serve",
        )
        return request

    def make_non_wagtail_request(self, path: str = "/test-page/"):
        request = self.factory.get(path)
        request.resolver_match = Mock(
            func=Mock(__module__="cms.search.views"),
            view_name="resources-list",
        )
        return request

    def make_custom_homepage_request(self):
        request = self.factory.get("/cy")
        request.resolver_match = Mock(
            func=Mock(__module__="cms.home.views"),
            view_name="localied_homepage",
        )
        return request

    def test_adds_default_cache_tag_to_wagtail_route(self):
        """Wagtail routes should get the default cache tag."""
        request = self.make_wagtail_request()
        response = self.middleware.process_response(request, HttpResponse("Test content"))
        self.assertEqual(response.get("Cache-Tag"), "wagtail")

    @override_settings(WAGTAIL_CLOUDFLARE_CACHE_TAG="custom-tag")
    def test_uses_custom_cache_tag_when_configured(self):
        """Custom tag values should replace the default."""
        request = self.make_wagtail_request()
        response = self.middleware.process_response(request, HttpResponse("Test content"))
        self.assertEqual(response.get("Cache-Tag"), "custom-tag")

    @override_settings(WAGTAIL_CLOUDFLARE_CACHE_TAG="")
    def test_does_not_add_header_when_cache_tag_is_empty(self):
        """Empty cache tag configuration should skip tagging."""
        request = self.make_wagtail_request()
        response = self.middleware.process_response(request, HttpResponse("Test content"))
        self.assertNotIn("Cache-Tag", response)

    def test_does_not_tag_non_wagtail_routes(self):
        """Non-Wagtail routes must not receive a cache tag."""
        request = self.make_non_wagtail_request()
        response = self.middleware.process_response(request, HttpResponse("Test content"))
        self.assertNotIn("Cache-Tag", response)

    def test_appends_tag_to_existing_header(self):
        """Existing Cache-Tag headers should be appended to, not replaced."""
        request = self.make_wagtail_request()
        response = HttpResponse("Test content")
        response["Cache-Tag"] = "existing-tag"
        result = self.middleware.process_response(request, response)
        self.assertEqual(result.get("Cache-Tag"), "existing-tag, wagtail")

    def test_does_not_duplicate_existing_tag(self):
        """If the configured tag already exists, it should not be added again."""
        request = self.make_wagtail_request()
        response = HttpResponse("Test content")
        response["Cache-Tag"] = "wagtail"
        result = self.middleware.process_response(request, response)
        self.assertEqual(result.get("Cache-Tag"), "wagtail")

    def test_does_not_tag_unsuccessful_responses(self):
        """Responses with error status codes should not be tagged."""
        for status_code in [400, 404, 500]:
            with self.subTest(status_code=status_code):
                request = self.make_wagtail_request()
                response = HttpResponse("Test content", status=status_code)
                result = self.middleware.process_response(request, response)
                self.assertNotIn("Cache-Tag", result)
                self.assertEqual(result.status_code, status_code)

    def test_preserves_other_response_headers(self):
        """Middleware should preserve existing response headers."""
        request = self.make_wagtail_request()
        response = HttpResponse("Test content")
        response["Content-Type"] = "application/json"
        result = self.middleware.process_response(request, response)
        self.assertEqual(result["Content-Type"], "application/json")
        self.assertEqual(result.get("Cache-Tag"), "wagtail")
