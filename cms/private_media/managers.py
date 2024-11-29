from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone
from wagtail.documents.models import DocumentQuerySet
from wagtail.images.models import ImageQuerySet

from .bulk_operations import bulk_set_file_permissions
from .constants import Privacy

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile

    from cms.private_media.models import PrivateMediaMixin


class PrivateMediaModelManager(models.Manager):
    """A custom model `Manager` to be used by concrete subclasses of
    `PrivateMediaCollectionMember`. It includes several methods for
    applying privacy-related changes to multiple objects at the same
    time.
    """

    def bulk_set_privacy(self, objects: Iterable["PrivateMediaMixin"], intended_privacy: Privacy) -> int:
        """Update an iterable of objects of this type to reflect the 'intended_privacy'
        as efficiently as possible. Returns the number of objects that were actually
        updated in the process.
        """
        to_update = []
        for obj in objects:
            if obj.privacy != intended_privacy:
                obj.privacy = intended_privacy
                to_update.append(obj)
        if not to_update:
            return 0

        count = self.bulk_update(to_update, fields=["_privacy", "privacy_last_changed"])  # type: ignore[arg-type]
        self.bulk_update_file_permissions(to_update, intended_privacy)
        return count

    def bulk_make_public(self, objects: Iterable["PrivateMediaMixin"]) -> int:
        """Make an iterable of objects of this type 'public' as efficiently as
        possible. Returns the number of objects that were actually updated in
        the process.
        """
        return self.bulk_set_privacy(objects, Privacy.PUBLIC)

    def bulk_make_private(self, objects: Iterable["PrivateMediaMixin"]) -> int:
        """Make an iterable of objects of this type 'private' as efficiently as
        possible. Returns the number of objects that were actually updated
        in the process.
        """
        return self.bulk_set_privacy(objects, Privacy.PRIVATE)

    def bulk_update_file_permissions(self, objects: Iterable["PrivateMediaMixin"], intended_privacy: Privacy) -> int:
        """For an itrerable of objects of this type, set the file permissions for all
        related files to reflect `intended_privacy`. Returns the number of objects
        for which all related files were successfully updated (which will also have
        their 'file_permissions_last_set' datetime updated).
        """
        successfully_updated_objects = []
        files_by_object: dict[PrivateMediaMixin, list[FieldFile]] = defaultdict(list)
        all_files = []

        for obj in objects:
            for file in obj.get_privacy_controlled_files():
                all_files.append(file)
                files_by_object[obj].append(file)

        results = bulk_set_file_permissions(all_files, intended_privacy)

        for obj, files in files_by_object.items():
            if all(results.get(file) for file in files):
                obj.file_permissions_last_set = timezone.now()
                successfully_updated_objects.append(obj)

        if successfully_updated_objects:
            return self.bulk_update(
                successfully_updated_objects,  # type: ignore[arg-type]
                fields=["file_permissions_last_set"],
            )

        return 0


class PrivateImageManager(PrivateMediaModelManager):
    """A subclass of `PrivateMediaModelManager` that returns instances of
    Wagtail's custom `ImageQuerySet`, which includes image-specific
    filter methods other functionality that Wagtail itself depends on.
    """

    def get_queryset(self) -> ImageQuerySet:
        """Return an `ImageQuerySet` instance."""
        return ImageQuerySet(self.model, using=self._db)


class PrivateDocumentManager(PrivateMediaModelManager):
    """A subclass of `PrivateMediaModelManager` that returns instances of
    Wagtail's custom `DocumentQuerySet`, which includes document-specific
    filter methods other functionality that Wagtail itself depends on.
    """

    def get_queryset(self) -> DocumentQuerySet:
        """Return a `DocumentQuerySet` instance."""
        return DocumentQuerySet(self.model, using=self._db)
