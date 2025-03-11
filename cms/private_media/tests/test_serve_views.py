from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.images.models import Filter
from wagtail.models import Collection
from wagtail_factories import DocumentFactory, ImageFactory

from cms.private_media.constants import Privacy


class TestImageServeView(TestCase):
    model = get_image_model()

    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)
        cls.private_image = ImageFactory(collection=cls.root_collection)
        cls.public_image = ImageFactory(_privacy=Privacy.PUBLIC, collection=cls.root_collection)
        cls.private_image_renditions = tuple(
            cls.private_image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20")).values()
        )
        cls.public_image_renditions = tuple(
            cls.public_image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20")).values()
        )
        cls.superuser = get_user_model().objects.create(username="superuser", is_superuser=True)

    def setUp(self):
        # Clear potentially invalid 'serve_url' @cached_property values
        for rendition in self.private_image_renditions + self.public_image_renditions:
            rendition.__dict__.pop("serve_url", None)

    def test_serve_private_image(self):
        """Test the serve view behaviour for private image renditions."""
        # If not authenticated, permission checks should fail and a Forbidden response returned
        for rendition in self.private_image_renditions:
            for is_external_env in [True, False]:
                with self.subTest(rendition=rendition, is_external_env=is_external_env) and override_settings(
                    IS_EXTERNAL_ENV=is_external_env
                ):
                    response = self.client.get(rendition.serve_url)
                    self.assertEqual(response.status_code, 403)

        # If authenticated as a superuser, the view should serve the files
        self.client.force_login(self.superuser)
        for rendition in self.private_image_renditions:
            for is_external_env in [True, False]:
                with self.subTest(rendition=rendition, is_external_env=is_external_env) and override_settings(
                    IS_EXTERNAL_ENV=is_external_env
                ):
                    response = self.client.get(rendition.serve_url)
                    self.assertEqual(response.status_code, 200)

    def test_serve_public_image(self):
        """Test the serve view behaviour for public image renditions."""
        # For public image renditions, the serve view should redirect to the file path or URL.
        for rendition in self.public_image_renditions:
            for is_external_env in [True, False]:
                with self.subTest(rendition=rendition, is_external_env=is_external_env) and override_settings(
                    IS_EXTERNAL_ENV=is_external_env
                ):
                    response = self.client.get(rendition.serve_url)
                    self.assertEqual(response.status_code, 302)

    def test_serve_public_image_with_outdated_file_permissions(self):
        """Test the serve view behaviour for public image renditions with outdated file permissions."""
        self.model.objects.filter(id=self.public_image.id).update(file_permissions_last_set=None)
        self.public_image.refresh_from_db()
        self.assertTrue(self.public_image.has_outdated_file_permissions())
        for rendition in self.public_image_renditions:
            response = self.client.get(rendition.serve_url)
            self.assertEqual(response.status_code, 200)

    def test_serve_with_invalid_signature(self):
        """Test the serve view rejects requests when the signature is invalid."""
        rendition = self.private_image_renditions[0]

        # Generate an otherwise valid `serve_url` with an invalid signature
        with mock.patch("wagtail.images.views.serve.generate_signature", return_value="invalid-signature"):
            serve_url = rendition.serve_url

        # Test the view using the generated `serve_url`
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 400)

    def test_serve_with_invalid_image_id(self):
        """Test the serve view behaviour when the signature is valid but the image ID
        is not recognised.
        """
        rendition = self.public_image_renditions[0]
        original_image_id = self.public_image.id

        # Replace `image_id` value with an invalid one
        self.public_image.id = 9999999

        # Generate an otherwise valid `serve_url` with a reference to a non-existent image ID
        serve_url = rendition.serve_url

        # Undo change to `image_id` to avoid impacting other tests
        self.public_image.id = original_image_id

        # Test the view using the generated `serve_url`
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 404)

    def test_serve_with_invalid_filter_spec(self):
        """Test the serve view behaviour when the filter spec is invalid."""
        rendition = self.public_image_renditions[0]
        original_filter_spec = rendition.filter_spec

        # Replace `filter_spec`` value with an invalid one
        rendition.filter_spec = "invalid-filter-spec"

        # Generate an otherwise valid `serve_url` with an invalid filter spec
        serve_url = rendition.serve_url

        # Undo change to `filter_spec` to avoid impacting other tests
        rendition.filter_spec = original_filter_spec

        # Test the view using the generated `serve_url`
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 400)


class TestDocumentServeView(TestCase):
    model = get_document_model()

    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)
        cls.private_document = DocumentFactory(collection=cls.root_collection)
        cls.public_document = DocumentFactory(_privacy=Privacy.PUBLIC, collection=cls.root_collection)
        cls.superuser = get_user_model().objects.create(username="superuser", is_superuser=True)

    def test_serve_private_document(self):
        """Test the serve view behaviour for private documents."""
        serve_url = self.private_document.url

        # If not authenticated, permission checks should fail and a Forbidden response returned
        for is_external_env in [True, False]:
            with self.subTest(is_external_env=is_external_env) and override_settings(IS_EXTERNAL_ENV=is_external_env):
                response = self.client.get(serve_url)
                self.assertEqual(response.status_code, 403)

        # If authenticated as a superuser, the view should serve the file
        self.client.force_login(self.superuser)
        for is_external_env in [True, False]:
            with self.subTest(is_external_env=is_external_env) and override_settings(IS_EXTERNAL_ENV=is_external_env):
                response = self.client.get(serve_url)
                self.assertEqual(response.status_code, 200)

    def test_serve_public_document(self):
        """Test the serve view behaviour for public documents."""
        # For public documents, the serve view should redirect to the file path or URL.
        for is_external_env in [True, False]:
            with self.subTest(is_external_env=is_external_env) and override_settings(IS_EXTERNAL_ENV=is_external_env):
                response = self.client.get(self.public_document.serve_url)
                self.assertEqual(response.status_code, 302)

    def test_serve_public_document_with_outdated_file_permissions(self):
        """Test the serve view behaviour for public documents with outdated file permissions."""
        self.model.objects.filter(id=self.public_document.id).update(file_permissions_last_set=None)
        self.public_document.refresh_from_db()
        self.assertTrue(self.public_document.has_outdated_file_permissions())
        response = self.client.get(self.public_document.url)
        self.assertEqual(response.status_code, 200)

    def test_serve_with_invalid_document_id(self):
        """Test the serve view behaviour when the document ID is not recognised."""
        serve_url = self.private_document.url
        serve_url = serve_url.replace(f"/{self.private_document.id}/", "/9999999/")

        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 404)

    def test_serve_with_invalid_filename(self):
        """Test the serve view behaviour when the document ID is correct, but the filename is not."""
        serve_url = self.private_document.url
        serve_url = serve_url.replace(self.private_document.filename, "invalid-filename.docx")

        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 404)
