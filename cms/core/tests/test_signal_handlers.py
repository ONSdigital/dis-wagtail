from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from wagtail.models import Locale, Page

from cms.core.signal_handlers import sync_alias_translation_slugs
from cms.core.templatetags.page_config_tags import get_page_config_cache_key
from cms.home.models import HomePage
from cms.standard_pages.tests.factories import IndexPageFactory


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

        self.site = self.page.get_site()

        # Warm the cache
        self.client.get(self.page.get_url())

    def _cache_keys_for_page(self, page: Page) -> list[str]:
        return [get_page_config_cache_key(self.site, page, language_code) for language_code in dict(settings.LANGUAGES)]

    def tearDown(self):
        cache.clear()

    def test_stable_cache_key(self):
        with self.assertNumQueries(0):
            self.assertEqual(self._cache_keys_for_page(self.page), self._cache_keys_for_page(self.page))

    def test_invalidate_on_publish(self):
        self.assertNotEqual(cache.get_many(self._cache_keys_for_page(self.page)), {})

        # Publish a change
        self.page.save_revision().publish()
        self.page.refresh_from_db()

        self.assertEqual(cache.get_many(self._cache_keys_for_page(self.page)), {})

    def test_invalidate_on_unpublish(self):
        self.assertNotEqual(cache.get_many(self._cache_keys_for_page(self.page)), {})

        # Unpublish the revision
        self.page.unpublish()

        self.assertEqual(cache.get_many(self._cache_keys_for_page(self.page)), {})


class SyncAliasTranslationSlugsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cy_locale = Locale.objects.get(language_code="cy")
        cls.cy_home = HomePage.objects.get(locale=cls.cy_locale)

    def setUp(self):
        self.en_page = IndexPageFactory()
        self.cy_alias = self.en_page.create_alias(
            parent=self.cy_home,
            update_locale=self.cy_locale,
            reset_translation_key=False,
        )

    def test_syncs_slug_for_aliased_translation_with_different_slug(self):
        self.cy_alias.slug = "different-slug"
        self.cy_alias.save(update_fields=["slug"])

        sync_alias_translation_slugs(None, instance=self.en_page)

        self.cy_alias.refresh_from_db()
        self.assertEqual(self.cy_alias.slug, self.en_page.slug)

    def test_does_not_modify_alias_when_slug_already_matches(self):
        self.cy_alias.slug = self.en_page.slug
        self.cy_alias.save(update_fields=["slug"])

        with patch.object(Page, "save") as mock_save:
            sync_alias_translation_slugs(None, instance=self.en_page)

        mock_save.assert_not_called()

    def test_skips_for_non_default_locale_page(self):
        with patch.object(Page, "save") as mock_save:
            sync_alias_translation_slugs(None, instance=self.cy_alias)

        mock_save.assert_not_called()

    def test_proper_translation_slug_is_not_synced(self):
        self.cy_alias.alias_of = None
        self.cy_alias.slug = "different-slug"
        self.cy_alias.save(update_fields=["alias_of", "slug"])

        with patch.object(Page, "save") as mock_save:
            sync_alias_translation_slugs(None, instance=self.en_page)

        mock_save.assert_not_called()


class SyncAliasTranslationSlugsOnSlugChangeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cy_locale = Locale.objects.get(language_code="cy")
        cls.cy_home = HomePage.objects.get(locale=cls.cy_locale)

    def setUp(self):
        self.en_page = IndexPageFactory()
        self.cy_alias = self.en_page.create_alias(
            parent=self.cy_home,
            update_locale=self.cy_locale,
            reset_translation_key=False,
        )

    def test_slug_synced_on_slug_change(self):
        self.cy_alias.slug = "different-slug"
        self.cy_alias.save(update_fields=["slug"])

        new_slug = "new-en-slug"
        self.en_page.slug = new_slug
        with self.captureOnCommitCallbacks(execute=True):
            self.en_page.save_revision().publish()

        self.cy_alias.refresh_from_db()
        self.assertNotEqual(self.cy_alias.slug, "different-slug")
        self.assertEqual(self.cy_alias.slug, new_slug)

    def test_root_level_page_slug_not_synced_on_slug_change(self):
        en_home = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
        cy_home = HomePage.objects.get(locale=self.cy_locale)
        original_cy_slug = cy_home.slug

        en_home.slug = "new-home-slug"
        with self.captureOnCommitCallbacks(execute=True):
            en_home.save_revision().publish()

        cy_home.refresh_from_db()
        self.assertEqual(cy_home.slug, original_cy_slug)

    def test_alias_url_path_gets_updated_on_slug_change(self):
        self.cy_alias.slug = "different-slug"
        # Save to ensure url_path is updated to match the slug before publish
        # so we can confirm it gets changed after publish.
        self.cy_alias.save()
        self.cy_alias.refresh_from_db()
        original_url_path = self.cy_alias.url_path

        # Change en_page's slug and publish
        self.en_page.slug = "new-en-slug"
        with self.captureOnCommitCallbacks(execute=True):
            self.en_page.save_revision().publish()

        # URL path should be updated to match the new slug
        self.cy_alias.refresh_from_db()
        self.assertNotEqual(self.cy_alias.url_path, original_url_path)

    def test_alias_slug_sync_does_not_cause_further_saves(self):
        """page_slug_changed fires for the alias too (its slug changed), but the handler
        must not save any further pages when re-invoked for the alias.
        """
        self.cy_alias.slug = "different-slug"
        self.cy_alias.save(update_fields=["slug"])

        self.en_page.slug = "new-en-slug"
        save_calls = []
        original_save = Page.save

        def tracking_save(instance, *args, **kwargs):
            save_calls.append(instance.pk)
            return original_save(instance, *args, **kwargs)

        with patch.object(Page, "save", tracking_save), self.captureOnCommitCallbacks(execute=True):
            self.en_page.save_revision().publish()

        # Exactly 2 saves are expected for the alias:
        # 1. Wagtail's update_aliases (content sync during publish)
        # 2. Our handler's translation.save() (slug sync)
        alias_save_count = save_calls.count(self.cy_alias.pk)
        self.assertEqual(alias_save_count, 2)

        save_calls = []

        with patch.object(Page, "save", tracking_save), self.captureOnCommitCallbacks(execute=True):
            self.en_page.save_revision().publish()

        # No further saves should occur for the alias on subsequent publish since the slug is already in sync
        # (just the update_aliases save, no handler-triggered saves)
        alias_save_count = save_calls.count(self.cy_alias.pk)
        self.assertEqual(alias_save_count, 1)
