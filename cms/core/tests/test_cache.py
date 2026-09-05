from http import HTTPStatus

from django.core.cache import caches
from django.test import SimpleTestCase, TestCase, override_settings
from fakeredis import FakeConnection

from cms.home.models import HomePage


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "cms.core.cache.InvalidateReplayRedisCache",
            "LOCATION": "redis://default",
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
            },
        },
        "invalidate_replay": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://invalidate_replay",
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
            },
        },
    },
)
class InvalidateReplayRedisCacheTestCase(SimpleTestCase):
    def setUp(self) -> None:
        caches["default"].set("key", "value")
        caches["invalidate_replay"].set("key", "value")

    def test_doesnt_replay_set(self) -> None:
        caches["default"].set("key2", "value2")
        self.assertEqual(caches["default"].get("key2"), "value2")
        self.assertEqual(caches["invalidate_replay"].get("key"), "value")
        self.assertIsNone(caches["invalidate_replay"].get("key2"))

    def test_replays_delete(self) -> None:
        result = caches["default"].delete("key")

        self.assertTrue(result)

        self.assertIsNone(caches["default"].get("key"))
        self.assertIsNone(caches["invalidate_replay"].get("key"))

    def test_replays_delete_many(self) -> None:
        caches["default"].delete_many(["key"])

        self.assertIsNone(caches["default"].get("key"))
        self.assertIsNone(caches["invalidate_replay"].get("key"))

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "cms.core.cache.InvalidateReplayRedisCache",
                "LOCATION": "redis://default/0",
                "OPTIONS": {
                    "CONNECTION_POOL_KWARGS": {"connection_class": FakeConnection},
                },
            },
            "invalidate_replay": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": "redis://invalidate_replay/0",
            },
        },
    )
    def test_fail_to_replay_with_log(self) -> None:
        with self.assertLogs("cms.core.cache", "ERROR") as delete_logs:
            result = caches["default"].delete("key")
        self.assertFalse(result)
        self.assertEqual(delete_logs.records[0].message, "Unable to replay delete")

        with self.assertLogs("cms.core.cache", "ERROR") as delete_many_logs:
            caches["default"].delete_many(["key"])
        self.assertEqual(delete_many_logs.records[0].message, "Unable to replay delete_many")

        self.assertIsNone(caches["default"].get("key"))

    def test_delete_many_generator(self):
        def key_generator():
            yield "key"

        caches["default"].delete_many(key_generator())

        self.assertIsNone(caches["default"].get("key"))
        self.assertIsNone(caches["invalidate_replay"].get("key"))


class PageCacheControlHeadersTestCase(TestCase):
    """Test the Cache-Control and Cloudflare-CDN-Cache-Control headers set on page responses."""

    cdn_cache_control = "max-age=31536000, stale-while-revalidate=86400, stale-if-error=432000"

    def test_default_semi_static_page(self) -> None:
        home_page = HomePage.objects.first()

        response = self.client.get(home_page.get_url())

        self.assertEqual(
            response.headers["Cache-Control"],
            "public, max-age=60, stale-while-revalidate=0, stale-if-error=300",
        )
        self.assertEqual(response.headers["Cloudflare-CDN-Cache-Control"], self.cdn_cache_control)

    def test_welsh_home_page_headers_with_subdomain(self) -> None:
        response = self.client.get("/", headers={"host": "cy.ons.localhost"})

        self.assertEqual(
            response.headers["Cache-Control"],
            "public, max-age=60, stale-while-revalidate=0, stale-if-error=300",
        )
        self.assertEqual(response.headers["Cloudflare-CDN-Cache-Control"], self.cdn_cache_control)

    @override_settings(CMS_USE_SUBDOMAIN_LOCALES=False)
    def test_welsh_home_page_with_path_based_routing(self) -> None:
        response = self.client.get("/cy")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(
            response.headers["Cache-Control"],
            "public, max-age=60, stale-while-revalidate=0, stale-if-error=300",
        )
        self.assertEqual(response.headers["Cloudflare-CDN-Cache-Control"], self.cdn_cache_control)
