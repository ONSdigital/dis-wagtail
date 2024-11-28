from django.test import override_settings
from wagtail.coreutils import get_dummy_request
from wagtail.models import Site

from cms.core.models.settings import SocialMediaSettings
from cms.core.tests import TransactionTestCase


class SocialSettingsTestCase(TransactionTestCase):
    """Tests for the SocialSettings model, and how it behaves with multiple databases."""

    def setUp(self):
        self.request = get_dummy_request()

    def test_none_site(self):
        with self.assertRaises(SocialMediaSettings.DoesNotExist):
            SocialMediaSettings.for_site(None)

    def test_create_setting(self):
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

        with self.assertNumQueriesConnection(default=4, replica=2):
            SocialMediaSettings.for_request(self.request)

        # Explicitly use default connection to work around strange issue with Django
        self.assertTrue(SocialMediaSettings.objects.using("default").exists())

        with self.assertNumQueriesConnection(default=0, replica=0):
            # This load is cached on the Site
            SocialMediaSettings.for_request(self.request)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env_doesnt_create_instance(self):
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

        with self.assertTotalNumQueries(2):
            setting = SocialMediaSettings.for_request(self.request)

        self.assertIsNone(setting.pk)
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

    def test_external_env_with_existing_instance(self):
        SocialMediaSettings.objects.create(site=Site.find_for_request(self.request))

        with override_settings(IS_EXTERNAL_ENV=True), self.assertTotalNumQueries(1):
            setting = SocialMediaSettings.for_request(self.request)

        self.assertIsNotNone(setting.pk)

        # Explicitly use default connection to work around strange issue with Django
        self.assertTrue(SocialMediaSettings.objects.using("default").exists())
