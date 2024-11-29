from collections.abc import Iterator
from typing import TYPE_CHECKING, ClassVar

from cms.private_media.managers import PrivateDocumentManager

from .mixins import PrivateMediaMixin

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


class PrivateDocumentMixin(PrivateMediaMixin):
    """A mixin class to be applied to a project's custom Document model,
    allowing the privacy to be controlled effectively, depending on the
    collection the image belongs to.
    """

    objects: ClassVar[PrivateDocumentManager] = PrivateDocumentManager()

    class Meta:
        abstract = True

    def get_privacy_controlled_files(self) -> Iterator["FieldFile"]:
        file: FieldFile | None = getattr(self, "file", None)
        if file:
            yield file
