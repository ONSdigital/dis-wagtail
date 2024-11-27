from django.test import override_settings
from wagtail.coreutils import get_dummy_request
from wagtail.models import Site

from cms.core.models.settings import SocialMediaSettings
from cms.core.tests import TransactionTestCase


class SocialSettingsTestCase(TransactionTestCase):
    """Tests for the ContactDetails model."""

    def setUp(self):
        self.request = get_dummy_request()

    def test_none_site(self):
        with self.assertRaises(SocialMediaSettings.DoesNotExist):
            SocialMediaSettings.for_site(None)

    def test_create_setting(self):
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

        with self.assertTotalNumQueries(5):
            setting = SocialMediaSettings.for_request(self.request)

        self.assertIsNotNone(setting.pk)

        self.assertEqual(SocialMediaSettings.objects.count(), 1)

        with self.assertTotalNumQueries(0):
            SocialMediaSettings.for_request(self.request)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env_doesnt_create_instance(self):
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

        with self.assertTotalNumQueries(2), self.assertNumWriteQueries(0):
            setting = SocialMediaSettings.for_request(self.request)

        self.assertIsNone(setting.pk)
        self.assertEqual(SocialMediaSettings.objects.count(), 0)

    @override_settings(IS_EXTERNAL_ENV=True)
    def test_external_env_with_existing_instance(self):
        SocialMediaSettings.objects.create(site=Site.find_for_request(self.request))

        with self.assertTotalNumQueries(1), self.assertNumWriteQueries(0):
            setting = SocialMediaSettings.for_request(self.request)

        self.assertIsNotNone(setting.pk)
