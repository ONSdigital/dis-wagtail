from django.core.cache import caches
from django.test import SimpleTestCase, override_settings
from fakeredis import FakeConnection


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
        caches["default"].delete("key")

        self.assertIsNone(caches["default"].get("key"))
        self.assertIsNone(caches["invalidate_replay"].get("key"))

    def test_replays_delete_many(self) -> None:
        caches["default"].delete_many(["key"])

        self.assertIsNone(caches["default"].get("key"))
        self.assertIsNone(caches["invalidate_replay"].get("key"))

    def test_replays_clear(self) -> None:
        caches["default"].delete_many(["key"])

        self.assertIsNone(caches["default"].get("key"))
        self.assertIsNone(caches["invalidate_replay"].get("key"))
