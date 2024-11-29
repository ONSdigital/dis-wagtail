from django.test import TestCase, override_settings
from django.utils.connection import ConnectionDoesNotExist
from wagtail.images import get_image_model
from wagtail_factories import ImageFactory


@override_settings(IS_EXTERNAL_ENV=True)
class ReadOnlyConnectionTestCase(TestCase):
    databases = "__all__"

    def test_cannot_write_to_disallowed_table(self):
        """Test that disallowed models cannot be written to in external env."""
        image_model = get_image_model()

        self.assertFalse(image_model.objects.exists())

        with self.assertRaises(ConnectionDoesNotExist):
            ImageFactory.create()

        self.assertFalse(image_model.objects.exists())

    def test_can_write_to_allowed_table(self):
        """Test that allowed models can be written to in external env."""
        self.assertEqual(get_image_model().get_rendition_model().objects.count(), 0)

        with override_settings(IS_EXTERNAL_ENV=False):
            image = ImageFactory.create()

        rendition = image.get_rendition("width-100")

        # Confirm instance exists in DB
        rendition.refresh_from_db()

        self.assertEqual(get_image_model().get_rendition_model().objects.count(), 1)
