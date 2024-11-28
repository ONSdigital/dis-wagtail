from django.test import TestCase, override_settings
from django.utils.connection import ConnectionDoesNotExist
from wagtail.images import get_image_model
from wagtail_factories import ImageFactory


@override_settings(IS_EXTERNAL_ENV=True)
class ReadOnlyConnectionTestCase(TestCase):
    databases = "__all__"

    def test_cannot_write_to_disallowed_table(self):
        Image = get_image_model()

        self.assertFalse(Image.objects.exists())

        with self.assertRaises(ConnectionDoesNotExist):
            ImageFactory.create()

        self.assertFalse(Image.objects.exists())

    def test_can_write_to_allowed_table(self):
        with override_settings(IS_EXTERNAL_ENV=False):
            image = ImageFactory.create()

        rendition = image.get_rendition("width-100")

        # Confirm instance exists in DB
        rendition.refresh_from_db()
