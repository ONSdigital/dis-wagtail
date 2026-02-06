"""Tests for document audit logging.

This module tests that document create, edit, and delete actions
are properly logged via Wagtail's audit logging system.
"""

from http import HTTPStatus
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from wagtail.documents import get_document_model
from wagtail.models import Collection, ModelLogEntry
from wagtail.test.utils import WagtailTestUtils
from wagtail_factories import DocumentFactory

Document = get_document_model()


def create_test_document_file(filename: str = "test.txt") -> SimpleUploadedFile:
    """Create a simple test document file for upload tests."""
    return SimpleUploadedFile(filename, b"Test document content", content_type="text/plain")


class DocumentAuditLoggingTestCase(WagtailTestUtils, TestCase):
    """Test audit logging for document create, edit, and delete actions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = cls.create_superuser(username="admin", password="password")
        cls.root_collection = Collection.objects.get(depth=1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_document_create_creates_audit_log_entry(self):
        """Test that uploading a document creates an audit log entry."""
        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customdocument",
        ).count()

        add_url = reverse("wagtaildocs:add")
        response = self.client.post(
            add_url,
            {
                "title": "Test Document",
                "file": create_test_document_file(),
                "collection": self.root_collection.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Verify audit log entry was created
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customdocument",
        ).count()
        self.assertEqual(final_count, initial_count + 1)

        log_entry = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customdocument",
        ).latest("timestamp")
        self.assertEqual(log_entry.user, self.user)

    def test_document_edit_creates_audit_log_entry(self):
        """Test that editing a document creates an audit log entry."""
        document = DocumentFactory(collection=self.root_collection)

        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.edit",
            content_type__model="customdocument",
            object_id=str(document.id),
        ).count()

        edit_url = reverse("wagtaildocs:edit", args=[document.id])
        response = self.client.post(
            edit_url,
            {
                "title": "Updated Title",
                "collection": self.root_collection.id,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Verify audit log entry was created for this specific document
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.edit",
            content_type__model="customdocument",
            object_id=str(document.id),
        ).count()
        self.assertEqual(final_count, initial_count + 1)

        log_entry = ModelLogEntry.objects.filter(
            action="wagtail.edit",
            content_type__model="customdocument",
            object_id=str(document.id),
        ).latest("timestamp")
        self.assertEqual(log_entry.user, self.user)

    def test_document_delete_creates_audit_log_entry(self):
        """Test that deleting a document creates an audit log entry."""
        document = DocumentFactory(collection=self.root_collection)
        document_id = document.id

        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.delete",
            content_type__model="customdocument",
        ).count()

        delete_url = reverse("wagtaildocs:delete", args=[document.id])
        response = self.client.post(delete_url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Verify document was deleted
        self.assertFalse(Document.objects.filter(id=document_id).exists())

        # Verify audit log entry was created
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.delete",
            content_type__model="customdocument",
        ).count()
        self.assertEqual(final_count, initial_count + 1)

        log_entry = ModelLogEntry.objects.filter(
            action="wagtail.delete",
            content_type__model="customdocument",
        ).latest("timestamp")
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.object_id, str(document_id))

    def test_document_create_audit_log_mirrors_to_stdout(self):
        """Test that document create audit log entry is mirrored to stdout."""
        add_url = reverse("wagtaildocs:add")

        with patch("cms.core.audit.audit_logger") as mock_logger:
            response = self.client.post(
                add_url,
                {
                    "title": "Test Document for Stdout",
                    "file": create_test_document_file(),
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
            self.assertEqual(extra["object_type"], "custom document")

    def test_document_delete_audit_log_mirrors_to_stdout(self):
        """Test that document delete audit log entry is mirrored to stdout."""
        document = DocumentFactory(collection=self.root_collection)

        delete_url = reverse("wagtaildocs:delete", args=[document.id])

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
            self.assertEqual(extra["object_type"], "custom document")


class DocumentMultipleUploadAuditLoggingTestCase(WagtailTestUtils, TestCase):
    """Test audit logging limitations for the multiple document upload view.

    KNOWN LIMITATION: Wagtail's multiple upload view (/admin/documents/multiple/add/)
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

    def test_multiple_document_upload_does_not_create_audit_log_entry(self):
        """Document that multiple document upload does NOT create audit log entries.

        This is a known limitation. The multiple upload view bypasses Wagtail's
        standard CreateView which handles audit logging.
        """
        initial_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customdocument",
        ).count()

        # This is the URL used by Wagtail's default document upload UI
        multiple_add_url = reverse("wagtaildocs:add_multiple")
        response = self.client.post(
            multiple_add_url,
            {
                "files[]": create_test_document_file(),
            },
        )

        # Upload succeeds
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # But NO audit log entry is created - this is the limitation we're documenting
        final_count = ModelLogEntry.objects.filter(
            action="wagtail.create",
            content_type__model="customdocument",
        ).count()
        self.assertEqual(
            final_count,
            initial_count,
            "Multiple upload should NOT create audit log entries (known limitation)",
        )
