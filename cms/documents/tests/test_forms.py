from unittest.mock import Mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import filesizeformat
from django.test import TestCase, override_settings
from wagtail.documents import get_document_model
from wagtail.documents.forms import get_document_form

from cms.documents.models import CustomDocument


class ONSDocumentFormTestCase(TestCase):
    """Tests for file size validation in ONSDocumentForm."""

    def setUp(self):
        """Set up the document model and form class."""
        self.form_class = get_document_form(get_document_model())

    def test_save(self):
        self.assertEqual(CustomDocument.objects.count(), 0)
        test_file = SimpleUploadedFile("test.pdf", b"x", content_type="application/pdf")
        form = self.form_class({"title": "test", "file": test_file}, files={"file": test_file})
        self.assertTrue(form.is_valid())

        self.assertEqual(CustomDocument.objects.count(), 1)

    def test_title_field_help_text(self):
        form = self.form_class()
        self.assertEqual(form.fields["title"].help_text, "Limited to 100 characters.")

    # note: setting these to something predictable
    @override_settings(WAGTAILDOCS_EXTENSIONS=["pdf", "doc"], DOCUMENTS_MAX_UPLOAD_SIZE=1024 * 1024)
    def test_file_field_help_text(self):
        form = self.form_class()

        self.assertEqual(form.fields["file"].help_text, "Supported formats: PDF, DOC. Maximum filesize: 1.0\xa0MB.")

    def test_clean_file_accepts_file_under_size_limit(self):
        """clean_file should accept files smaller than DOCUMENTS_MAX_UPLOAD_SIZE."""
        # Create a small file (1KB)
        small_file = SimpleUploadedFile("test.pdf", b"x" * 1024, content_type="application/pdf")

        form = self.form_class(data={"title": "Test"}, files={"file": small_file})
        # Call clean_file directly
        form.cleaned_data = {"file": small_file}
        result = form.clean_file()

        self.assertEqual(result, small_file)

    def test_clean_file_accepts_file_at_exact_size_limit(self):
        """clean_file should accept files exactly at DOCUMENTS_MAX_UPLOAD_SIZE."""
        # Create a mock file at exactly DOCUMENTS_MAX_UPLOAD_SIZE

        exact_size_file = SimpleUploadedFile(
            "test.pdf", b"x" * settings.DOCUMENTS_MAX_UPLOAD_SIZE, content_type="application/pdf"
        )

        form = self.form_class()
        form.cleaned_data = {"file": exact_size_file}
        result = form.clean_file()

        self.assertEqual(result, exact_size_file)

    def test_clean_file_rejects_file_over_size_limit(self):
        """clean_file should raise ValidationError for files exceeding DOCUMENTS_MAX_UPLOAD_SIZE."""
        # Create a mock file that's too large
        large_file = Mock()
        large_file.size = settings.DOCUMENTS_MAX_UPLOAD_SIZE + 1

        form = self.form_class()
        form.cleaned_data = {"file": large_file}

        with self.assertRaises(ValidationError) as context:
            form.clean_file()

        # Check the error message format
        max_upload_size_text = filesizeformat(settings.DOCUMENTS_MAX_UPLOAD_SIZE)
        expected_message = f"File size must be less than {max_upload_size_text}."
        self.assertEqual(str(context.exception.message), expected_message)

    @override_settings(DOCUMENTS_MAX_UPLOAD_SIZE=10 * 1024 * 1024)  # 10MB
    def test_clean_file_error_message_uses_correct_size_limit(self):
        """ValidationError message should reflect the configured DOCUMENTS_MAX_UPLOAD_SIZE."""
        large_file = Mock()
        large_file.size = 15 * 1024 * 1024  # 15MB

        form = self.form_class()
        form.cleaned_data = {"file": large_file}

        with self.assertRaises(ValidationError) as context:
            form.clean_file()

        # Should show 10.00 MB in the message
        self.assertEqual("File size must be less than 10.0\xa0MB.", str(context.exception.message))

    def test_clean_file_returns_file_when_no_file_provided(self):
        """clean_file should return None when no file is provided."""
        form = self.form_class()
        form.cleaned_data = {"file": None}
        result = form.clean_file()

        self.assertIsNone(result)
