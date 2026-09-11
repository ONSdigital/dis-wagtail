from unittest import mock
from wsgiref.headers import Headers

from django.test import SimpleTestCase

from cms.core.whitenoise import CMSWhiteNoiseMiddleware


class WhiteNoiseForeverCacheHeaderTestCase(SimpleTestCase):
    """Test that immutable static files are cached using the FOREVER duration, and that
    changing FOREVER propagates to the Cache-Control header whitenoise sets.
    """

    def _get_cache_control(self) -> str:
        # Skip __init__, which scans the filesystem for static files - irrelevant here.
        middleware = CMSWhiteNoiseMiddleware.__new__(CMSWhiteNoiseMiddleware)
        headers = Headers([])

        with mock.patch.object(middleware, "immutable_file_test", return_value=True):
            middleware.add_cache_headers(headers, "css/app.abc123.css", "/static/css/app.abc123.css")

        return headers["Cache-Control"]

    def test_immutable_files_cached_for_default_forever_value(self) -> None:
        self.assertEqual(
            self._get_cache_control(),
            f"max-age={CMSWhiteNoiseMiddleware.FOREVER}, public, immutable",
        )

    def test_changing_forever_propagates_to_cache_control_header(self) -> None:
        with mock.patch.object(CMSWhiteNoiseMiddleware, "FOREVER", 123):
            self.assertEqual(self._get_cache_control(), "max-age=123, public, immutable")
