from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings

from cms.core.templatetags.page_config_tags import get_base_page_config_cache_key
from cms.home.models import HomePage

from .factories import NavigationSettingsFactory


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "InvalidateBaseConfigCacheSignalTestCase",
        }
    }
)
class InvalidateBaseConfigCacheSignalTestCase(TestCase):
    def setUp(self):
        homepage = HomePage.objects.first()

        self.navigation_settings = NavigationSettingsFactory(site=homepage.get_site())

        self.cache_keys = [
            get_base_page_config_cache_key(self.navigation_settings.site, language_code)
            for language_code in dict(settings.LANGUAGES)
        ]

        # Warm the cache
        self.client.get(homepage.get_url())

    def tearDown(self):
        cache.clear()

    def test_invalidate_on_settings_save(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        self.navigation_settings.save()

        self.assertEqual(cache.get_many(self.cache_keys), {})

    def test_invalidate_on_site_save(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        self.navigation_settings.site.save()

        self.assertEqual(cache.get_many(self.cache_keys), {})

    def test_invalidate_on_main_menu_publish(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        self.navigation_settings.main_menu.save_revision().publish()

        self.assertEqual(cache.get_many(self.cache_keys), {})

    def test_invalidate_on_footer_menu_publish(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        self.navigation_settings.footer_menu.save_revision().publish()

        self.assertEqual(cache.get_many(self.cache_keys), {})

    def test_invalidate_on_main_menu_unpublish(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        self.navigation_settings.main_menu.unpublish()

        self.assertEqual(cache.get_many(self.cache_keys), {})

    def test_invalidate_on_footer_menu_unpublish(self):
        self.assertNotEqual(cache.get_many(self.cache_keys), {})

        self.navigation_settings.footer_menu.unpublish()

        self.assertEqual(cache.get_many(self.cache_keys), {})
