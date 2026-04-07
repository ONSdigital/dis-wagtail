from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from wagtail.models import Locale, Page

from cms.core.signal_handlers import sync_alias_translation_slugs
from cms.home.models import HomePage
from cms.standard_pages.tests.factories import IndexPageFactory


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
