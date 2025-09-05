from django.test import RequestFactory, TestCase

from cms.core.middleware import NonTrailingSlashRedirectMiddleware


class TestNonTrailingSlashRedirectMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = NonTrailingSlashRedirectMiddleware(lambda req: None)

    def test_redirects_trailing_slash(self):
        """Test that URLs with trailing slash are redirected to non-trailing slash."""
        request = self.factory.get("/some-page/")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/some-page")

    def test_preserves_query_string(self):
        """Test that query parameters are preserved during redirection."""
        request = self.factory.get("/some-page/?foo=bar")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/some-page?foo=bar")

    def test_preserves_complex_query_string(self):
        """Test that complex query strings with multiple parameters are preserved."""
        request = self.factory.get("/some-page/?foo=bar&baz=qux&test=value")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 301)
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
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/section/subsection/page")

    def test_nested_paths_with_query_string(self):
        """Test that nested paths with trailing slash and query string are handled correctly."""
        request = self.factory.get("/section/subsection/page/?param=value")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/section/subsection/page?param=value")

    def test_empty_query_string_not_added(self):
        """Test that empty query strings don't result in a trailing question mark."""
        # Simulate request with empty query string
        request = self.factory.get("/some-page/")
        request.META["QUERY_STRING"] = ""
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 301)
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
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/special-chars_%C3%A9_%C3%A1")

    def test_multiple_trailing_slashes(self):
        """Test that multiple trailing slashes are handled correctly."""
        request = self.factory.get("/some-page///")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "/some-page")

    def test_different_http_methods(self):
        """Test that the middleware works with different HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for method in methods:
            with self.subTest(method=method):
                request = getattr(self.factory, method.lower())("/test-page/")
                response = self.middleware.process_request(request)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response.url, "/test-page")

    def test_canonical_url_route_joining(self):
        """Test that canonical URLs properly join routes without double slashes."""
        # This test simulates the edge case handled in get_canonical_url
        # where a route needs to be joined to the base URL
        request = self.factory.get("/page/subpath/")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 301)
        # Should redirect to non-trailing slash version
        self.assertEqual(response.url, "/page/subpath")
