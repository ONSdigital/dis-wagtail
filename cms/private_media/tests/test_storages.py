from unittest import mock

from botocore.exceptions import ClientError
from django.test import TestCase
from wagtail_factories import DocumentFactory

from cms.private_media.storages import PrivacySettingS3Storage


class PrivacySettingS3StorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.document = DocumentFactory()

    def setUp(self):
        self.storage = PrivacySettingS3Storage()

        bucket_mock = mock.MagicMock()
        bucket_mock.Object = mock.MagicMock()
        object_mock = mock.MagicMock()
        bucket_mock.Object.return_value = object_mock
        acl_mock = mock.MagicMock()
        object_mock.Acl.return_value = acl_mock

        # This should make self.storage.bucket() return our customised MagicMock instance
        self.storage._bucket = bucket_mock  # pylint: disable=protected-access

        # Make the mock objects available for use in tests
        self.bucket_mock = bucket_mock
        self.object_mock = object_mock
        self.acl_mock = acl_mock

    def test_make_private(self):
        self.storage.make_private(self.document.file)
        self.bucket_mock.Object.assert_called_once_with(self.document.file.name)
        self.object_mock.Acl.assert_called_once()
        self.acl_mock.put.assert_called_once_with(ACL=self.storage.private_acl_name)

    def test_make_public(self):
        self.storage.make_public(self.document.file)
        self.object_mock.Acl.assert_called_once()
        self.acl_mock.put.assert_called_once_with(ACL=self.storage.public_acl_name)

    def test_client_error_on_acl_get(self):
        self.object_mock.Acl.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObjectAcl")
        self.assertFalse(self.storage.make_private(self.document.file))

    def test_client_error_on_acl_set(self):
        self.acl_mock.put.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "PutObjectAcl")
        self.assertFalse(self.storage.make_private(self.document.file))
