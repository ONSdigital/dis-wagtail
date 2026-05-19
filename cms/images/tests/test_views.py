from http import HTTPStatus

from django.urls import reverse
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.test.utils import WagtailPageTestCase


class ImageDownloadViewTests(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        image_model = get_image_model()
        cls.image = image_model.objects.create(
            title="My chart image",
            file=get_test_image_file(),
            description="Alt text",
        )
        cls.rendition = cls.image.get_rendition("width-2048")

    def test_returns_404_for_nonexistent_rendition(self):
        url = reverse("image_download", args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_content_disposition_filename(self):
        url = reverse("image_download", args=[self.rendition.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content_disposition = response.get("Content-Disposition", "")
        self.assertIn("attachment", content_disposition)
        self.assertIn("My chart image", content_disposition)
