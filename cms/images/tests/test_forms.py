from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from wagtail.images import get_image_model
from wagtail.images.forms import get_image_form
from wagtail.images.tests.utils import get_test_image_file


class CustomImageFormTests(TestCase):
    def test_description_field_is_relabelled_and_required(self):
        image = get_image_model()
        form_class = get_image_form(image)

        form = form_class()

        self.assertIn("description", form.fields)
        self.assertEqual(form.fields["description"].label, "Alternative text")
        self.assertTrue(form.fields["description"].required)

        self.assertIn("title", form.fields)
        self.assertEqual(
            form.fields["title"].help_text,
            "The title field will be used as the file name when the image is downloaded.",
        )

    @patch.object(Image, "MAX_IMAGE_PIXELS", 1)
    def test_decompression_bomb(self):
        image = get_image_model()
        form_class = get_image_form(image)

        form = form_class(
            data={
                "title": "Test image",
                "description": "test",
            },
            files={"file": SimpleUploadedFile("test.png", get_test_image_file().file.getvalue())},
        )

        self.assertFormError(form, "file", "This file has too many pixels (unknown number). Maximum pixels 10000000.")
