from django.db import DEFAULT_DB_ALIAS, router
from django.test import TestCase, override_settings
from django.utils.connection import ConnectionDoesNotExist
from wagtail_factories import ImageFactory

from cms.core.db_router import ExternalEnvRouter
from cms.images.models import CustomImage, Rendition


@override_settings(IS_EXTERNAL_ENV=True)
class ReadOnlyConnectionTestCase(TestCase):
    def test_cannot_write_to_disallowed_table(self):
        """Test that disallowed models cannot be written to in external env."""
        self.assertFalse(CustomImage.objects.exists())

        with self.assertRaises(ConnectionDoesNotExist):
            ImageFactory.create()

        self.assertFalse(CustomImage.objects.exists())

    def test_can_write_to_allowed_table(self):
        """Test that allowed models can be written to in external env."""
        self.assertEqual(Rendition.objects.count(), 0)

        with override_settings(IS_EXTERNAL_ENV=False):
            image = ImageFactory.create()

        rendition = image.get_rendition("width-100")

        # Confirm instance exists in DB
        rendition.refresh_from_db()

        self.assertEqual(Rendition.objects.count(), 1)

    def test_uses_correct_connection(self):
        """Test that the correct connection is used."""
        self.assertEqual(router.db_for_read(CustomImage), DEFAULT_DB_ALIAS)  # TestCase runs in a transaction
        self.assertEqual(router.db_for_write(CustomImage), ExternalEnvRouter.FAKE_BACKEND)
