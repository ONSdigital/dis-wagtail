from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from cms.private_media import utils

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile

    from cms.private_media.models import PrivateFilesMixin


class PrivateFilesModelManager(models.Manager):
    """A custom model `Manager` to be used by concrete subclasses of
    `PrivateMediaCollectionMember`. It includes several methods for
    applying privacy-related changes to multiple objects at the same
    time.
    """

    def bulk_make_public(self, objects: Iterable["PrivateFilesMixin"]) -> int:
        """Make a list of objects of this type 'public' as efficiently as
        possible. Returns the number of objects that were actually updated
        in response to the request.
        """
        to_update = []
        for obj in objects:
            if obj.is_private:
                obj.set_privacy()
                to_update.append(obj)
        if not to_update:
            return 0

        count = self.bulk_update(to_update, fields=["is_private", "privacy_last_changed"])  # type: ignore[arg-type]
        self.bulk_update_file_permissions(to_update, False)
        return count

    def bulk_make_private(self, objects: Iterable["PrivateFilesMixin"]) -> int:
        """Make a list of objects of this type 'private' as efficiently as
        possible. Returns the number of objects that were actually updated
        in response to the request.
        """
        to_update = []
        for obj in objects:
            if not obj.is_private:
                obj.set_privacy()
                to_update.append(obj)
        if not to_update:
            return 0

        count = self.bulk_update(to_update, fields=["is_private", "privacy_last_changed"])  # type: ignore[arg-type]
        self.bulk_update_file_permissions(to_update, True)
        return count

    def bulk_update_file_permissions(self, objects: Iterable["PrivateFilesMixin"], private: bool) -> int:
        """For a list of objects of this type, set the file permissions for all
        related files to either 'public' or 'private'. Returns the number of objects
        for which all related files were successfully updated - which will
        also have their 'file_permissions_last_set' datetime updated.
        """
        successfully_updated_objects = []
        files_by_object: dict[PrivateFilesMixin, list[FieldFile]] = defaultdict(list)
        all_files = []

        for obj in objects:
            for file in obj.get_privacy_controlled_files():
                all_files.append(file)
                files_by_object[obj].append(file)

        results = utils.bulk_set_file_permissions(all_files, private)

        for obj, files in files_by_object.items():
            if all(results.get(file) for file in files):
                obj.file_permissions_last_set = timezone.now()
                successfully_updated_objects.append(obj)

        if successfully_updated_objects:
            return self.bulk_update(  # type: ignore[arg-type]
                successfully_updated_objects, fields=["file_permissions_last_set"]
            )

        return 0
