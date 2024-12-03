from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, ClassVar

from cms.private_media.managers import PrivateDocumentManager

from .mixins import PrivateMediaMixin

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile
    from wagtail.models import Site


class PrivateDocumentMixin(PrivateMediaMixin):
    """A mixin class to be applied to a project's custom Document model,
    allowing the privacy of related files to be controlled effectively.
    """

    objects: ClassVar[PrivateDocumentManager] = PrivateDocumentManager()

    class Meta:
        abstract = True

    def get_privacy_controlled_files(self) -> Iterator["FieldFile"]:
        file: FieldFile | None = getattr(self, "file", None)
        if file:
            yield file

    def get_privacy_controlled_serve_urls(self, sites: Iterable["Site"]) -> Iterator[str]:
        """Return an iterator of fully-fledged serve URLs for this document, covering the domains for all
        provided sites.
        """
        if not sites:
            return
        for site in sites:
            yield site.root_url + self.url  # type: ignore[attr-defined]
