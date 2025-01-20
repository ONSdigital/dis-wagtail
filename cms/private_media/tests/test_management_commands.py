from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail_factories import DocumentFactory, ImageFactory

from cms.private_media.constants import Privacy


class RetryFilePermissionSetAttemptsCommandTests(TestCase):
    command_name = "retry_file_permission_set_attempts"

    def setUp(self):
        ImageFactory()
        ImageFactory(_privacy=Privacy.PUBLIC)
        DocumentFactory()
        DocumentFactory(_privacy=Privacy.PUBLIC)
        up_to_date_image = ImageFactory()
        up_to_date_document = DocumentFactory()

        # Adjust `file_permissions_last_set` for all items but the 'up-to-date' ones
        one_day_ago = timezone.now() - timedelta(days=1)
        get_image_model().objects.exclude(id=up_to_date_image.id).update(file_permissions_last_set=one_day_ago)
        get_document_model().objects.exclude(id=up_to_date_document.id).update(file_permissions_last_set=one_day_ago)

    def call_command(self, command_name: str, *args, **kwargs):
        out = StringIO()
        call_command(
            command_name,
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test_default(self):
        with self.assertNumQueries(7):
            # Query summary:
            # 1. Fetch outdated documents
            # 2. Update 'file_permissions_last_set' for outdated private documents
            # 3. Update 'file_permissions_last_set' for outdated public documents
            # 4. Fetch outdated images
            # 5. Fetch renditions for those images
            # 6. Update 'file_permissions_last_set' for outdated private images
            # 7. Update 'file_permissions_last_set' for outdated public images
            output = self.call_command(self.command_name)

        self.assertIn("2 CustomDocument instances have outdated file permissions", output)
        self.assertIn("File permissions successfully updated for 1 private custom documents.", output)
        self.assertIn("File permissions successfully updated for 1 public custom documents.", output)
        self.assertIn("2 CustomImage instances have outdated file permissions", output)
        self.assertIn("File permissions successfully updated for 1 private custom images.", output)
        self.assertIn("File permissions successfully updated for 1 public custom images.", output)

    def test_dry_run(self):
        with self.assertNumQueries(2):
            # Query summary:
            # 1. Fetch outdated documents
            # 2. Fetch outdated images
            output = self.call_command(self.command_name, "--dry-run")
        self.assertIn("This is a dry run.", output)
        self.assertIn("2 CustomDocument instances have outdated file permissions", output)
        self.assertIn("Would update file permissions for 1 private custom documents.", output)
        self.assertIn("Would update file permissions for 1 public custom documents.", output)
        self.assertIn("2 CustomImage instances have outdated file permissions", output)
        self.assertIn("Would update file permissions for 1 private custom images.", output)
        self.assertIn("Would update file permissions for 1 public custom images.", output)
