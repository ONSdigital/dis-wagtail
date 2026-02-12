"""Tests for image audit logging.

This module tests that image create, edit, and delete actions
are properly logged via Wagtail's audit logging system.
"""

from http import HTTPStatus
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image as PILImage
from wagtail.images import get_image_model
from wagtail.models import Collection, ModelLogEntry
from wagtail.test.utils import WagtailTestUtils
from wagtail_factories import ImageFactory

Image = get_image_model()


def create_test_image_file(filename: str = "test.jpg") -> SimpleUploadedFile:
    """Create a simple test image file for upload tests."""
    image = PILImage.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(filename, buffer.read(), content_type="image/jpeg")


class ImageAuditLoggingTestCase(WagtailTestUtils, TestCase):
    """Test audit logging for image create, edit, and delete actions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_superuser(username="admin", password="password")
        cls.root_collection = Collection.objects.get(depth=1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_image_create_creates_audit_log_entry(self):
        """Test that uploading an image creates an audit log entry."""
        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customimage",
        ).count()

        add_url = reverse("wagtailimages:add")
        response = self.client.post(
            add_url,
            {
                "title": "Test Image",
                "description": "Test image description",
                "file": create_test_image_file(),
                "collection": self.root_collection.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Verify audit log entry was created
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customimage",
        ).count()
        self.assertEqual(final_count, initial_count + 1)

        log_entry = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customimage",
        ).latest("timestamp")
        self.assertEqual(log_entry.user, self.user)

    def test_image_edit_creates_audit_log_entry(self):
        """Test that editing an image creates an audit log entry."""
        image = ImageFactory(collection=self.root_collection)

        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.edit",
            content_type__model="customimage",
            object_id=str(image.id),
        ).count()

        edit_url = reverse("wagtailimages:edit", args=[image.id])
        response = self.client.post(
            edit_url,
            {
                "title": "Updated Title",
                "description": "Updated description",
                "collection": self.root_collection.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Verify audit log entry was created for this specific image
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.edit",
            content_type__model="customimage",
            object_id=str(image.id),
        ).count()
        self.assertEqual(final_count, initial_count + 1)

        log_entry = ModelLogEntry.objects.filter(
            action="wagtail.edit",
            content_type__model="customimage",
            object_id=str(image.id),
        ).latest("timestamp")
        self.assertEqual(log_entry.user, self.user)

    def test_image_delete_creates_audit_log_entry(self):
        """Test that deleting an image creates an audit log entry."""
        image = ImageFactory(collection=self.root_collection)
        image_id = image.id

        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.delete",
            content_type__model="customimage",
        ).count()

        delete_url = reverse("wagtailimages:delete", args=[image.id])
        response = self.client.post(delete_url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Verify image was deleted
        self.assertFalse(Image.objects.filter(id=image_id).exists())

        # Verify audit log entry was created
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.delete",
            content_type__model="customimage",
        ).count()
        self.assertEqual(final_count, initial_count + 1)

        log_entry = ModelLogEntry.objects.filter(
            action="wagtail.delete",
            content_type__model="customimage",
        ).latest("timestamp")
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.object_id, str(image_id))

    def test_image_create_audit_log_mirrors_to_stdout(self):
        """Test that image create audit log entry is mirrored to stdout."""
        add_url = reverse("wagtailimages:add")

        with patch("cms.core.audit.audit_logger") as mock_logger:
            response = self.client.post(
                add_url,
                {
                    "title": "Test Image for Stdout",
                    "description": "Test image description",
                    "file": create_test_image_file(),
                    "collection": self.root_collection.id,
                },
            )

            self.assertEqual(response.status_code, HTTPStatus.FOUND)

            # Verify audit logger was called
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args

            # Verify the log message format and action
            self.assertEqual(call_args[0][0], "Audit event: %s")
            self.assertEqual(call_args[0][1], "wagtail.create")
            extra = call_args[1]["extra"]
            self.assertEqual(extra["event"], "wagtail.create")
            self.assertEqual(extra["object_type"], "custom image")

    def test_image_delete_audit_log_mirrors_to_stdout(self):
        """Test that image delete audit log entry is mirrored to stdout."""
        image = ImageFactory(collection=self.root_collection)

        delete_url = reverse("wagtailimages:delete", args=[image.id])

        with patch("cms.core.audit.audit_logger") as mock_logger:
            response = self.client.post(delete_url)

            self.assertEqual(response.status_code, HTTPStatus.FOUND)

            # Verify audit logger was called
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args

            # Verify the log message format and action
            self.assertEqual(call_args[0][0], "Audit event: %s")
            self.assertEqual(call_args[0][1], "wagtail.delete")
            extra = call_args[1]["extra"]
            self.assertEqual(extra["event"], "wagtail.delete")
            self.assertEqual(extra["object_type"], "custom image")


class ImageMultipleUploadAuditLoggingTestCase(WagtailTestUtils, TestCase):
    """Test audit logging limitations for the multiple image upload view.

    KNOWN LIMITATION: Wagtail's multiple upload view (/admin/images/multiple/add/)
    does not create audit log entries. This is the default upload UI in Wagtail.

    These tests document this limitation. If audit logging is later implemented
    for multiple uploads, these tests should be updated to expect log entries.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_superuser(username="admin", password="password")
        cls.root_collection = Collection.objects.get(depth=1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_multiple_image_upload_does_not_create_audit_log_entry(self):
        """Document that multiple image upload does NOT create audit log entries.

        This is a known limitation. The multiple upload view bypasses Wagtail's
        standard CreateView which handles audit logging.
        """
        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customimage",
        ).count()

        # This is the URL used by Wagtail's default image upload UI
        multiple_add_url = reverse("wagtailimages:add_multiple")
        response = self.client.post(
            multiple_add_url,
            {
                "files[]": create_test_image_file(),
            },
        )

        # Upload succeeds
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # But NO audit log entry is created - this is the limitation we're documenting
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customimage",
        ).count()
        self.assertEqual(
            final_count,
            initial_count,
            "Multiple upload should NOT create audit log entries (known limitation)",
        )
