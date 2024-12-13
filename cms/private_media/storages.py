import logging
from typing import TYPE_CHECKING

from botocore.exceptions import ClientError
from django.core.files.storage import FileSystemStorage, InMemoryStorage
from storages.backends.s3 import S3Storage

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


logger = logging.getLogger(__name__)


class AccessControlledS3Storage(S3Storage):
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
        except ClientError:
            logger.exception("Failed to retrieve ACL for %s", file.name)
            return False
        try:
            obj_acl.put(ACL=acl_name)
        except ClientError:
            logger.exception("Failed to set ACL for %s", file.name)
            return False

        logger.info("ACL set successfully for %s", file.name)
        return True


class AccessControlLoggingFileSystemStorage(FileSystemStorage):
    """A version of Django's `FileSystemStorage` backend for local development and tests, which logs
    file-permission-setting requests, and always reports success.
    """

    def make_private(self, file: "FieldFile") -> bool:
        """Pretend to make the provided file private."""
        logger.info("Skipping private file permission setting for '%s'.", file.name)
        return True

    def make_public(self, file: "FieldFile") -> bool:
        """Pretend to make the provided file public."""
        logger.info("Skipping public file permission setting for '%s'.", file.name)
        return True


class ReliableAccessControlInMemoryStorage(InMemoryStorage):
    """A version of Django's `InMemoryStorage` backend for unit tests, that always reports success
    for file-permission-setting requests.
    """

    def make_private(self, file: "FieldFile") -> bool:  # pylint: disable=unused-argument
        """Report success in making the provided file private."""
        return True

    def make_public(self, file: "FieldFile") -> bool:  # pylint: disable=unused-argument
        """Report success in making the provided file public."""
        return True


class FlakyAccessControlInMemoryStorage(InMemoryStorage):
    """A version of Django's `InMemoryStorage` backend for unit tests, that always reports failure
    for file-permission-setting requests.
    """

    def make_private(self, file: "FieldFile") -> bool:  # pylint: disable=unused-argument
        """Report failure in making the provided file private."""
        return False

    def make_public(self, file: "FieldFile") -> bool:  # pylint: disable=unused-argument
        """Report failure in making the provided file public."""
        return False
