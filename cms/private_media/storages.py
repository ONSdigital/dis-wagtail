import logging
from typing import TYPE_CHECKING

from botocore.exceptions import ClientError
from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


logger = logging.getLogger(__name__)


class PrivacySettingS3Storage(S3Storage):
    # pylint: disable=abstract-method
    private_acl_name = "private"
    public_acl_name = "public-read"

    def make_private(self, file: "FieldFile") -> bool:
        """Make the provided file private in S3."""
        return self._set_file_acl(file, self.private_acl_name)

    def make_public(self, file: "FieldFile") -> bool:
        """Make the provided file publically readable in S3."""
        return self._set_file_acl(file, self.public_acl_name)

    def _set_file_acl(self, file: "FieldFile", acl_name: str) -> bool:
        obj = self.bucket.Object(file.name)
        try:
            obj_acl = obj.Acl()
        except ClientError as e:
            logger.exception("Failed to retrieve ACL for %s", file.name, e)
            return False
        try:
            obj_acl.put(ACL=acl_name)
        except ClientError as e:
            logger.exception("Failed to set ACL for %s", file.name, e)
            return False

        logger.info("ACL set successfully for %s", file.name)
        return True


class DummyPrivacySettingFileSystemStorage(FileSystemStorage):
    """Dummy storage class for use in tests."""

    def make_private(self, file: "FieldFile") -> bool:  # pylint: disable=unused-argument
        """Pretend to make the provided file private."""
        return True

    def make_public(self, file: "FieldFile") -> bool:  # pylint: disable=unused-argument
        """Pretend to make the provided file public."""
        return True
