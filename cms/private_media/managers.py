from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone
from wagtail.contrib.frontend_cache.utils import PurgeBatch
from wagtail.documents.models import DocumentQuerySet
from wagtail.images.models import ImageQuerySet
from wagtail.models import Site

from .bulk_operations import bulk_set_file_permissions
from .constants import Privacy
from .utils import get_frontend_cache_configuration

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile

    from cms.private_media.models import PrivateMediaMixin


class PrivateMediaModelManager(models.Manager):
    """A custom model `Manager` to be used by concrete subclasses of
    `PrivateMediaCollectionMember`. It includes several methods for
    applying privacy-related changes to multiple objects at the same
    time.
    """

    def bulk_set_privacy(self, objects: Iterable[PrivateMediaMixin], privacy: Privacy) -> int:
        """Update an iterable of objects of this type to reflect the 'privacy'
        as efficiently as possible. Returns the number of objects that were actually
        updated in the process.
        """
        to_update = []
        for obj in objects:
            if obj.privacy != privacy:
                obj.privacy = privacy
                to_update.append(obj)
        if not to_update:
            return 0

        to_update = self.bulk_set_file_permissions(to_update, privacy, save_changes=False)

        count = self.bulk_update(
            to_update,  # type: ignore[arg-type]
            fields=["_privacy", "privacy_last_changed", "file_permissions_last_set"],
        )

        if count and get_frontend_cache_configuration():
            sites = Site.objects.all()
            serve_url_batch = PurgeBatch()
            file_url_batch = PurgeBatch()
            for obj in to_update:
                serve_url_batch.add_urls(obj.get_privacy_controlled_serve_urls(sites))
                file_url_batch.add_urls(obj.get_privacy_controlled_file_urls())
            serve_url_batch.purge()
            file_url_batch.purge()
        return count

    def bulk_make_public(self, objects: Iterable[PrivateMediaMixin]) -> int:
        """Make an iterable of objects of this type 'public' as efficiently as
        possible. Returns the number of objects that were actually updated in
        the process.
        """
        return self.bulk_set_privacy(objects, Privacy.PUBLIC)

    def bulk_make_private(self, objects: Iterable[PrivateMediaMixin]) -> int:
        """Make an iterable of objects of this type 'private' as efficiently as
        possible. Returns the number of objects that were actually updated
        in the process.
        """
        return self.bulk_set_privacy(objects, Privacy.PRIVATE)

    def bulk_set_file_permissions(
        self, objects: Iterable[PrivateMediaMixin], privacy: Privacy, *, save_changes: bool = False
    ) -> list[PrivateMediaMixin]:
        """For an iterable of objects of this type, set the file permissions for all
        related files to reflect `privacy`. Returns a list of the provided objects,
        with their `file_permissions_last_set` datetime updated if all related files
        were successfully updated.
        """
        files_by_object: dict[PrivateMediaMixin, list[FieldFile]] = defaultdict(list)
        all_files = []
        objects = list(objects)

        for obj in objects:
            for file in obj.get_privacy_controlled_files():
                all_files.append(file)
                files_by_object[obj].append(file)

        results = bulk_set_file_permissions(all_files, privacy)

        now = timezone.now()
        for obj in objects:
            files = files_by_object[obj]
            if all(results.get(file) for file in files):
                obj.file_permissions_last_set = now

        if save_changes:
            self.bulk_update(objects, ["file_permissions_last_set"])  # type: ignore[arg-type]

        return objects


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
