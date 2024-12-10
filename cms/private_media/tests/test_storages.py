from unittest import mock

from botocore.exceptions import ClientError
from django.conf import settings
from django.test import TestCase, override_settings
from moto import mock_aws
from wagtail_factories import DocumentFactory

from cms.private_media.storages import PrivacySettingS3Storage


@mock_aws
@override_settings(AWS_STORAGE_BUCKET_NAME="test-bucket")
class PrivacySettingS3StorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.document = DocumentFactory()

    def setUp(self):
        super().setUp()
        self.storage = PrivacySettingS3Storage()
        # Create a bucket to allow '_set_file_acl' to at least reach the 'put' stage
        bucket = self.storage.connection.Bucket(settings.AWS_STORAGE_BUCKET_NAME)
        bucket.create()

    def test_make_private_client_error_on_acl_set(self):
        with self.assertLogs("cms.private_media.storages", level="EXCEPTION") as logs:
            self.assertFalse(self.storage.make_private(self.document.file))
        self.assertIn(
            f"EXCEPTION:cms.private_media.storages:Failed to set ACL for {self.document.file.name}",
            logs.output[0],
        )

    def test_make_private_client_error_on_acl_get(self):
        object_mock = mock.MagicMock()
        object_mock.Acl.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObjectAcl")
        # initialize the bucket to allow it to be patched
        self.storage.bucket  # noqa: B018 # pylint: disable=pointless-statement
        with mock.patch.object(self.storage._bucket, "Object", return_value=object_mock):  # pylint: disable=protected-access  # noqa: SIM117
            with self.assertLogs("cms.private_media.storages", level="EXCEPTION") as logs:
                self.assertFalse(self.storage.make_private(self.document.file))
        self.assertIn(
            f"EXCEPTION:cms.private_media.storages:Failed to retrieve ACL for {self.document.file.name}",
            logs.output[0],
        )

    def test_make_public_success(self):
        acl_mock = mock.MagicMock()
        acl_mock.put.return_value = True
        object_mock = mock.MagicMock()
        object_mock.Acl.return_value = acl_mock
        # initialize the bucket to allow it to be patched
        self.storage.bucket  # noqa: B018 # pylint: disable=pointless-statement
        with mock.patch.object(self.storage._bucket, "Object", return_value=object_mock):  # pylint: disable=protected-access  # noqa: SIM117
            with self.assertLogs("cms.private_media.storages", level="INFO") as logs:
                self.assertTrue(self.storage.make_public(self.document.file))
        self.assertIn(
            f"INFO:cms.private_media.storages:ACL set successfully for {self.document.file}",
            logs.output,
        )
