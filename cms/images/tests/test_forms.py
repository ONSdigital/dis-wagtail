from django.test import TestCase
from wagtail.images import get_image_model
from wagtail.images.forms import get_image_form


class CustomImageFormTests(TestCase):
    def test_description_field_is_relabelled_and_required(self):
        image = get_image_model()
        form_class = get_image_form(image)

        form = form_class()

        self.assertIn("description", form.fields)
        self.assertEqual(form.fields["description"].label, "Alternative Text")
        self.assertTrue(form.fields["description"].required)

        self.assertIn("title", form.fields)
        self.assertEqual(
            form.fields["title"].help_text,
            "The title field will be used as the file name when the image is downloaded.",
        )
