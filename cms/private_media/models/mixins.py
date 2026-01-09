import logging
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models
from django.utils import timezone

from cms.private_media.bulk_operations import bulk_set_file_permissions
from cms.private_media.constants import Privacy
from cms.private_media.managers import PrivateMediaModelManager

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile
    from wagtail.models import Site

logger = logging.getLogger(__name__)


class PrivateMediaMixin(models.Model):
    """A mixin class for models that have files that need to remain private
    until the object itself is no longer private.

    Subclasses must implement the `get_privacy_controlled_files()` method,
    which should return an iterable of `FieldFile` objects that are managed
    by the model instance.

    Where individual objects are updated (usually via the Wagtail UI), changes to
    managed field values are written to the database by the overridden
    `save()` method.

    Where multiple objects are updated at once (e.g. via a signal handler or
    management command running on the server), changes to managed field values
    are written to the database by the bulk update methods provided by
    `PrivateMediaModelManager`.
    """

    _privacy = models.CharField(max_length=10, choices=Privacy.choices, default=Privacy.PRIVATE)
    file_permissions_last_set = models.DateTimeField(editable=False, null=True)
    privacy_last_changed = models.DateTimeField(editable=False, default=timezone.now, null=False)

    class Meta:
        abstract = True

    objects: ClassVar[models.Manager] = PrivateMediaModelManager()

    @property
    def privacy(self) -> Privacy:
        """Return the privacy status of the object."""
        if isinstance(self._privacy, Privacy):
            return self._privacy
        for item in Privacy:
            if item.value == self._privacy:
                return item
        raise ValueError(f"Invalid privacy value: {self._privacy}")

    @privacy.setter
    def privacy(self, value: Privacy) -> None:
        """Set the privacy status of the object and conditionally update the
        privacy_last_changed timestamp if the privacy has changed.
        """
        if self.privacy is not value:
            self._privacy = value.value
            self.privacy_last_changed = timezone.now()

    @property
    def is_private(self) -> bool:
        """Return True if the object is private."""
        return self.privacy is Privacy.PRIVATE

    @property
    def is_public(self) -> bool:
        """Return True if the object is public."""
        return self.privacy is Privacy.PUBLIC

    def save(self, *args: Any, set_file_permissions: bool = True, **kwargs: Any) -> None:
        """Save the model instance and manage file permissions.

        Args:
            set_file_permissions: If True, updates file permissions after saving
            *args: Additional positional arguments passed to parent save method
            **kwargs: Additional keyword arguments passed to parent save method
        """
        # Save model field changes at this point
        super().save(*args, **kwargs)

        # Trigger file permission updates after-the-fact
        if set_file_permissions and self.has_outdated_file_permissions():
            results = bulk_set_file_permissions(self.get_privacy_controlled_files(), self.privacy)
            # Only update 'file_permissions_last_set' if all updates were successfull
            all_updates_successful = all(results.values())
            if all_updates_successful:
                self.file_permissions_last_set = timezone.now()
                kwargs.update(force_insert=False, update_fields=["file_permissions_last_set"])
                super().save(*args, **kwargs)

    def has_outdated_file_permissions(self) -> bool:
        """Check if the file permissions are outdated relative to privacy changes."""
        return self.file_permissions_last_set is None or self.file_permissions_last_set < self.privacy_last_changed

    def get_privacy_controlled_files(self) -> Iterator[FieldFile]:
        """Return an Iterator of files that are managed by the model instance.

        Returns:
            Iterator[FieldFile]: An Iterator of files managed by the instance
        """
        raise NotImplementedError

    def get_privacy_controlled_serve_urls(self, sites: Iterable[Site]) -> Iterator[str]:
        """Return an iterator of fully-fledged serve URLs for this object, covering the domains for all provided
        sites. It is the responsibility of the subclass to implement this method.
        """
        raise NotImplementedError

    def get_privacy_controlled_file_urls(self) -> Iterator[str]:
        """Return an iterator of fully-fledged file URLs for this object.

        NOTE: Will only return URLs that include a domain prefix (where the files are externally hosted).
        """
        for file in self.get_privacy_controlled_files():
            url = file.url
            if not url.startswith("/"):
                yield url
