import logging
from typing import TYPE_CHECKING

from django.core.files.storage import FileSystemStorage

from botocore.exceptions import ClientError
from storages.backends.s3 import S3Storage

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


logger = logging.getLogger(__name__)


class PrivacySettingS3Storage(S3Storage):
    private_acl_name = "private"
    public_acl_name = "public-read"

    def make_private(self, file: "FieldFile") -> bool:
        return self._set_file_acl(file, self.private_acl_name)

    def make_public(self, file: "FieldFile") -> bool:
        return self._set_file_acl(file, self.public_acl_name)

    def _set_file_acl(self, file: "FieldFile", acl_name: str) -> bool:
        obj = self.bucket.Object(file.name)
        try:
            obj_acl = obj.Acl()
        except ClientError as e:
            logger.debug(f"Failed to retreive ACL for {file.name}: {e!r}")
            return False
        try:
            obj_acl.put(ACL=acl_name)
        except ClientError as e:
            logger.debug(f"Failed to set ACL for {file.name}: {e!r}")
            return False

        logger.info(f"ACL set successfully for {file.name}")
        return True


class PrivacySettingFileSystemStorage(FileSystemStorage):
    def make_private(self, file: "FieldFile") -> bool:
        logger.debug("PrivacySettingFileSystemStorage does not support setting of individual file permissions.")
        return True

    def make_public(self, file: "FieldFile") -> bool:
        logger.debug("PrivacySettingFileSystemStorage does not support setting of individual file permissions.")
        return True
