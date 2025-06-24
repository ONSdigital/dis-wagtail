import os
from unittest import mock

from botocore.exceptions import ClientError
from django.conf import settings
from django.test import TestCase, override_settings
from moto import mock_aws
from wagtail_factories import DocumentFactory

from cms.private_media.storages import AccessControlledS3Storage


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_S3_REGION_NAME="us-east-1",
    AWS_ACCESS_KEY_ID="testing",
    AWS_SECRET_ACCESS_KEY="testing",
    AWS_SESSION_TOKEN="testing",
    AWS_EC2_METADATA_DISABLED=True,
)
@mock_aws
class AccessControlledS3StorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.document = DocumentFactory()

    def setUp(self):
        super().setUp()
        self.storage = AccessControlledS3Storage()
        # Create a bucket to allow '_set_file_acl' to at least reach the 'put' stage
        bucket = self.storage.connection.Bucket(settings.AWS_STORAGE_BUCKET_NAME)
        bucket.create()

        self.document = DocumentFactory()

    def test_make_private_client_error_on_acl_set(self):
        with self.assertLogs("cms.private_media.storages", level="ERROR") as logs:
            self.assertFalse(self.storage.make_private(self.document.file))

        self.assertEqual(len(logs.records), 1)
        self.assertEqual(logs.records[0].message, "Failed to set ACL")
        self.assertEqual(logs.records[0].key, str(self.document.file))

    def test_make_private_client_error_on_acl_get(self):
        object_mock = mock.MagicMock()
        object_mock.Acl.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObjectAcl")
        # initialize the bucket to allow it to be patched
        self.storage.bucket  # noqa: B018 # pylint: disable=pointless-statement
        with mock.patch.object(self.storage._bucket, "Object", return_value=object_mock):  # pylint: disable=protected-access  # noqa: SIM117
            with self.assertLogs("cms.private_media.storages", level="ERROR") as logs:
                self.assertFalse(self.storage.make_private(self.document.file))

        self.assertEqual(len(logs.records), 1)
        self.assertEqual(logs.records[0].message, "Failed to retrieve ACL")
        self.assertEqual(logs.records[0].key, str(self.document.file))

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

        self.assertEqual(len(logs.records), 1)
        self.assertEqual(logs.records[0].message, "ACL set successfully")
        self.assertEqual(logs.records[0].key, str(self.document.file))
