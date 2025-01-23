from django.db import DEFAULT_DB_ALIAS
from django.test import override_settings
from wagtail.coreutils import get_dummy_request
from wagtail.models import Site

from cms.core.models.settings import SocialMediaSettings
from cms.core.tests import TransactionTestCase


class SiteSettingsTestCase(TransactionTestCase):
    """Tests for site settings, and how they behaves with multiple databases."""

    def setUp(self):
        self.request = get_dummy_request()

        # Pre-warm site cache to avoid queries
        self.site = Site.find_for_request(self.request)

    def test_none_site(self):
        """Test getting settings for a site which is None."""
        with self.assertRaises(SocialMediaSettings.DoesNotExist):
            SocialMediaSettings.for_site(None)

    def test_create_setting(self):
        """Test creating a setting."""
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

        with self.assertNumQueriesConnection(default=4, replica=1):
            SocialMediaSettings.for_request(self.request)

        # Explicitly use default connection to work around strange issue with Django
        self.assertTrue(SocialMediaSettings.objects.using(DEFAULT_DB_ALIAS).exists())

        with self.assertNumQueriesConnection(default=0, replica=0):
            # This load is cached on the Site
            SocialMediaSettings.for_request(self.request)

    def test_use_existing_instance(self):
        """Test fetching a setting uses the existing instance."""
        setting = SocialMediaSettings.objects.create(site=self.site)

        with self.assertNumQueriesConnection(replica=1):
            setting_for_request = SocialMediaSettings.for_request(self.request)

        self.assertEqual(setting_for_request, setting)
        self.assertEqual(SocialMediaSettings.objects.count(), 1)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env_doesnt_create_instance(self):
        """Test that a setting isn't created in an external env."""
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

        with self.assertTotalNumQueries(1):
            setting = SocialMediaSettings.for_request(self.request)

        self.assertIsNone(setting.pk)
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

    def test_external_env_with_existing_instance(self):
        """Test loading an existing setting in an external env."""
        SocialMediaSettings.objects.create(site=self.site)

        with override_settings(IS_EXTERNAL_ENV=True), self.assertTotalNumQueries(1):
            setting = SocialMediaSettings.for_request(self.request)

        self.assertIsNotNone(setting.pk)

        self.assertTrue(SocialMediaSettings.objects.exists())
