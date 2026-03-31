from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings

from cms.core.templatetags.page_config_tags import get_page_config_cache_key
from cms.home.models import HomePage


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "InvalidatePageConfigCacheSignalTestCase",
        }
    }
)
class InvalidatePageConfigCacheSignalTestCase(TestCase):
    def setUp(self):
        self.page: HomePage = HomePage.objects.first()

        self.cache_keys = [
            get_page_config_cache_key(self.page.get_site(), self.page, language_code)
            for language_code in dict(settings.LANGUAGES)
        ]

        # Warm the cache
        self.client.get(self.page.get_url())

    def tearDown(self):
        cache.clear()

    def test_invalidate_on_publish(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        # Publish a change
        self.page.save_revision().publish()

        self.assertEqual(cache.get_many(self.cache_keys), {})

    def test_invalidate_on_unpublish(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        # Unpublish the revision
        self.page.unpublish()

        self.assertEqual(cache.get_many(self.cache_keys), {})
